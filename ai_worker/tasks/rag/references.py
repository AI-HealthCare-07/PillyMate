"""3단계: 확정된 약 목록 → { medication_id: "참조 정보 요약" }

generate_guide() 안에서 부른다. BE-2는 references를 넘길 필요가 없다.

매칭 순서
  1) 보험코드 → 품목기준코드  (drug_refs.json에 insurance_codes가 있을 때)
  2) 이름 정확히 일치 (정규화 후, 별칭 names 포함)
  3) 비슷한 이름 (difflib 유사도 0.88 이상)
  4) 같은 성분의 대표 문서 (요약에 '성분 기준'이라고 표시)
  5) 없음 → 결과에 넣지 않음 → 가이드에서 '약사 확인'이 켜짐
"""

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

from ai_worker.tasks.rag.normalize import bracket_text, normalize_name

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "data" / "drug_refs.json"
FUZZY_CUTOFF = 0.88
MAX_CHARS = 600  # 약 하나당 LLM에 넣는 최대 글자 수


@dataclass
class Match:
    medication_id: int
    name: str
    method: str  # insurance | exact | fuzzy | ingredient | none
    key: str | None = None
    score: float = 1.0


class DrugRefIndex:
    def __init__(self, path: Path = DEFAULT_PATH):
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"drugs": []}
        # 다 채운 항목만 쓴다. 반쯤 채운 항목이 LLM에 들어가면 근거가 약해짐
        self.drugs = [d for d in data["drugs"] if d.get("status") == "done"]
        self.by_name: dict[str, dict] = {}
        self.by_ingredient: dict[str, dict] = {}
        self.by_insurance: dict[str, dict] = {}
        for d in self.drugs:
            for n in [d["key"], *d.get("names", [])]:
                self.by_name.setdefault(normalize_name(n), d)
            if d.get("ingredient"):
                self.by_ingredient.setdefault(normalize_name(d["ingredient"]), d)
            for code in d.get("insurance_codes", []):
                self.by_insurance[str(code)] = d

    def find(self, med: dict) -> tuple[dict | None, Match]:
        mid, name = med["medication_id"], med.get("name") or ""

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
            if best and best_score >= FUZZY_CUTOFF:
                return best, Match(mid, name, "fuzzy", best["key"], round(best_score, 2))

        ingr = normalize_name(med.get("ingredient") or bracket_text(name))
        if ingr and ingr in self.by_ingredient:
            d = self.by_ingredient[ingr]
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
        f"흔한 부작용: {d['side_effects']}" if d.get("side_effects") else "",
        f"보관: {d['storage']}" if d.get("storage") else "",
    ]
    text = " ".join(p for p in parts if p)
    return text if len(text) <= MAX_CHARS else text[: MAX_CHARS - 1] + "…"


@lru_cache(maxsize=1)
def _default_index() -> DrugRefIndex:
    return DrugRefIndex()


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
            refs[med["medication_id"]] = summarize(d, by_ingredient=(m.method == "ingredient"))
    return refs, report
