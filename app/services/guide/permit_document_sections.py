"""식약처 허가 상세정보(getDrugPrdtPrmsnDtlInq08)의 문서 XML → 가이드 약 정보 초안에 쓸 단락만 고르기.

허가 문서는 길고(주의사항 500~23,000자) 성인 기준이라 그대로 가이드에 넣을 수 없다.
필요한 단락만 고른다. 쓰는 곳:
  - scripts/rag/draft_refs_from_permit.py: 고른 단락을 자르지 않고 LLM 초안·사람 검수에 넘긴다
  - unreviewed_drug_reference.py (가이드 생성 때 '검수 전 정보'): 고른 단락을 칸별로 줄여 600자 요약을 만든다

- 효능효과 문서(EE_DOC_DATA): 전부
- 사용상의 주의사항 문서(NB_DOC_DATA): 아래 PICK의 단락만. 상호작용·임부·고령자·과량투여는 뺀다
- 용법용량 문서(UD_DOC_DATA)는 읽지 않는다 (NFR-SAFE-002: 용량은 처방·약봉투를 따른다)
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

# (분류, 단락 제목에 들어 있으면 고르는 말). 위에서부터 처음 맞는 분류에 넣는다.
# 전문의약품('투여하지 말 것')과 일반의약품('복용하지 말 것') 문서의 제목이 달라서 둘 다 적는다.
PICK: list[tuple[str, tuple[str, ...]]] = [
    ("warning", ("경고",)),
    ("contraindication", ("투여하지 말 것", "복용하지 말 것", "사용하지 말 것", "금기")),
    ("child", ("소아", "어린이", "영아", "유아", "신생아")),
    ("stop_signs", ("즉각 중지", "즉시 중지", "중지하고")),
    ("side_effects", ("이상반응", "부작용")),
    ("general", ("일반적 주의", "적용상의 주의", "행위를 하지 말 것")),
    ("storage", ("보관", "취급")),
]
SKIP_WORDS = ("상호작용", "임부", "수유부", "고령자", "과량투여", "임상검사치")


@dataclass
class PermitDocument:
    item_seq: str
    item_name: str
    efficacy: str = ""
    sections: dict[str, str] = field(default_factory=dict)  # PICK의 분류 → 단락 글
    storage_method: str = ""  # 허가 정보의 '저장방법' 칸

    def is_empty(self) -> bool:
        return not (self.efficacy or self.sections or self.storage_method)


def _clean(text: str | None) -> str:
    """공백 정리. 원문 CDATA 안에 남은 HTML 태그('<sub>,</sub>')는 지우고 '&lt;'·'&nbsp;'는 글자로 푼다."""
    s = re.sub(r"<[^>]+>", "", text or "")
    s = html.unescape(s).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def articles(doc_xml: str | None) -> list[tuple[str, str]]:
    """문서 XML → [(단락 제목, 단락 글)]. 글은 PARAGRAPH의 CDATA를 이어 붙인다. 읽을 수 없으면 []."""
    if not doc_xml:
        return []
    try:
        root = ET.fromstring(doc_xml)
    except ET.ParseError:
        return []
    out = []
    for art in root.iter("ARTICLE"):
        body = " ".join(_clean(p.text) for p in art.iter("PARAGRAPH") if _clean(p.text))
        out.append((_clean(art.get("title")), body))
    return out


def category_of(title: str) -> str | None:
    """단락 제목 → PICK의 분류. 고르지 않는 단락이면 None."""
    if any(w in title for w in SKIP_WORDS):
        return None
    return next((cat for cat, words in PICK if any(w in title for w in words)), None)


def efficacy_text(ee_xml: str | None) -> str:
    """효능효과 문서 → 한 줄. 효능이 단락 제목에만 적힌 문서가 많아 제목과 글을 함께 쓴다."""
    parts = [p for title, body in articles(ee_xml) for p in (title, body) if p]
    return " ".join(parts)


def caution_sections(nb_xml: str | None) -> dict[str, str]:
    """사용상의 주의사항 문서 → {분류: 단락 글}. 같은 분류의 단락은 이어 붙인다.

    자르지 않는다. 이상반응 단락은 앞부분이 임상시험 통계라, 앞에서부터 자르면 흔한 부작용이 빠진다.
    (초안 스크립트는 전부 LLM에 넘기고, 가이드의 실시간 요약은 unreviewed_drug_reference가 칸별로 줄인다)
    """
    picked: dict[str, list[str]] = {}
    for title, body in articles(nb_xml):
        cat = category_of(title)
        if cat:
            picked.setdefault(cat, []).append(f"{title}: {body}" if body else title)
    return {cat: " ".join(texts) for cat, texts in picked.items()}


def permit_document(item: dict) -> PermitDocument:
    """허가 상세 API 응답 항목 1개 → PermitDocument."""
    return PermitDocument(
        item_seq=str(item.get("ITEM_SEQ") or ""),
        item_name=_clean(item.get("ITEM_NAME")),
        efficacy=efficacy_text(item.get("EE_DOC_DATA")),
        sections=caution_sections(item.get("NB_DOC_DATA")),
        storage_method=_clean(item.get("STORAGE_METHOD")),
    )
