"""식약처 공공데이터 API로 약 1개(품목기준코드)의 원문을 받는다: 허가 상세 문서, DUR 연령 금기, e약은요.

가이드 생성(unreviewed_drug_reference.py)과 초안 스크립트(scripts/rag/draft_refs_from_permit.py)가 함께 쓴다.
키는 app/core/config.py: MFDS_API_KEY(허가·DUR), DATA_GO_KR_KEY(e약은요, 비면 MFDS_API_KEY로 시도).
키는 로그·오류 문장에 남기지 않는다.
"""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Iterable

import httpx

from app.core import config
from app.services.guide.easy_drug_info_fields import EasyDrugInfo, easy_drug_info
from app.services.guide.permit_document_sections import PermitDocument, permit_document

PERMIT_DETAIL = "getDrugPrdtPrmsnDtlInq08"
DUR_AGE_TABOO = "getSpcifyAgrdeTabooInfoList03"
EASY_DRUG_LIST = "getDrbEasyDrugList"


class MfdsApiError(RuntimeError):
    """식약처 API가 200이 아니거나 JSON이 아닐 때. 문장에 키는 들어가지 않는다."""


def decoded(key: str | None) -> str:
    """Encoding 키('%2B…')가 들어 있어도 쓸 수 있게 푼다. httpx가 다시 인코딩한다."""
    return urllib.parse.unquote(key) if key and "%" in key else (key or "")


def permit_key() -> str:
    return decoded(config.MFDS_API_KEY)


def easy_key() -> str:
    return decoded(getattr(config, "DATA_GO_KR_KEY", "") or config.MFDS_API_KEY)


def get_items(client: httpx.Client, url: str, key: str, params: dict[str, str]) -> list[dict]:
    res = client.get(url, params={"serviceKey": key, "type": "json", "pageNo": 1, "numOfRows": 10, **params})
    if res.status_code != 200:
        raise MfdsApiError(f"식약처 API {res.status_code}: {res.text[:120].replace(key, '***')}")
    try:
        body = res.json().get("body") or {}
    except ValueError as e:
        raise MfdsApiError("식약처 API 응답이 JSON이 아니에요") from e
    items = body.get("items") or []
    if isinstance(items, dict):  # 결과가 1건이면 dict로 올 때가 있다
        items = items.get("item") or []
    return items if isinstance(items, list) else [items]


def fetch_permit_document(client: httpx.Client, item_seq: str) -> tuple[PermitDocument | None, dict]:
    """(허가 문서, 응답 항목 그대로). 없으면 (None, {})."""
    items = get_items(client, f"{config.MFDS_PERMIT_URL}/{PERMIT_DETAIL}", permit_key(), {"item_seq": item_seq})
    item = next((it for it in items if str(it.get("ITEM_SEQ")) == item_seq), None)
    return (permit_document(item), item) if item else (None, {})


def fetch_dur_age_taboo(client: httpx.Client, item_seq: str) -> str:
    """DUR 특정연령대금기 문장 (원문 그대로, 겹치면 한 번만). 없으면 ''."""
    items = get_items(client, f"{config.MFDS_DUR_URL}/{DUR_AGE_TABOO}", permit_key(), {"itemSeq": item_seq})
    return join_unique(str(it.get("PROHBT_CONTENT") or "") for it in items)


def join_unique(texts: Iterable[str]) -> str:
    """같은 문장이 문장부호·띄어쓰기만 다르게 여러 번 오면 한 번만 남긴다.

    DUR은 성분별로 항목이 따로 와서 '…큼.12세 미만…'과 '…큼, 12세 미만…'이 함께 오기도 한다.
    """
    seen: set[str] = set()
    out: list[str] = []
    for raw in texts:
        text = re.sub(r"\s+", " ", raw).strip()
        key = re.sub(r"[\s.,·]", "", text)
        if text and key not in seen:
            seen.add(key)
            out.append(text)
    return " ".join(out)


def _easy_url() -> str:
    return f"{getattr(config, 'MFDS_EASY_DRUG_URL', '')}/{EASY_DRUG_LIST}"


def fetch_easy_drug(client: httpx.Client, item_seq: str) -> EasyDrugInfo | None:
    """e약은요에 이 품목이 있으면 그 설명. 일반의약품 위주라 전문의약품은 대부분 None."""
    items = get_items(client, _easy_url(), easy_key(), {"itemSeq": item_seq})
    item = next((it for it in items if str(it.get("itemSeq")) == item_seq), None)
    info = easy_drug_info(item) if item else None
    return info if info and not info.is_empty() else None


def search_easy_drugs(client: httpx.Client, item_name: str, rows: int = 30) -> list[dict]:
    """e약은요를 이름(일부)으로 찾기. 응답 항목 그대로."""
    return get_items(client, _easy_url(), easy_key(), {"itemName": item_name, "numOfRows": str(rows)})
