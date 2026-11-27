"""확정된 약 목록 → { medication_id: "참조 정보 요약" } (가이드의 약 정보 reference, GUIDE-004)

generate_guide() 안에서 부른다. BE-2는 references를 넘길 필요가 없다.
근거 데이터는 app/data/drug_refs.json (사람이 식약처 허가 문서와 대조해 검수한 요약).
API 서버 이미지에는 app/ 폴더만 들어가므로 코드와 데이터를 모두 app/ 안에 둔다.

매칭 순서
  1) 보험코드 → 그 문서의 제품 (insurance_codes, 또는 허가 CSV에서 문서 품목기준코드의 보험코드)
  2) 이름 정확히 일치 (정규화 후, 별칭 names 포함)
  3) 비슷한 이름 (difflib 유사도 0.88 이상)
  4) 같은 성분 (허가 CSV의 주성분 집합이 문서와 똑같을 때, permit_ingredient_index) → 요약에 '같은 성분' 표시
  5) 같은 성분 이름 (성분 표 merge.ingredient_of 또는 이름 괄호 속 글자) → 요약에 '같은 성분' 표시
  6) 없음 → 결과에 넣지 않음 → 가이드에서 '약사 확인'이 켜짐

3)·5)는 허가 CSV로 약과 문서의 성분을 둘 다 알 때 서로 다르면 쓰지 않는다 (성분이 다른 약에 연결 금지).
4)·5)는 약의 투여 경로(내복·외용)와 문서 제형의 경로가 다르면 쓰지 않는다 (점안액 문서를 먹는 약에 붙이지 않기).
복합제는 성분 집합이 정확히 같을 때만 연결한다. 부분 일치는 쓰지 않는다 (짐작 금지).
"""

import json
import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

from app.services.guide.drug_name_normalize import bracket_text, normalize_name
from app.services.guide.permit_ingredient_index import (
    IngredientSet,
    PermitIngredientIndex,
    default_permit_index,
)

logger = logging.getLogger(__name__)

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "drug_refs.json"  # app/data/drug_refs.json
FUZZY_CUTOFF = 0.88
MAX_CHARS = 600  # 약 하나당 LLM에 넣는 최대 글자 수


@dataclass
class Match:
    medication_id: int
    name: str
    method: str  # insurance | exact | fuzzy | permit_ingredient | ingredient | none
    key: str | None = None
    score: float = 1.0


BY_INGREDIENT_METHODS = ("permit_ingredient", "ingredient")

# 제형 낱말 → 투여 경로. 흡입제처럼 내복·외용으로 나누기 애매한 것은 None (경로 확인을 하지 않음).
EXTERNAL_FORM_WORDS = (
    "점안",
    "점이",
    "이용액",
    "크림",
    "연고",
    "로션",
    "겔",
    "스프레이",
    "좌약",
    "좌제",
    "가글",
    "외용",
    "패취",
    "패치",
)
INHALED_FORM_WORDS = ("흡입", "할러", "네뷸", "에어로", "레스풀", "헬러")


def route_of_form(form: str | None) -> str | None:
    """'점안액' → '외용', '건조시럽' → '내복', '흡입액' → None"""
    if not form or any(w in form for w in INHALED_FORM_WORDS):
        return None
    return "외용" if any(w in form for w in EXTERNAL_FORM_WORDS) else "내복"


class DrugRefIndex:
    def __init__(self, path: Path = DEFAULT_PATH, permit: PermitIngredientIndex | None = None):
        """permit: 허가 CSV 성분 색인. 없으면 성분 확인 없이 이름·성분 표로만 찾는다."""
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        else:  # 데이터가 없으면 모든 약이 '약사 확인'이 된다. 조용히 넘어가지 않게 남긴다
            logger.warning("약 정보 파일이 없어 참조 없이 가이드를 만들어요: %s", path)
            data = {"drugs": []}
        # 다 채운 항목만 쓴다. 반쯤 채운 항목이 LLM에 들어가면 근거가 약해짐
        self.drugs = [d for d in data["drugs"] if d.get("status") == "done"]
        self.by_name: dict[str, dict] = {}
        self.by_ingredient: dict[str, dict] = {}
        self.by_insurance: dict[str, dict] = {}
        self.by_ingredient_set: dict[IngredientSet, list[dict]] = {}
        self.permit = permit
        self.doc_ingredients: dict[str, IngredientSet] = {}  # 문서 key → 성분 집합 (허가 CSV에서)
        for d in self.drugs:
            for n in [d["key"], *d.get("names", [])]:
                self.by_name.setdefault(normalize_name(n), d)
            if d.get("ingredient"):
                self.by_ingredient.setdefault(normalize_name(d["ingredient"]), d)
            for code in d.get("insurance_codes", []):
                self.by_insurance[str(code)] = d
            item = permit.by_seq.get(str(d.get("item_seq") or "")) if permit else None
            if item:
                self.doc_ingredients[d["key"]] = item.ingredients
                self.by_ingredient_set.setdefault(item.ingredients, []).append(d)
                for code in item.edi_codes:
                    self.by_insurance.setdefault(code, d)

    def _conflicts(self, d: dict, med_ingredients: IngredientSet | None) -> bool:
        """약과 문서의 성분을 둘 다 아는데 서로 다르면 True."""
        doc = self.doc_ingredients.get(d["key"])
        return bool(med_ingredients and doc and med_ingredients != doc)

    @staticmethod
    def _route_ok(d: dict, med: dict) -> bool:
        """약의 경로(내복·외용)와 문서 제형의 경로를 둘 다 아는데 서로 다르면 False."""
        med_route = med.get("route")
        doc_routes = {r for f in d.get("dosage_forms", []) if (r := route_of_form(f))}
        return not (med_route in ("내복", "외용") and doc_routes and med_route not in doc_routes)

    def _pick_by_form(self, docs: list[dict], med: dict) -> dict:
        """같은 성분 문서가 여럿이면 제형이 같은 문서를 먼저 쓴다 (시럽 약 → 시럽 문서)."""
        form = med.get("dosage_form")
        return next((d for d in docs if form and form in d.get("dosage_forms", [])), docs[0])

    def find(self, med: dict) -> tuple[dict | None, Match]:
        mid, name = med["medication_id"], med.get("name") or ""

        med_ingredients = self.permit.ingredients_for(med) if self.permit else None

        code = str(med.get("insurance_code") or "")
        if code and code in self.by_insurance:
            d = self.by_insurance[code]
            return d, Match(mid, name, "insurance", d["key"])

        key = normalize_name(name)
        if key in self.by_name:
            d = self.by_name[key]
            return d, Match(mid, name, "exact", d["key"])

        if key:
            best, best_score = None, 0.0
            for cand, d in self.by_name.items():
                s = SequenceMatcher(None, key, cand).ratio()
                if s > best_score:
                    best, best_score = d, s
            if best and best_score >= FUZZY_CUTOFF and not self._conflicts(best, med_ingredients):
                return best, Match(mid, name, "fuzzy", best["key"], round(best_score, 2))

        same = [d for d in self.by_ingredient_set.get(med_ingredients or frozenset(), []) if self._route_ok(d, med)]
        if same:
            d = self._pick_by_form(same, med)
            return d, Match(mid, name, "permit_ingredient", d["key"])

        ingr = normalize_name(med.get("ingredient") or bracket_text(name))
        if ingr and ingr in self.by_ingredient:
            d = self.by_ingredient[ingr]
            if not self._conflicts(d, med_ingredients) and self._route_ok(d, med):
                return d, Match(mid, name, "ingredient", d["key"])

        return None, Match(mid, name, "none", score=0.0)


def summarize(d: dict, by_ingredient: bool = False) -> str:
    """LLM에 넣을 요약. 용법·용량은 넣지 않는다 (NFR-SAFE-002)."""
    src = d.get("source", {})
    head = f"[출처: {src.get('name', '')}"
    if d.get("item_seq"):
        head += f", 품목기준코드 {d['item_seq']}"
    head += "]"
    if by_ingredient:
        head += " (같은 성분의 다른 제품 정보 — 제품별 차이는 약사 확인)"
    parts = [
        head,
        f"성분: {d['ingredient']}" if d.get("ingredient") else "",
        f"효능: {d['efficacy']}" if d.get("efficacy") else "",
        f"주의: {d['cautions']}" if d.get("cautions") else "",
        f"연령 금기(DUR): {d['dur_age_taboo']}" if d.get("dur_age_taboo") else "",
        f"흔한 부작용: {d['side_effects']}" if d.get("side_effects") else "",
        f"보관: {d['storage']}" if d.get("storage") else "",
    ]
    text = " ".join(p for p in parts if p)
    return text if len(text) <= MAX_CHARS else text[: MAX_CHARS - 1] + "…"


@lru_cache(maxsize=1)
def _default_index() -> DrugRefIndex:
    return DrugRefIndex(permit=default_permit_index())


def build_references(medications: list[dict], index: DrugRefIndex | None = None) -> dict[int, str]:
    refs, _ = build_references_with_report(medications, index)
    return refs


def build_references_with_report(
    medications: list[dict], index: DrugRefIndex | None = None
) -> tuple[dict[int, str], list[Match]]:
    index = index or _default_index()
    refs: dict[int, str] = {}
    report: list[Match] = []
    for med in medications:
        d, m = index.find(med)
        report.append(m)
        if d:
            refs[med["medication_id"]] = summarize(d, by_ingredient=m.method in BY_INGREDIENT_METHODS)
    return refs, report
