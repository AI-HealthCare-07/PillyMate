"""generate_guide(): 확정 API·DB 모양 입력 → 가이드 (가짜 LLM으로, 키 없이)

입력은 AI-1 OCR 예시(해솔소아청소년과의원, 2026-11-12)를 보호자가 확정한 뒤 DB에 저장된 모양으로 적었다.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.services.guide.generator import RESOURCE_DIR
from app.services.guide.service import disease_groups_of, generate_guide, normalize_medication

CHILD = {"birth_date": "2023-04-02", "weight_kg": 16.9, "allergies": "계란, 우유"}
PRESCRIPTION = {
    "prescription_id": 12,
    "prescription_date": "2026-11-12",
    "diagnosis_user_input": "기침감기",
    "symptom_notes": "기침, 콧물",
}
MEDS: list[dict[str, Any]] = [
    {
        "medication_id": 41,
        "name": "세파클러건조시럽(내복)/60(1)mL/병",
        "dose_per_time": 4.2,
        "unit": "mL",
        "daily_count": 3,
        "total_days": 5,
        "as_needed": False,
        "max_daily_count": None,
        "usage": "가루약,물약 따로 식후 30분",
        "route": "ORAL",
        "dosage_form": "DRY_SYRUP",
    },
    {
        "medication_id": 42,
        "name": "세토펜현탁액(아세트아미노펜)/100(1)mL/병",
        "dose_per_time": 5.0,
        "unit": "mL",
        "daily_count": None,
        "total_days": 3,
        "as_needed": True,
        "max_daily_count": 5,
        "usage": "필요시 (5)mL씩복용(사용)하세요",
        "route": "ORAL",
        "dosage_form": "SYRUP",
    },
]


def _fake_llm(system: str, user: str) -> dict[str, Any]:
    return {
        "summary": "3세 7개월 아이의 오늘 처방은 약 2가지예요.",
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
        "home_care_picks": [],
    }


def _guide() -> dict[str, Any]:
    return generate_guide(CHILD, PRESCRIPTION, MEDS, call_llm=_fake_llm)


def test_codes_become_schema_values() -> None:
    m = normalize_medication(MEDS[0])
    assert (m["route"], m["dosage_form"], m["ingredient"]) == ("내복", "건조시럽", "cefaclor")
    assert MEDS[0]["route"] == "ORAL"  # 원래 값은 그대로


def test_liquid_and_class_tips_are_attached() -> None:
    tip_ids = {t["template_item_id"] for t in _guide()["with_this_medicine"]}
    assert "form.liquid.separate" in tip_ids  # 시럽 → 제형 팁
    assert "abx.finish" in tip_ids  # 세파클러 → 항생제 팁 (성분은 이름에서 찾음)
    assert "apap.interval" in tip_ids  # 세토펜 → 해열제 간격


def test_allergies_are_not_split_into_letters() -> None:
    assert _guide()["child"]["allergies"] == ["계란", "우유"]


def test_age_uses_prescription_date() -> None:
    assert _guide()["child"]["age_months"] == 43  # 2023-04-02 → 2026-11-12


@pytest.mark.parametrize(
    ("text", "groups"),
    [
        ("기침감기", ["cold_bronchitis"]),
        ("목감기, 접촉성 피부염", ["cold_bronchitis", "dermatitis"]),
        ("중이염", ["otitis_sinusitis"]),
        ("열이 나요", []),
    ],
)
def test_disease_group_from_guardian_input(text: str, groups: list[str]) -> None:
    assert disease_groups_of(text) == groups


def test_matches_schema() -> None:
    schema_path = RESOURCE_DIR / "schema" / "guide_content.schema.json"
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(_guide(), json.loads(schema_path.read_text(encoding="utf-8")))
