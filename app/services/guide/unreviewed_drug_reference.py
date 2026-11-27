"""검수 문서가 없는 약의 '검수 전' 약 정보 (낮은 단계 reference). 가이드를 만들 때 식약처 API로 찾아 붙인다.

검수된 문서(app/data/drug_refs.json, status done)가 있는 약은 그 문서를 쓰고, 여기는 그 밖의 약만 맡는다.

  처방 약 → 허가 CSV로 성분·대표 품목 찾기 (permit_ingredient_index)
          → 식약처 API: 허가 상세 문서 + DUR 연령 금기 + e약은요 (mfds_drug_info_api)
          → 필요한 단락에서 중요한 문장을 골라 800자 안의 요약 (summarize_unreviewed, important_permit_sentences)

- 요약은 UNREVIEWED_HEADER로 시작한다. prompts.py가 이 글자로 '검수 전 원문'임을 알아보고,
  service.generate_guide()가 이 약의 '약사 확인'을 반드시 켠다 (LLM이 놓쳐도).
- 용법·용량 문서는 읽지 않는다 (NFR-SAFE-002).
- 가이드 전체 제한 시간(60초) 안에 LLM(최대 50초)이 돌아야 해서, 조회는 약끼리 동시에 하고 LOOKUP_BUDGET_SECONDS 안에
  끝난 것만 쓴다. 늦거나 실패한 약은 예전처럼 '참조 정보 없음'(약사 확인)이 된다.
- 결과는 품목기준코드별로 메모리에 캐시한다 (찾음 7일, 못 찾음·오류 1시간). drug_efficacy.py와 같은 방식.
- MFDS_API_KEY가 없으면 아무것도 하지 않는다 (테스트·키 없는 서버).
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass
from typing import Any

import httpx

from app.core import config
from app.services.guide.drug_reference import route_of_form
from app.services.guide.easy_drug_info_fields import EasyDrugInfo
from app.services.guide.important_permit_sentences import Kind, pick_important
from app.services.guide.mfds_drug_info_api import (
    MfdsApiError,
    fetch_dur_age_taboo,
    fetch_easy_drug,
    fetch_permit_document,
)
from app.services.guide.permit_document_sections import PermitDocument
from app.services.guide.permit_ingredient_index import (
    PermitIngredientIndex,
    PermitItem,
    default_permit_index,
    form_word,
    representative_item,
)

logger = logging.getLogger(__name__)

UNREVIEWED_HEADER = "[검수 전 정보"  # prompts.py·service.py가 이 글자로 알아본다
UNREVIEWED_REASON = "검수 전 정보예요. 약사에게 확인해 주세요."  # 80자 이내. prompts.py의 문장과 같게
# 검수 전 요약은 원문 발췌라 검수 문서(drug_reference.MAX_CHARS 600자)보다 덜 빽빽해서 조금 더 준다. 약 5개면 4,000자 정도
UNREVIEWED_MAX_CHARS = 800
MIN_FIELD_CHARS = 30  # 남은 자리가 이보다 작으면 그 칸부터는 넣지 않는다 (빈 '흔한 부작용: …' 방지)
LOOKUP_BUDGET_SECONDS = 6.0
REQUEST_TIMEOUT_SECONDS = 4.0
FOUND_TTL = 7 * 24 * 3600
MISS_TTL = 3600
MAX_WORKERS = 6

# (칸 이름, 최대 글자). 위에서부터 중요한 순서. 전체가 UNREVIEWED_MAX_CHARS를 넘으면 남은 자리만큼만 넣는다.
FIELD_LIMITS: list[tuple[str, int]] = [
    ("효능", 150),
    ("연령 금기(DUR)", 150),
    ("투여 금기", 160),
    ("소아", 140),
    ("경고", 120),
    ("주의(e약은요)", 160),
    ("보관", 80),
    ("흔한 부작용", 150),
]


# 허가 문서 단락이 들어가는 칸 → 중요한 문장 고르기 방식. 효능·DUR·보관은 짧아서 고르지 않는다.
PICKED_FIELDS: dict[str, Kind] = {
    "투여 금기": "caution",
    "소아": "caution",
    "경고": "caution",
    "흔한 부작용": "side_effects",
}


@dataclass
class UnreviewedSources:
    """품목 1개의 원문 묶음."""

    doc: PermitDocument
    age_taboo: str = ""
    easy: EasyDrugInfo | None = None


FetchSources = Callable[[str], "UnreviewedSources | None"]  # 품목기준코드 → 원문 (없으면 None)


def _cut(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def summarize_unreviewed(src: UnreviewedSources, same_product: bool) -> str:
    """원문 묶음 → reference 요약. e약은요(쉬운 말)가 있으면 그 문장을 먼저 쓴다."""
    doc, easy = src.doc, (src.easy.sections if src.easy else {})
    sections = doc.sections
    fields = {
        "효능": easy.get("효능") or doc.efficacy,
        "연령 금기(DUR)": src.age_taboo,
        "투여 금기": sections.get("contraindication", ""),
        "소아": sections.get("child", ""),
        "경고": sections.get("warning", "") or easy.get("경고", ""),
        "주의(e약은요)": easy.get("주의", ""),
        "보관": easy.get("보관") or doc.storage_method or sections.get("storage", ""),
        "흔한 부작용": easy.get("부작용") or sections.get("side_effects", ""),
    }
    head = f"{UNREVIEWED_HEADER} — 식약처 허가정보 원문 발췌{' + e약은요' if src.easy else ''}, 품목 {doc.item_name}]"
    if not same_product:
        head += " (같은 성분의 다른 제품 정보 — 제품별 차이는 약사 확인)"
    out = head
    for name, limit in FIELD_LIMITS:
        room = UNREVIEWED_MAX_CHARS - len(out) - len(name) - 3  # ' 이름: '
        if room < MIN_FIELD_CHARS:
            break
        limit = min(limit, room)
        text = fields[name]
        if name in PICKED_FIELDS:  # 긴 허가 문서 단락: 앞에서 자르지 않고 중요한 문장을 고른다
            text = pick_important(text, limit, PICKED_FIELDS[name])
        if text:
            out += f" {name}: {_cut(text, limit)}"
    return out


def is_unreviewed(reference: str | None) -> bool:
    return bool(reference and reference.startswith(UNREVIEWED_HEADER))


# ------------------------------------------------------------------ 처방 약 → 대표 품목


def target_item(med: dict[str, Any], permit: PermitIngredientIndex) -> tuple[PermitItem | None, bool]:
    """(근거로 쓸 허가 품목, 처방된 그 제품인지). 못 찾거나 투여 경로가 다르면 (None, False)."""
    ingredients, items, how = permit.lookup(med)
    if not ingredients:
        return None, False
    candidates = items or permit.by_ingredients.get(ingredients, [])  # 찾은 품목(같은 상표 등)이 먼저
    item = representative_item(candidates, ingredients, med.get("name") or "")
    if not item:
        return None, False
    med_route, item_route = med.get("route"), route_of_form(form_word(item.item_name))
    if med_route in ("내복", "외용") and item_route and med_route != item_route:
        return None, False  # 귀약에 먹는 약 문서를 붙이지 않기
    return item, how in ("code", "name") and item in items


# ------------------------------------------------------------------ 식약처 API (캐시)

_cache: dict[str, tuple[float, UnreviewedSources | None]] = {}
_cache_lock = threading.Lock()


def fetch_sources(item_seq: str) -> UnreviewedSources | None:
    """품목 1개의 허가 문서·DUR·e약은요. 캐시가 있으면 그것을 쓴다. 허가 문서가 없으면 None."""
    now = time.monotonic()
    with _cache_lock:
        hit = _cache.get(item_seq)
    if hit and hit[0] > now:
        return hit[1]
    result: UnreviewedSources | None = None
    ttl = MISS_TTL
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS) as c:
            doc, _ = fetch_permit_document(c, item_seq)
            if doc and not doc.is_empty():
                result = UnreviewedSources(doc, fetch_dur_age_taboo(c, item_seq))
                try:
                    result.easy = fetch_easy_drug(c, item_seq)
                except (MfdsApiError, httpx.HTTPError) as e:  # e약은요가 안 돼도 허가 문서로 쓴다
                    logger.info("e약은요 조회 실패(%s): %s", item_seq, e)
                ttl = FOUND_TTL
    except (MfdsApiError, httpx.HTTPError) as e:
        logger.warning("식약처 약 정보 조회 실패(%s): %s", item_seq, e)
    with _cache_lock:
        _cache[item_seq] = (time.monotonic() + ttl, result)
    return result


def lookup_enabled() -> bool:
    return bool(config.MFDS_API_KEY)


def unreviewed_references(
    medications: list[dict[str, Any]],
    permit: PermitIngredientIndex | None = None,
    fetch: FetchSources | None = None,
    budget_seconds: float = LOOKUP_BUDGET_SECONDS,
) -> dict[int, str]:
    """{medication_id: 검수 전 요약}. 찾은 약만 들어간다. fetch는 테스트용(기본은 식약처 API)."""
    if fetch is None:
        if not lookup_enabled():
            return {}
        fetch = fetch_sources
    permit = permit or default_permit_index()
    targets = [(m, *target_item(m, permit)) for m in medications]
    targets = [(m, item, same) for m, item, same in targets if item]
    if not targets:
        return {}

    pool = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    futures = {pool.submit(fetch, item.item_seq): (m, same) for m, item, same in targets}
    done, not_done = wait(futures, timeout=budget_seconds)
    pool.shutdown(wait=False, cancel_futures=True)  # 늦은 조회는 기다리지 않는다 (끝나면 캐시에 남는다)
    if not_done:
        logger.warning("식약처 약 정보 조회가 %.0f초 안에 끝나지 않은 약 %d개는 빼요", budget_seconds, len(not_done))

    refs: dict[int, str] = {}
    for fut in done:
        m, same = futures[fut]
        try:
            src = fut.result()
        except Exception:  # 조회 함수 밖 오류도 가이드를 막지 않는다
            logger.exception("검수 전 약 정보 만들기 실패: %s", m.get("name"))
            continue
        if src:
            refs[m["medication_id"]] = summarize_unreviewed(src, same)
    return refs
