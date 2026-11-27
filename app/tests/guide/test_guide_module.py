"""가이드 모듈 테스트 (진짜 LLM 없이 가짜 LLM으로).

확인하는 것
1. 정상 답 → 스키마에 맞는 가이드, status "ok"
2. 템플릿에 없는 문장 id → 걸러진다
3. 망가진 JSON / LLM 호출 실패 → 서비스가 멈추지 않고 fallback 가이드, 모든 약에 약사 확인
4. 약을 빠뜨린 답 → fallback
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.services.guide.generator import RESOURCE_DIR, generate, load
from app.services.guide.llm_client import LLMCallError

DISEASE_GROUP = "cold_bronchitis"

# 가상 데이터 15번과 비슷한 입력: 기침감기, 3세 7개월, 약 2개 (해열제는 필요시)
CHILD = {"birth_date": "2023-04-02", "weight_kg": 16.9, "allergies": []}
PRESCRIPTION = {
    "prescription_id": 15,
    "diagnosis_user_input": "기침감기",
    "symptom_notes": "기침, 콧물",
    "prescription_date": "2026-11-19",
}
MEDS: list[dict[str, Any]] = [
    {
        "medication_id": 1,
        "name": "세토펜현탁액",
        "dosage_form": "현탁액",
        "route": "내복",
        "dose_per_time": 5.0,
        "unit": "mL",
        "as_needed": True,
        "daily_count": None,
        "max_daily_count": 4,
        "min_interval_h": 4,
        "total_days": 3,
        "usage": "열날 때 4시간 간격",
        "ingredient": "acetaminophen",
        "storage": None,
        "pharmacy_caution": None,
        "has_pharmacy_info": False,
    },
    {
        "medication_id": 2,
        "name": "뮤코펙트시럽",
        "dosage_form": "시럽",
        "route": "내복",
        "dose_per_time": 4.0,
        "unit": "mL",
        "as_needed": False,
        "daily_count": 3,
        "max_daily_count": None,
        "min_interval_h": None,
        "total_days": 3,
        "usage": "1일 3회 식후 30분",
        "ingredient": "ambroxol",
        "storage": None,
        "pharmacy_caution": None,
        "has_pharmacy_info": False,
    },
]
REFS = {1: "약국 안내(약봉투): [해열진통제] 열을 내려요", 2: "약국 안내(약봉투): [거담제] 가래를 묽게 해요"}


def _template_ids() -> list[str]:
    tpl = load(f"DATA-REF-006_{DISEASE_GROUP}.json")
    return [i["id"] for s in tpl.get("sections", []) for i in s["items"]]


def _mock_answer() -> dict[str, Any]:
    picks = [{"template_item_id": i, "personal_note": None} for i in _template_ids()[:2]]
    picks.append({"template_item_id": "made.up.item", "personal_note": None})  # 함정: 템플릿에 없는 id
    return {
        "summary": "3세 7개월 아이의 오늘 처방은 약 2가지이고, 열날 때만 먹이는 해열제가 있어요. 기침과 콧물이 있어요.",
        "medications": [
            {
                "medication_id": m["medication_id"],
                "purpose": "처방받은 약",
                "how_to_give": ["정해진 양을 먹이세요."],
                "cautions": [],
                "common_side_effects": [],
                "storage": None,
                "pharmacist_check_needed": False,
                "pharmacist_check_reason": None,
            }
            for m in MEDS
        ],
        "home_care_picks": picks,
    }


def _run(call_llm: Any) -> dict[str, Any]:
    return generate(call_llm, CHILD, PRESCRIPTION, MEDS, REFS, DISEASE_GROUP, llm_label="mock")


def _assert_schema(guide: dict[str, Any]) -> None:
    schema_path = RESOURCE_DIR / "schema" / "guide_content.schema.json"
    if not schema_path.exists():
        pytest.skip("스키마 파일 없음")
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(guide, json.loads(schema_path.read_text(encoding="utf-8")))


def test_ok_guide_matches_schema() -> None:
    guide = _run(lambda s, u: json.dumps(_mock_answer(), ensure_ascii=False))
    assert guide["status"] == "ok"
    assert guide["child"]["age_months"] == 43  # 2023-04-02 → 2026-11-19
    assert guide["medications"][0]["dose_text"] == "1회 5mL"  # 숫자는 처방 그대로
    _assert_schema(guide)


def test_dict_answer_is_accepted() -> None:
    # call_haiku는 JSON 문자열이 아니라 dict를 돌려준다
    assert _run(lambda s, u: _mock_answer())["status"] == "ok"


def test_made_up_template_id_is_dropped() -> None:
    guide = _run(lambda s, u: _mock_answer())
    ids = [i["template_item_id"] for sec in guide["home_care"]["sections"] for i in sec["items"]]
    assert "made.up.item" not in ids


@pytest.mark.parametrize(
    "bad_llm",
    [
        lambda s, u: "{깨진 JSON",
        lambda s, u: (_ for _ in ()).throw(LLMCallError("timeout")),
        lambda s, u: {**_mock_answer(), "medications": _mock_answer()["medications"][:1]},  # 약 하나 빠뜨림
    ],
)
def test_failure_falls_back(bad_llm: Any) -> None:
    guide = _run(bad_llm)
    assert guide["status"] == "fallback"
    assert all(m["pharmacist_check"]["needed"] for m in guide["medications"])
    _assert_schema(guide)


# ------------------------------------------------------------------ LLM 답 받기: 글자 수만 넘긴 칸은 줄인다


def _llm_answer(purpose: str, how_to_give: list[str] | None = None) -> dict:
    return {
        "summary": "요약이에요.",
        "medications": [
            {
                "medication_id": 1,
                "purpose": purpose,
                "how_to_give": how_to_give if how_to_give is not None else ["식후에 먹여요."],
                "cautions": [],
                "common_side_effects": [],
                "storage": None,
                "pharmacist_check_needed": False,
            }
        ],
        "home_care_picks": [],
    }


def test_too_long_text_is_shortened_not_rejected():
    from app.services.guide.generator import parse_llm_output

    long_purpose = "배가 아프거나 소화가 안 될 때 장의 움직임을 조절해 주는 약이에요. " * 3
    out = parse_llm_output(_llm_answer(long_purpose))
    assert len(out.medications[0].purpose) <= 60
    assert out.medications[0].purpose.endswith("요.")  # 문장 끝에서 잘랐다


def test_other_format_errors_are_still_rejected():
    import pytest
    from pydantic import ValidationError

    from app.services.guide.generator import parse_llm_output

    with pytest.raises(ValidationError):
        parse_llm_output(_llm_answer("짧아요.", how_to_give=[]))  # how_to_give는 1개 이상
