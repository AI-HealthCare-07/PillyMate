"""약효 분류 찾기 (services/drug_efficacy.py). 식약처 API는 부르지 않고 가짜 응답으로 확인한다."""

import asyncio
from collections.abc import Coroutine
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import httpx

from app.services import drug_efficacy as de

FAKE_CONFIG = SimpleNamespace(MFDS_API_KEY="test-key", MFDS_PERMIT_URL="https://mfds.test/DrugPrdtPrmsnInfoService08")
DATA = {
    "챔프시럽": [{"ITEM_NAME": "챔프시럽(아세트아미노펜)", "ATC_CODE": "N02BE01", "EDI_CODE": None}],
    "오구멘틴듀오시럽": [
        {"ITEM_NAME": "오구멘틴듀오시럽228mg/5ml", "ATC_CODE": "J01CR02"},
        {"ITEM_NAME": "오구멘틴듀오시럽457mg/5ml", "ATC_CODE": "J01CR02"},
    ],
    "모호한약": [{"ITEM_NAME": "모호한약A", "ATC_CODE": "J01CA04"}, {"ITEM_NAME": "모호한약B", "ATC_CODE": "N02BE01"}],
    "성분만있는약": [{"ITEM_NAME": "성분만있는약", "ATC_CODE": None, "MAIN_INGR_ENG": "[M1]Cetirizine"}],
}


def _run[T](coro: Coroutine[Any, Any, T]) -> T:
    """asyncio.run()은 끝나면서 '현재 이벤트 루프' 설정을 지워서, 뒤에 도는 DB 테스트(tortoise)가 깨진다.
    그래서 따로 만든 루프에서만 돌리고 현재 루프 설정은 건드리지 않는다."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _handler(request: httpx.Request) -> httpx.Response:
    items = DATA.get(request.url.params["item_name"], [])
    return httpx.Response(200, json={"header": {"resultCode": "00"}, "body": {"items": items}})


def _find(name: str, insurance_code: str | None = None) -> de.Efficacy | None:
    async def run() -> de.Efficacy | None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(_handler)) as client:
            return await de.find_efficacy(client, asyncio.Semaphore(1), name, insurance_code)

    de._cache.clear()
    with patch.object(de, "config", FAKE_CONFIG):
        return _run(run())


def test_atc_prefix_uses_most_specific_label() -> None:
    assert de.label_from_atc("N02BE01") == "해열진통제"
    assert de.label_from_atc("S01AA12") == "항생제 안약"
    assert de.label_from_atc("S01XA20") == "안약"
    assert de.label_from_atc("Z99") is None


def test_name_with_ingredient_and_strength_is_found_by_atc() -> None:
    result = _find("챔프시럽(아세트아미노펜) 32mg/mL")
    assert result == de.Efficacy(label="해열진통제", atc_code="N02BE01", source="mfds_atc")


def test_products_with_same_atc_count_as_one() -> None:
    assert _find("오구멘틴듀오시럽").label == "항생제"  # type: ignore[union-attr]


def test_ambiguous_or_unknown_drug_is_none() -> None:
    assert _find("모호한약") is None
    assert _find("없는약") is None


def test_falls_back_to_main_ingredient_without_atc() -> None:
    result = _find("성분만있는약")
    assert result is not None and result.label == "항히스타민제" and result.source == "mfds_ingredient"


def test_api_failure_is_none() -> None:
    async def run() -> de.Efficacy | None:
        transport = httpx.MockTransport(lambda request: httpx.Response(500))
        async with httpx.AsyncClient(transport=transport) as client:
            return await de.find_efficacy(client, asyncio.Semaphore(1), "챔프시럽")

    de._cache.clear()
    with patch.object(de, "config", FAKE_CONFIG):
        assert _run(run()) is None
