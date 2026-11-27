"""약 이름 → 약효 분류 조회 (홈 '오늘 먹을 약' 배지, frontend/src/data/efficacy.js의 efficacy 필드).

원칙: 확실할 때만 분류를 돌려주고, 애매하면 None(화면은 '약효 정보 확인 중'). 짐작하지 않는다.

분류를 찾는 순서 (efficacy_for):
  1. 약봉투에 약국이 인쇄한 분류([항생제] 등)  → source='pharmacy_bag'
  2. 처방전 보험코드(9자리)로 허가정보 조회     → source='insurance_code'
  3. 약 이름으로 허가정보 조회 (find_by_name)   → source='name_lookup'

이름 조회는 이렇게 좁힌다.
  - 이름을 '상표 + 제형 + 함량'으로 쪼갠다. 예: 지스로맥스정250mg → 지스로맥스 / 정 / 250mg
  - 상표가 같은 품목을 모으고, 제형·함량으로 거른다.
  - 약봉투의 다른 값으로 교차 확인한다: 단위(정·캡슐·mL)와 제형, 성상의 색, 효능 문장.
  - 후보가 여러 개여도 분류가 모두 같으면 그 분류를 쓴다(제품은 몰라도 분류는 확실).
  - 상표 한 글자 오타(OCR)는 후보가 하나이고 교차 확인 근거가 2개 이상일 때만 인정한다.

허가정보 데이터는 공공데이터 파일을 내려받아 load_records()로 읽는다. 열 이름은 파일마다 다를 수 있어
COLUMN_MAP으로 맞춘다. DB 테이블로 옮기더라도 DrugRecord 모양만 맞추면 이 파일은 그대로 쓸 수 있다.
"""

from __future__ import annotations

import csv
import io
import logging
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

Source = Literal["pharmacy_bag", "insurance_code", "name_lookup"]
Match = Literal["printed", "code", "exact", "class_agree", "ingredient", "fuzzy"]

# ------------------------------------------------------------------ 이름 정리·쪼개기

# 긴 것부터 확인해야 '건조시럽'이 '시럽'으로, '서방정'이 '정'으로 잘리지 않는다.
FORM_WORDS = [
    "필름코팅정", "건조시럽", "드라이시럽", "나잘스프레이", "연질캡슐", "경질캡슐", "현탁액",
    "점안액", "점이액", "서방정", "츄정", "캡슐", "시럽", "세립", "과립", "크림", "연고",
    "로션", "좌약", "좌제", "가글", "산", "정", "액",
]  # fmt: skip
# 제형 → 묶음. 단위(정·캡슐·mL)와 맞는지 볼 때 쓴다.
FORM_FAMILY = {
    "정": "tablet", "필름코팅정": "tablet", "서방정": "tablet", "츄정": "tablet",
    "캡슐": "capsule", "연질캡슐": "capsule", "경질캡슐": "capsule",
    "시럽": "liquid", "건조시럽": "liquid", "현탁액": "liquid", "액": "liquid", "가글": "liquid",
    "산": "powder", "세립": "powder", "과립": "powder", "드라이시럽": "powder",
    "점안액": "drops", "점이액": "drops",
    "크림": "topical", "연고": "topical", "로션": "topical",
    "나잘스프레이": "spray", "좌약": "suppository", "좌제": "suppository",
}  # fmt: skip
# 약봉투 1회 단위 → 그 단위를 쓰는 제형 묶음. 표에 없는 단위는 확인하지 않는다.
UNIT_FAMILIES = {
    "정": {"tablet"},
    "캡슐": {"capsule"},
    "ml": {"liquid", "drops"},
    "방울": {"drops"},
    "포": {"powder", "liquid"},  # 건조시럽을 포로 주기도 한다
    "g": {"powder", "liquid", "topical"},
}
UNIT_WORDS = [("밀리그램", "mg"), ("밀리그람", "mg"), ("밀리그림", "mg"), ("밀리리터", "ml"),
              ("마이크로그램", "mcg"), ("그램", "g")]  # fmt: skip
SALT_WORDS = r"(염산염|말레산염|황산염|인산염|수화물|나트륨|칼륨|칼슘)"
STRENGTH_RE = re.compile(r"(\d+(?:\.\d+)?)(mg|mcg|ml|g|%|iu)$")
COLOR_WORDS = ["흰색", "백색", "분홍색", "빨간색", "주황색", "노란색", "황색", "녹색", "초록색",
               "파란색", "청색", "보라색", "갈색", "회색", "검은색", "투명"]  # fmt: skip
COLOR_SAME = {"백색": "흰색", "황색": "노란색", "초록색": "녹색", "청색": "파란색"}


@dataclass(frozen=True)
class ParsedName:
    stem: str  # 상표 (예: 지스로맥스)
    form: str | None  # 제형 낱말 (예: 정)
    strength: str | None  # 함량 (예: 250mg)
    ingredient: str | None  # 괄호 속 성분 (예: 아지트로마이신)


def _nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text or "")


def normalize_ingredient(text: str | None) -> str | None:
    """'암브록솔염산염' → '암브록솔'. 성분끼리 비교할 때만 쓴다."""
    if not text:
        return None
    s = re.sub(r"\[[^\]]*\]", "", _nfkc(text))  # '[M250781]아지트로마이신' → '아지트로마이신'
    s = re.sub(SALT_WORDS, "", s)
    s = re.sub(r"[\s·,]", "", s).lower()
    return s or None


def parse_name(name: str) -> ParsedName:
    """약 이름을 상표·제형·함량·성분으로 나눈다. 계산하거나 짐작하지 않고 글자만 나눈다.

    '지스로맥스정250mg'                         → 지스로맥스 / 정 / 250mg
    '지스로맥스정250밀리그램(아지트로마이신수화물)' → 지스로맥스 / 정 / 250mg / 아지트로마이신
    '세파클러건조시럽(내복)/60(1)mL/병'          → 세파클러 / 건조시럽 / - / -
    """
    s = _nfkc(name).split("/")[0]  # '/' 뒤는 포장 규격(60(1)mL/병)이라 버린다
    inside = re.findall(r"\(([^()]*)\)", s)
    # 괄호 속 글자가 성분 이름처럼 생겼을 때만 성분으로 본다 (숫자·내복·외용 제외)
    ingredient = next(
        (normalize_ingredient(x) for x in inside if re.search(r"[가-힣a-zA-Z]{2}", x) and x not in ("내복", "외용")),
        None,
    )
    s = re.sub(r"\([^()]*\)", "", s)
    for word, unit in UNIT_WORDS:
        s = s.replace(word, unit)
    s = re.sub(r"\s", "", s).lower()
    m = STRENGTH_RE.search(s)
    strength = None
    if m:
        strength = f"{float(m.group(1)):g}{m.group(2)}"
        s = s[: m.start()]
    form = next((w for w in FORM_WORDS if s.endswith(w) and len(s) > len(w)), None)
    stem = s[: -len(form)] if form else s
    return ParsedName(stem=stem, form=form, strength=strength, ingredient=ingredient)


def _unit_key(unit: str | None) -> str | None:
    u = _nfkc(unit or "").strip().lower()
    return u or None


def _colors(text: str | None) -> set[str]:
    t = _nfkc(text or "")
    return {COLOR_SAME.get(c, c) for c in COLOR_WORDS if c in t}


def _edit_distance_le1(a: str, b: str) -> bool:
    """두 글자열이 한 글자 차이(바꿈·빠짐·더함) 이하인지."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b, strict=True)) == 1
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return any(long_[:i] + long_[i + 1 :] == short for i in range(len(long_)))


# ------------------------------------------------------------------ 분류 이름 → 보호자에게 보일 낱말


def clean_printed_class(text: str | None) -> str | None:
    """약봉투에 인쇄된 분류 '[항생제]' → '항생제'."""
    s = re.sub(r"[\[\]【】]", "", _nfkc(text or "")).strip()
    return s or None


# 식약처 분류번호(3자리) → 화면 낱말. 공식 분류표와 대조해 확인한 것만 넣는다. 없으면 데이터의 분류명을 그대로 쓴다.
# TODO(검수): 받은 데이터의 분류번호·분류명으로 다시 확인하고 MVP 질환에 나오는 분류를 채운다.
CLASS_LABEL_BY_NO: dict[str, str] = {
    "114": "해열진통제",
    "141": "항히스타민제",
    "222": "진해거담제",
}
CLASS_LABEL_BY_PREFIX: dict[str, str] = {
    "61": "항생제",  # 61x 항생물질제제
}

# ATC 코드 앞부분 → 화면 낱말. 가장 길게 맞는 앞부분을 쓴다. ATC는 WHO 국제 분류라 나라마다 같다.
# 표에 없는 코드는 분류를 짐작하지 않는다(None). MVP 질환 약이 나오면 확인해서 늘린다.
# TODO(검수): 팀이 공식 ATC 분류명과 대조해 확인한다.
ATC_LABELS: dict[str, str] = {
    "J01": "항생제",  # 전신용 항균제
    "N02B": "해열진통제",  # 아세트아미노펜 등
    "M01A": "해열진통소염제",  # 이부프로펜 등 비스테로이드 소염진통제
    "R05C": "거담제",  # 암브록솔·에르도스테인 등
    "R05D": "진해제",  # 기침 억제
    "R06A": "항히스타민제",
    "A07F": "정장제",  # 장내 미생물 제제
    "A01AB": "구강소독제",  # 클로르헥시딘 가글 등 — 삼키는 약이 아니다
    "R02AA": "인후소독제",  # 헥사메딘액(클로르헥시딘) 등 목 가글 — 삼키는 약이 아니다
    "D07": "피부 스테로이드",
    "S01A": "항생 점안제",
}


def atc_label(atc_code: str | None) -> str | None:
    codes = re.findall(r"[A-Z]\d{2}[A-Z0-9]*", _nfkc(atc_code or "").upper())
    labels = set()
    for code in codes:  # 한 칸에 코드가 여러 개면 모두 같은 분류일 때만 쓴다
        prefix = max((p for p in ATC_LABELS if code.startswith(p)), key=len, default=None)
        labels.add(ATC_LABELS[prefix] if prefix else None)
    return labels.pop() if len(labels) == 1 else None


# 화면 낱말 → 약봉투 효능 문장에 하나는 들어 있어야 하는 말. 문장이 있는데 하나도 없으면 분류를 버린다.
EFFICACY_WORDS: dict[str, list[str]] = {
    "항생제": ["세균", "감염", "항생", "폐렴", "균"],
    "해열진통제": ["열", "통증", "아픔", "진통"],
    "진해거담제": ["기침", "가래"],
    "거담제": ["가래"],
    "항히스타민제": ["알레르기", "가려", "콧물", "두드러기"],
    "해열진통소염제": ["열", "통증", "염증", "아픔"],
    "진해제": ["기침"],
    "정장제": ["장", "설사", "변"],
    "구강소독제": ["입", "구강", "목", "가글", "헹", "소독"],
    "인후소독제": ["입", "구강", "목", "가글", "헹", "소독"],
}


def class_label(class_no: str | None, class_name: str | None) -> str | None:
    """분류번호·분류명 → 화면 낱말.

    분류번호는 '222'처럼 오기도 하고 '[02220]진해거담제'처럼 이름이 붙어 오기도 해서 둘 다 받는다.
    앞의 0을 떼고 앞 3자리를 식약처 분류번호로 본다 ('02220' → '222').
    """
    raw = _nfkc(class_no or "")
    no = re.sub(r"\D", "", raw).lstrip("0")[:3]
    if no in CLASS_LABEL_BY_NO:
        return CLASS_LABEL_BY_NO[no]
    for prefix, label in CLASS_LABEL_BY_PREFIX.items():
        if no.startswith(prefix):
            return label
    name = class_name or re.sub(r"[\[\]\d\s]", "", raw)  # '[02220]진해거담제' → '진해거담제'
    name = re.sub(r"^\[?\d+\]?\s*", "", _nfkc(name)).strip()
    return name or None


# ------------------------------------------------------------------ 허가정보 데이터


@dataclass(frozen=True)
class DrugRecord:
    item_name: str  # 공식 품목명
    class_no: str | None = None  # 식약처 분류번호
    class_name: str | None = None
    ingredient: str | None = None  # 주성분
    edi_code: str | None = None  # 보험코드
    chart: str | None = None  # 성상
    atc_code: str | None = None  # WHO ATC 코드 (식약처 허가 상세정보에 있음)
    parsed: ParsedName = field(init=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "parsed", parse_name(self.item_name))

    @property
    def label(self) -> str | None:
        """ATC 코드가 있으면 ATC로, 없으면 식약처 분류번호로 정한다."""
        if self.atc_code:
            return atc_label(self.atc_code)
        return class_label(self.class_no, self.class_name)

    @property
    def form_family(self) -> str | None:
        return FORM_FAMILY.get(self.parsed.form or "")


# 파일의 열 이름 → DrugRecord 칸. app/scripts/build_drug_data.py가 만드는 파일(식약처 API 항목 이름)에 맞춰 두었다.
# 다른 파일을 쓰면 그 파일의 열 이름으로 바꾼다. 파일에 없는 열은 빈 값이 된다.
COLUMN_MAP: dict[str, str] = {
    "item_name": "ITEM_NAME",
    "class_no": "CLASS_NO",
    "class_name": "CLASS_NAME",
    "ingredient": "MAIN_ITEM_INGR",
    "edi_code": "EDI_CODE",
    "chart": "CHART",
    "atc_code": "ATC_CODE",
}
DRUG_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "drug_permit.csv"  # app/data/drug_permit.csv


def load_records(path: str | Path, column_map: Mapping[str, str] = COLUMN_MAP) -> list[DrugRecord]:
    """공공데이터 CSV → DrugRecord 목록. 공공데이터 파일은 cp949인 경우가 많아 둘 다 시도한다."""
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "cp949"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"인코딩을 알 수 없어요: {path}")
    rows = csv.DictReader(io.StringIO(text, newline=""))  # 따옴표 안 줄바꿈(성상 등)이 있어도 한 줄로 읽는다
    out = []
    for row in rows:
        values = {k: (row.get(col) or "").strip() or None for k, col in column_map.items()}
        if values.get("item_name"):
            out.append(DrugRecord(**values))  # type: ignore[arg-type]
    return out


class DrugIndex:
    def __init__(self, records: Iterable[DrugRecord]):
        records = list(records)
        self.size = len(records)
        self.by_stem: dict[str, list[DrugRecord]] = defaultdict(list)
        self.by_ingredient: dict[str, list[DrugRecord]] = defaultdict(list)
        self.by_edi: dict[str, list[DrugRecord]] = defaultdict(list)
        for r in records:
            if r.parsed.stem:
                self.by_stem[r.parsed.stem].append(r)
            ingr = normalize_ingredient(r.ingredient) or r.parsed.ingredient
            if ingr:
                self.by_ingredient[ingr].append(r)
            for code in re.findall(r"\d{9}", r.edi_code or ""):  # 한 칸에 여러 코드가 들어 있기도 하다
                self.by_edi[code].append(r)


# ------------------------------------------------------------------ 조회 결과


@dataclass(frozen=True)
class Efficacy:
    label: str
    source: Source
    match: Match

    def as_dict(self) -> dict[str, str]:
        """프론트 efficacyOf()가 읽는 모양: { label, source, match }"""
        return {"label": self.label, "source": self.source, "match": self.match}


@dataclass
class Lookup:
    """이름 조회 한 번의 결과. efficacy가 None이면 reason에 이유가 남는다(로그·보강용)."""

    efficacy: Efficacy | None
    reason: str
    candidates: list[DrugRecord] = field(default_factory=list)


def _efficacy_text_ok(label: str, efficacy_text: str | None) -> bool:
    words = EFFICACY_WORDS.get(label)
    if not words or not efficacy_text:
        return True  # 확인할 근거가 없으면 막지 않는다
    return any(w in efficacy_text for w in words)


def _gather(index: DrugIndex, p: ParsedName) -> tuple[list[DrugRecord], str]:
    """후보 모으기: 상표 → 괄호 속 성분 → 상표 한 글자 오타 순서. (후보, 어떻게 모았는지)"""
    cands = list(index.by_stem.get(p.stem, []))
    if cands:
        return cands, "stem"
    if p.ingredient and index.by_ingredient.get(p.ingredient):
        return list(index.by_ingredient[p.ingredient]), "ingredient"
    if len(p.stem) >= 4:
        near = [s for s in index.by_stem if _edit_distance_le1(s, p.stem)]
        if len(near) == 1:
            return list(index.by_stem[near[0]]), "fuzzy"
    return [], "none"


def _keep(cands: list[DrugRecord], same: Any, unknown: Any) -> tuple[list[DrugRecord], bool]:
    """same(후보)가 참이거나 unknown(후보)가 참(비교할 값이 없음)인 후보만 남긴다. (남은 후보, 맞는 후보가 있었는지)"""
    kept = [c for c in cands if same(c) or unknown(c)]
    return kept, any(same(c) for c in kept)


def _narrow(
    cands: list[DrugRecord], p: ParsedName, unit: str | None, chart: str | None
) -> tuple[list[DrugRecord], set[str]]:
    """제형·함량·단위·성상 색으로 후보를 줄인다. 값을 모르는 후보는 빼지 않는다. (남은 후보, 맞은 근거)"""
    checks = []
    fam = FORM_FAMILY.get(p.form or "")
    if fam:  # 이름의 제형과 같은 묶음
        checks.append(("form", lambda c: c.form_family == fam, lambda c: c.form_family is None))
    if p.strength:  # 이름의 함량과 같은 함량
        checks.append(("strength", lambda c: c.parsed.strength == p.strength, lambda c: c.parsed.strength is None))
    allowed = UNIT_FAMILIES.get(_unit_key(unit) or "")
    if allowed:  # 약봉투의 1회 단위를 쓰는 제형
        checks.append(("unit", lambda c: c.form_family in allowed, lambda c: c.form_family is None))
    bag_colors = _colors(chart)
    if bag_colors:  # 성상의 색이 하나라도 겹침
        checks.append(("chart", lambda c: bool(_colors(c.chart) & bag_colors), lambda c: not _colors(c.chart)))

    evidence: set[str] = set()
    for name, same, unknown in checks:
        cands, matched = _keep(cands, same, unknown)
        if matched:
            evidence.add(name)
    return cands, evidence


def _single_label(cands: list[DrugRecord]) -> tuple[str | None, str]:
    """후보가 모두 같은 분류면 (그 분류, 'ok'), 아니면 (None, 이유)."""
    if not cands:
        return None, "교차 확인에서 모든 후보가 빠졌어요"
    unknown = sorted({c.atc_code or c.class_no or "분류 정보 없음" for c in cands if c.label is None})
    if unknown:
        return None, f"분류 표에 없는 후보가 있어요: {', '.join(unknown)}"
    labels = sorted({c.label for c in cands if c.label})
    if len(labels) > 1:
        return None, f"후보의 분류가 서로 달라요: {labels}"
    return labels[0], "ok"


def _match_kind(by: str, count: int) -> Match:
    if by in ("fuzzy", "ingredient"):
        return by  # type: ignore[return-value]
    return "exact" if count == 1 else "class_agree"


def find_by_name(
    index: DrugIndex,
    name: str,
    *,
    unit: str | None = None,
    chart: str | None = None,
    efficacy_text: str | None = None,
) -> Lookup:
    """약 이름(+약봉투의 단위·성상·효능 문장)으로 분류를 찾는다. 애매하면 efficacy=None."""
    p = parse_name(name)
    if not p.stem:
        return Lookup(None, "이름이 비어 있어요")
    cands, by = _gather(index, p)
    if not cands:
        return Lookup(None, "같은 이름의 품목이 없어요")

    cands, evidence = _narrow(cands, p, unit, chart)
    label, reason = _single_label(cands)
    if label is None:
        return Lookup(None, reason, cands)
    if by == "fuzzy" and (len(cands) > 1 or len(evidence) < 2):
        return Lookup(None, "오타로 보이는 이름인데 확인 근거가 부족해요", cands)
    if not _efficacy_text_ok(label, efficacy_text):
        return Lookup(None, f"약봉투 효능 문장과 분류({label})가 맞지 않아요", cands)
    return Lookup(Efficacy(label, "name_lookup", _match_kind(by, len(cands))), "ok", cands)


def find_by_insurance_code(index: DrugIndex, code: str | None) -> Efficacy | None:
    """처방전 보험코드(9자리)로 찾는다. 같은 코드의 품목이 모두 같은 분류일 때만 돌려준다."""
    digits = re.sub(r"\D", "", code or "")
    labels = {r.label for r in index.by_edi.get(digits, [])}
    if len(labels) != 1 or None in labels:
        return None
    label = labels.pop()
    assert label is not None
    return Efficacy(label, "insurance_code", "code")


def efficacy_for(med: Mapping[str, Any], index: DrugIndex | None) -> Efficacy | None:
    """약 1개의 약효 분류.

    med 키: name, insurance_code, printed_class(약봉투 분류), unit, chart(성상), efficacy_text(효능).

    없으면 None — 화면은 '약효 정보 확인 중'으로 둔다.
    """
    printed = clean_printed_class(med.get("printed_class"))
    if printed:
        return Efficacy(printed, "pharmacy_bag", "printed")
    if index is None:
        return None
    by_code = find_by_insurance_code(index, med.get("insurance_code"))
    if by_code:
        return by_code
    return find_by_name(
        index,
        med.get("name") or "",
        unit=med.get("unit"),
        chart=med.get("chart"),
        efficacy_text=med.get("efficacy_text"),
    ).efficacy


@lru_cache(maxsize=1)
def get_drug_index() -> DrugIndex | None:
    """허가정보 파일을 한 번만 읽어 둔다. 파일이 없으면 None — 그래도 약봉투 인쇄 분류는 쓸 수 있다."""
    if not DRUG_DATA_PATH.exists():
        logger.warning("약효 조회 데이터가 없어요(%s). 약봉투에 인쇄된 분류만 씁니다.", DRUG_DATA_PATH)
        return None
    index = DrugIndex(load_records(DRUG_DATA_PATH))
    logger.info("약효 조회 데이터 %d건을 읽었어요.", index.size)
    return index
