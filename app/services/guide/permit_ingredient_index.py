"""처방 약 → 식약처 허가정보(app/data/drug_permit.csv)의 주성분 집합.

가이드 약 정보(reference)를 '같은 성분' 문서에 연결할 때, 손으로 적은 성분 표(merge.ingredient_of) 대신
허가 데이터로 성분이 정말 같은지 확인한다.

    '세토펜현탁액(아세트아미노펜)/100(1)mL/병' → frozenset({'아세트아미노펜'})

성분 비교는 M코드가 아니라 정리한 성분 이름으로 한다. 같은 성분이 원료 등록에 따라 M코드가 여러 개라서다.
  - 같게 보는 것: 염(염산염·수화물·칼륨·앞에 붙은 염산/황산/인산 …), 원료 모양(제피과립·과립·미분화), 비율 '(4:1)', '묽은'
      '클래리트로마이신제피과립' = '클래리트로마이신', '세파클러수화물' = '세파클러', '황산토브라마이신' = '토브라마이신'
  - 다르게 보는 것: 에스테르 등 다른 성분 — '히드로코르티손부티레이트' ≠ '히드로코르티손' (세기가 다름)

찾는 순서 (lookup)
  1) 보험코드(EDI)
  2) 이름 정확히 일치 (normalize_name 후. '밀리그램'은 'mg'로 맞춘다)
  3) 처방 이름 괄호 속 성분 — '몬테루카스트츄정5밀리그램(몬테루카스트나트륨)' → {'몬테루카스트'}
     허가 데이터에 있는 성분 이름일 때만 (OCR 오타·'(내복)'은 버린다)
  4) 이름 앞에 회사명만 붙은 품목 — '돔페리돈현탁액' → '대원돔페리돈현탁액' 등
     (4글자 이상, 1)·2)에서 아무것도 못 찾았을 때만. 앞에 '복합'이 붙은 품목은 다른 약이라 뺀다: '복합써스펜좌약')
  5) 상표가 같은 품목 — '씨잘시럽' → 상표 '씨잘' → 씨잘정·씨잘액 (2글자 이상, 4)도 못 찾았을 때만)
     허가 데이터에 그 이름 그대로는 없지만 상표로 성분을 알 수 있는 경우 (실제 제품명은 '씨잘액')
1)·2)·4)·5)는 찾은 품목들의 성분 집합이 모두 같을 때만 돌려준다. 다르면 None — 짐작하지 않는다.
CSV가 없으면 색인이 비고, 그러면 호출하는 쪽은 예전처럼 이름·성분 표로만 찾는다.
"""

from __future__ import annotations

import csv
import logging
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.services.drug_lookup import DRUG_DATA_PATH, FORM_FAMILY, UNIT_WORDS, normalize_ingredient, parse_name
from app.services.guide.drug_name_normalize import bracket_text, normalize_name

logger = logging.getLogger(__name__)

IngredientSet = frozenset[str]
_COMPONENT = re.compile(r"\[M\d+\]([^|]+)")  # '[M040353]아세트아미노펜|[M223015]DL-메티오닌'
_EDI_CODE = re.compile(r"\d{9}")
_FORM_WORDS = re.compile(r"제피세립|제피과립|과립|세립|미분화")
# '염산세티리진' = 세티리진염산염, '인산오셀타미비르' = 오셀타미비르인산염. '초산'·'낙산'은 에스테르라 떼지 않는다
_PREFIX_SALTS = ("염산", "황산", "인산")
_HYDRATE = re.compile(r"(일|이|삼|반|세스퀴)?수화물")  # '모메타손푸로에이트일수화물' → '모메타손푸로에이트'
_COMBINATION_PREFIX = "복합"
# 같은 성분의 다른 한글 표기 → 허가 데이터에 많이 쓰인 표기. 허가 데이터에서 품목 수를 세어 확인한 것만 넣는다.
SPELLING_VARIANTS = {
    "클래리스로마이신": "클래리트로마이신",  # 1품목 vs 194품목
    "락툴로오스농축액": "락툴로오즈농축액",  # 7품목 vs 7품목 — 둘 중 하나로 맞춘다
}
CONTAINS_MIN_LEN = 4  # 4)에서 이보다 짧은 이름은 쓰지 않는다 ('시럽'처럼 너무 흔한 말)
STEM_MIN_LEN = 2  # 5)에서 이보다 짧은 상표는 쓰지 않는다


def brand_stem(name: str | None) -> str:
    """약 이름 → 상표 (제형·함량·괄호를 뗀 앞부분). '씨잘정5밀리그램(레보세티리진염산염)' → '씨잘'"""
    return parse_name(name or "").stem


def ingredient_key(name: str) -> str | None:
    """허가 데이터의 성분 이름 1개 → 비교용 이름. '클래리트로마이신 제피과립(42%)' → '클래리트로마이신'"""
    s = unicodedata.normalize("NFKC", name)
    s = re.sub(r"\([^)]*\)", "", s)  # (미분화), (42%), (4:1)
    s = re.sub(r"\d+\s*:\s*\d+", "", s)
    s = _FORM_WORDS.sub("", s)
    s = re.sub(r"\s", "", s).removeprefix("묽은")
    s = _HYDRATE.sub("", s)
    for p in _PREFIX_SALTS:
        if s.startswith(p) and len(s) >= len(p) + 3:  # '인산칼슘'처럼 남는 게 짧으면 떼지 않는다
            s = s[len(p) :]
    key = normalize_ingredient(s)
    return SPELLING_VARIANTS.get(key, key) if key else None


def _split_ingredients(text: str) -> IngredientSet:
    """'아목시실린ㆍ클라불란산칼륨(4:1)' → {'아목시실린', '클라불란산'}"""
    return frozenset(k for part in re.split(r"[ㆍ·,]", text) if (k := ingredient_key(part)))


def ingredient_set(main_item_ingr: str | None) -> IngredientSet:
    """'[M223098]아목시실린수화물|[M248503]묽은클라불란산칼륨' → {'아목시실린', '클라불란산'}

    한 칸에 두 성분이 함께 적힌 '아목시실린ㆍ클라불란산칼륨(4:1)'도 둘로 나눈다.
    """
    keys: set[str] = set()
    for component in _COMPONENT.findall(main_item_ingr or ""):
        keys |= _split_ingredients(component)
    return frozenset(keys)


def name_key(name: str | None) -> str:
    """처방전·약봉투 이름과 허가 품목명을 같은 규칙으로 맞춘다. '/' 뒤(포장 규격)는 버린다.

    '소론도정5밀리그램(프레드니솔론)/1정' → '소론도정'
    """
    s = (name or "").split("/")[0]
    for word, unit in UNIT_WORDS:
        s = s.replace(word, unit)
    return normalize_name(s)


@dataclass(frozen=True)
class PermitItem:
    item_seq: str  # 품목기준코드
    item_name: str
    ingredients: IngredientSet
    edi_codes: tuple[str, ...]


class PermitIngredientIndex:
    def __init__(self, items: Iterable[PermitItem]):
        self.by_seq: dict[str, PermitItem] = {}
        self.by_edi: dict[str, list[PermitItem]] = defaultdict(list)
        self.by_name: dict[str, list[PermitItem]] = defaultdict(list)
        self.by_ingredients: dict[IngredientSet, list[PermitItem]] = defaultdict(list)
        self.by_stem: dict[str, list[PermitItem]] = defaultdict(list)
        self.known_ingredients: set[str] = set()
        for it in items:
            if not it.ingredients:
                continue
            self.by_seq[it.item_seq] = it
            self.by_ingredients[it.ingredients].append(it)
            self.known_ingredients |= it.ingredients
            for code in it.edi_codes:
                self.by_edi[code].append(it)
            key = name_key(it.item_name)
            if key:
                self.by_name[key].append(it)
            stem = brand_stem(it.item_name)
            if len(stem) >= STEM_MIN_LEN:
                self.by_stem[stem].append(it)

    def __len__(self) -> int:
        return len(self.by_seq)

    def lookup(self, med: Mapping[str, Any]) -> tuple[IngredientSet | None, list[PermitItem], str]:
        """처방 약 1개 → (성분 집합 또는 None, 허가 품목 후보, 'code' | 'name' | 'bracket' | 'contains' | 'stem' | 'none')"""
        name = med.get("name") or ""
        items, how = [], "none"
        code = re.sub(r"\D", "", str(med.get("insurance_code") or ""))
        key = name_key(name)
        if code and self.by_edi.get(code):
            items, how = self.by_edi[code], "code"
        elif key and self.by_name.get(key):
            items, how = self.by_name[key], "name"
        if items and (agreed := _agreed(items)):
            return agreed, items, how

        bracket = _split_ingredients(bracket_text(name))
        if bracket and bracket <= self.known_ingredients:
            return bracket, self.by_ingredients.get(bracket, []), "bracket"

        if not items and len(key) >= CONTAINS_MIN_LEN:
            near = [
                it
                for k, its in self.by_name.items()
                if k.endswith(key) and _COMBINATION_PREFIX not in k[: -len(key)]
                for it in its
            ]
            if near:
                return _agreed(near), near, "contains"

        stem = brand_stem(name)
        if not items and len(stem) >= STEM_MIN_LEN and self.by_stem.get(stem):
            same_brand = self.by_stem[stem]
            return _agreed(same_brand), same_brand, "stem"
        return None, items, how

    def ingredients_for(self, med: Mapping[str, Any]) -> IngredientSet | None:
        """처방 약 1개 → 성분 집합. 후보끼리 성분이 다르거나 못 찾으면 None."""
        return self.lookup(med)[0]


def _agreed(items: list[PermitItem]) -> IngredientSet | None:
    """후보들의 성분 집합이 모두 같으면 그 집합, 아니면 None."""
    sets = {it.ingredients for it in items}
    return next(iter(sets)) if len(sets) == 1 else None


# parse_name이 모르는 제형 낱말. '이용액'(귀에 넣는 약)을 '액'(먹는 약)으로 읽지 않게 먼저 찾는다.
EXTRA_FORM_WORDS = ("이용액", "점이액", "점안액", "나잘스프레이", "흡입액", "에보할러", "네뷸", "레스풀", "터부헬러")


def form_word(name: str | None) -> str | None:
    """품목명 → 제형 낱말. '에펙신이용액(오플록사신)' → '이용액', '애니세프세립(세프디니르)' → '세립'"""
    stem = re.split(r"[\(（]", name or "")[0]
    return next((w for w in EXTRA_FORM_WORDS if w in stem), None) or parse_name(name or "").form


def representative_item(items: list[PermitItem], ingredients: IngredientSet, med_name: str) -> PermitItem | None:
    """같은 성분 품목 중 처방된 약과 가장 비슷한 1개 (이 품목의 허가 문서를 근거로 쓴다).

    처방 이름이 품목명 끝에 붙은 것 → 상표가 같고 제형이 같은 것 → 상표가 같고 제형 묶음(물약·정제 …)이 같은 것
    → 제형이 같은 것 → 제형 묶음이 같은 것 → 상표가 같은 것 → 처음 것
    예: '씨잘시럽' → 씨잘액 (씨잘정보다 먼저. 시럽과 액은 같은 물약 묶음)
    """
    same = [it for it in items if it.ingredients == ingredients]
    if not same:
        return None
    key, form, stem = name_key(med_name), form_word(med_name), brand_stem(med_name)
    family = FORM_FAMILY.get(form or "")

    def brand(it: PermitItem) -> bool:
        return (bool(stem) and brand_stem(it.item_name) == stem) or (
            bool(key[:4]) and name_key(it.item_name).startswith(key[:4])
        )

    def same_form(it: PermitItem) -> bool:
        return bool(form) and form_word(it.item_name) == form

    def same_family(it: PermitItem) -> bool:
        return bool(family) and FORM_FAMILY.get(form_word(it.item_name) or "") == family

    for ok in (
        lambda it: bool(key) and name_key(it.item_name).endswith(key),
        lambda it: same_form(it) and brand(it),
        lambda it: same_family(it) and brand(it),
        same_form,
        same_family,
        brand,
    ):
        found = next((it for it in same if ok(it)), None)
        if found:
            return found
    return same[0]


def load_permit_items(path: Path) -> list[PermitItem]:
    """허가정보 CSV → PermitItem 목록. 허가가 취소된 품목은 뺀다."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [
            PermitItem(
                item_seq=(row.get("ITEM_SEQ") or "").strip(),
                item_name=(row.get("ITEM_NAME") or "").strip(),
                ingredients=ingredient_set(row.get("MAIN_ITEM_INGR")),
                edi_codes=tuple(_EDI_CODE.findall(row.get("EDI_CODE") or "")),
            )
            for row in csv.DictReader(f)
            if not (row.get("CANCEL_DATE") or "").strip()
        ]


@lru_cache(maxsize=1)
def default_permit_index() -> PermitIngredientIndex:
    """허가정보 파일을 한 번만 읽어 둔다. 없으면 빈 색인 (가이드는 이름·성분 표로만 찾는다)."""
    if not DRUG_DATA_PATH.exists():
        logger.warning("허가정보 파일이 없어 성분으로 약 정보를 찾지 않아요: %s", DRUG_DATA_PATH)
        return PermitIngredientIndex([])
    return PermitIngredientIndex(load_permit_items(DRUG_DATA_PATH))
