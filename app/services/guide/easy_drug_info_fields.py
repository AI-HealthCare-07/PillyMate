"""식약처 의약품개요정보(e약은요, getDrbEasyDrugList) 응답 → 가이드 약 정보 초안에 쓸 칸만 고르기.

e약은요는 일반의약품 위주라 전문의약품은 대부분 없다. 있으면 이미 쉬운 말이라 초안의 좋은 근거가 된다.
scripts/rag/draft_refs_from_permit.py가 허가 문서와 함께 LLM·검수 시트에 넘긴다. 서버(가이드 생성)는 쓰지 않는다.

- 쓰는 칸: 효능(efcyQesitm), 경고(atpnWarnQesitm), 주의(atpnQesitm), 부작용(seQesitm), 보관(depositMethodQesitm)
- 안 쓰는 칸: 사용법(useMethodQesitm — 용량은 처방·약봉투를 따른다, NFR-SAFE-002), 상호작용(intrcQesitm — 허가 문서와 맞춰 뺌)
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

EASY_FIELDS: dict[str, str] = {
    "efcyQesitm": "효능",
    "atpnWarnQesitm": "경고",
    "atpnQesitm": "주의",
    "seQesitm": "부작용",
    "depositMethodQesitm": "보관",
}
SKIPPED_FIELDS = ("useMethodQesitm", "intrcQesitm")


def _clean(text: object) -> str:
    s = re.sub(r"<[^>]+>", " ", str(text or ""))  # 태그를 먼저 지운다. 먼저 풀면 '&lt;농가진&gt;'이 태그처럼 지워진다
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class EasyDrugInfo:
    item_seq: str
    item_name: str
    sections: dict[str, str] = field(default_factory=dict)  # EASY_FIELDS의 한글 이름 → 문장

    def is_empty(self) -> bool:
        return not self.sections


def easy_drug_info(item: dict) -> EasyDrugInfo:
    """e약은요 응답 항목 1개 → EasyDrugInfo. 사용법·상호작용 칸은 버린다."""
    sections = {label: text for key, label in EASY_FIELDS.items() if (text := _clean(item.get(key)))}
    return EasyDrugInfo(str(item.get("itemSeq") or ""), _clean(item.get("itemName")), sections)
