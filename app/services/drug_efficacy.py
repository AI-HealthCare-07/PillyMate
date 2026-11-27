"""약효 분류 찾기 — 식약처 「의약품 제품 허가정보」 상세 조회(getDrugPrdtPrmsnDtlInq08)의 ATC 코드로 찾는다.

흐름
  약 이름 → 식약처 상세 조회 → 맞는 제품 하나 고르기 → ATC_CODE → 보호자용 이름(해열진통제 등)
  ATC 코드가 없으면 영문 주성분(MAIN_INGR_ENG)을 DATA-REF-007 ingredient_to_class와 같은 표로 바꾼다.
  어느 쪽도 안 되면 None → 화면에서 배지를 숨긴다.

원칙
- 분류 이름은 WHO ATC 분류에서 옮긴 아래 표로만 정한다. LLM이 쓰지 않는다 (NFR-SAFE-002).
- 제품이 하나로 정해지지 않으면(이름이 비슷한 제품이 여러 개, ATC가 서로 다름) 짐작하지 않고 None.
- 외부 API가 느리거나 실패해도 처방 조회는 그대로 된다 (짧은 타임아웃, 실패하면 None).
- 같은 약을 매번 묻지 않게 프로세스 메모리에 기억한다 (찾음: 7일, 실패: 1시간).
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Literal

import httpx

from app.core import config

logger = logging.getLogger(__name__)

DETAIL_OPERATION = "getDrugPrdtPrmsnDtlInq08"
TIMEOUT_SECONDS = 5
FOUND_TTL = 7 * 24 * 3600
MISS_TTL = 3600
MAX_CONCURRENT = 5

Source = Literal["mfds_atc", "mfds_ingredient"]


@dataclass(frozen=True)
class Efficacy:
    label: str
    atc_code: str | None
    source: Source


# ------------------------------------------------------------------ ATC 코드 → 보호자용 이름
# 긴 코드(더 구체적인 분류)가 먼저 맞도록 길이순으로 찾는다. 표에 없는 계열은 None.
ATC_LABELS: dict[str, str] = {
    # 해열·진통
    "N02BE": "해열진통제",  # 아세트아미노펜
    "N02B": "해열진통제",
    "M01AE": "해열진통소염제",  # 이부프로펜, 덱시부프로펜
    "M01A": "소염진통제",
    # 감염
    "J01": "항생제",
    "J02": "항진균제",
    "J05": "항바이러스제",
    # 호흡기
    "R05C": "가래약(거담제)",
    "R05D": "기침약(진해제)",
    "R05": "기침·가래약",
    "R06": "항히스타민제",
    "R03": "기관지·천식약",
    "R01": "코 막힘약",
    # 소화기
    "A07F": "정장제",
    "A07D": "지사제",
    "A07X": "지사제",
    "A07B": "지사제",
    "A07": "설사·장염약",
    "A09": "소화제",
    "A04": "구토 억제제",
    "A03F": "위장운동조절제",
    "A03": "위장약",
    "A02": "위장약",
    "A06": "변비약",
    # 피부
    "D11AH": "아토피 피부염약",
    "D07": "피부 스테로이드제",
    "D06": "피부 항생제",
    "D01": "피부 항진균제",
    # 눈·귀
    "S01AA": "항생제 안약",
    "S01AE": "항생제 안약",
    "S01G": "알레르기 안약",
    "S01": "안약",
    "S02": "귀약",
    "S03": "눈·귀약",
    # 기타
    "H02": "스테로이드제",
}
_ATC_PREFIXES = sorted(ATC_LABELS, key=len, reverse=True)

# ATC 코드가 비어 있을 때만 쓰는 성분 표 (DATA-REF-007 ingredient_to_class와 같은 성분)
INGREDIENT_LABELS: dict[str, str] = {
    "acetaminophen": "해열진통제",
    "ibuprofen": "해열진통소염제",
    "dexibuprofen": "해열진통소염제",
    "amoxicillin": "항생제",
    "cefaclor": "항생제",
    "clarithromycin": "항생제",
    "saccharomyces boulardii": "정장제",
    "racecadotril": "지사제",
    "cetirizine": "항히스타민제",
    "ambroxol": "가래약(거담제)",
    "levodropropizine": "기침약(진해제)",
    "hydrocortisone": "피부 스테로이드제",
    "desonide": "피부 스테로이드제",
    "pimecrolimus": "아토피 피부염약",
    "tobramycin": "항생제 안약",
}

_ATC_PATTERN = re.compile(r"[A-Z]\d{2}[A-Z]{0,2}\d{0,2}")


def atc_codes_of(value: Any) -> list[str]:
    """'N02BE01' 또는 'N02BE01, R05X' 같은 값 → ['N02BE01', 'R05X']"""
    return _ATC_PATTERN.findall(str(value or "").upper())


def label_from_atc(code: str) -> str | None:
    return next((ATC_LABELS[p] for p in _ATC_PREFIXES if code.startswith(p)), None)


def label_from_ingredient(value: Any) -> str | None:
    """'Acetaminophen' 또는 '[M040353]Acetaminophen' → 표에 있으면 이름. 복합 성분은 모두 같은 분류일 때만."""
    parts = [re.sub(r"\[[^\]]*\]", "", p).strip().lower() for p in re.split(r"[|,/;]", str(value or ""))]
    labels = {INGREDIENT_LABELS.get(p) for p in parts if p}
    labels.discard(None)
    if len(labels) == 1 and all(INGREDIENT_LABELS.get(p) for p in parts if p):
        return labels.pop()
    return None


def efficacy_of_item(item: dict[str, Any]) -> Efficacy | None:
    codes = atc_codes_of(item.get("ATC_CODE"))
    labels = {label_from_atc(c) for c in codes}
    labels.discard(None)
    if len(labels) == 1:
        return Efficacy(label=labels.pop(), atc_code=codes[0], source="mfds_atc")
    if codes and len(labels) > 1:
        return None  # 서로 다른 분류가 섞인 복합제는 짐작하지 않는다
    label = label_from_ingredient(item.get("MAIN_INGR_ENG"))
    return Efficacy(label=label, atc_code=None, source="mfds_ingredient") if label else None


# ------------------------------------------------------------------ 약 이름으로 제품 하나 고르기
_BRACKETS = re.compile(r"[\(\[（【].*?[\)\]）】]")
_STRENGTH = re.compile(r"\d+(\.\d+)?\s*(mg|g|ml|mcg|μg|iu|%|밀리그램|그램)(\s*/\s*\d*(\.\d+)?\s*(ml|g))?", re.I)
_SPACES = re.compile(r"[\s_\-·.,/`]+")


def search_name(name: str) -> str:
    """식약처에 보낼 검색어: '챔프시럽(아세트아미노펜) 32mg/mL' → '챔프시럽'"""
    s = _BRACKETS.sub("", name)
    s = _STRENGTH.sub("", s)
    return s.strip()


def normalize(name: Any) -> str:
    return _SPACES.sub("", search_name(str(name or ""))).lower()


def pick_item(items: list[dict[str, Any]], name: str, insurance_code: str | None) -> dict[str, Any] | None:
    """검색 결과에서 이 약에 해당하는 제품 하나. 하나로 정해지지 않으면 None."""
    live = [i for i in items if not i.get("CANCEL_DATE")] or items
    if insurance_code:
        hit = [i for i in live if insurance_code in str(i.get("EDI_CODE") or "")]
        if len(hit) == 1:
            return hit[0]
    exact = [i for i in live if normalize(i.get("ITEM_NAME")) == normalize(name)]
    if len(exact) == 1:
        return exact[0]
    if len(live) == 1:
        return live[0]
    # 같은 이름의 용량만 다른 제품들처럼, 후보의 ATC가 모두 같으면 그 분류로 본다
    candidates = exact or live
    codes = {tuple(atc_codes_of(i.get("ATC_CODE"))) for i in candidates}
    if candidates and len(codes) == 1 and next(iter(codes)):
        return candidates[0]
    return None


# ------------------------------------------------------------------ 식약처 호출 + 기억
_cache: dict[str, tuple[float, Efficacy | None]] = {}


def _items_of(data: Any) -> list[dict[str, Any]]:
    body = (data or {}).get("body") or {}
    items = body.get("items") or []
    if isinstance(items, dict):  # 결과가 1건이면 dict로 올 때가 있다
        items = items.get("item") or []
    return items if isinstance(items, list) else [items]


async def _fetch_items(client: httpx.AsyncClient, query: str, limit: asyncio.Semaphore) -> list[dict[str, Any]]:
    params = {"serviceKey": config.MFDS_API_KEY, "type": "json", "pageNo": 1, "numOfRows": 20, "item_name": query}
    async with limit:
        res = await client.get(f"{config.MFDS_PERMIT_URL}/{DETAIL_OPERATION}", params=params)
    res.raise_for_status()
    return _items_of(res.json())


async def find_efficacy(
    client: httpx.AsyncClient, limit: asyncio.Semaphore, name: str, insurance_code: str | None = None
) -> Efficacy | None:
    key = f"{normalize(name)}|{insurance_code or ''}"
    cached = _cache.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    query = search_name(name)
    result: Efficacy | None = None
    ttl = MISS_TTL
    if query:
        try:
            item = pick_item(await _fetch_items(client, query, limit), name, insurance_code)
            result = efficacy_of_item(item) if item else None
            ttl = FOUND_TTL if result else MISS_TTL
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("약효 조회 실패 (%s): %s", query, e)
    _cache[key] = (time.monotonic() + ttl, result)
    return result


def enabled() -> bool:
    return bool(getattr(config, "MFDS_API_KEY", None) and getattr(config, "MFDS_PERMIT_URL", None))


async def efficacy_for_medications(medications: list[Any]) -> dict[int, Efficacy]:
    """Medication 목록 → { medication_id: Efficacy }. 찾지 못한 약은 빠진다. 키가 없으면 빈 dict."""
    if not medications or not enabled():
        return {}
    limit = asyncio.Semaphore(MAX_CONCURRENT)
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
        results = await asyncio.gather(*(find_efficacy(client, limit, m.name, m.insurance_code) for m in medications))
    return {m.id: r for m, r in zip(medications, results, strict=True) if r}
