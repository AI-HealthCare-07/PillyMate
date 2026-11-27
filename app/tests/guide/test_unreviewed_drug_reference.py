"""검수 전(낮은 단계) 약 정보 — app/services/guide/unreviewed_drug_reference.py

식약처 API는 부르지 않는다. fetch에 가짜 함수를 넣는다.
"""

import threading
from unittest.mock import patch

import pytest

from app.services.guide import service
from app.services.guide import unreviewed_drug_reference as udr
from app.services.guide.easy_drug_info_fields import EasyDrugInfo
from app.services.guide.permit_document_sections import PermitDocument
from app.services.guide.permit_ingredient_index import PermitIngredientIndex, PermitItem, ingredient_set
from app.services.guide.unreviewed_drug_reference import (
    UNREVIEWED_HEADER,
    UNREVIEWED_REASON,
    UnreviewedSources,
    is_unreviewed,
    summarize_unreviewed,
    target_item,
    unreviewed_references,
)


@pytest.fixture
def permit():
    return PermitIngredientIndex(
        [
            PermitItem("1", "포리부틴드라이시럽(트리메부틴)", ingredient_set("[M1]트리메부틴말레산염"), ("650000001",)),
            PermitItem("2", "트리메부틴정(트리메부틴말레산염)", ingredient_set("[M1]트리메부틴말레산염"), ()),
            PermitItem("3", "에펙신이용액(오플록사신)", ingredient_set("[M2]오플록사신"), ()),
        ]
    )


def _doc(seq="1", name="포리부틴드라이시럽(트리메부틴)"):
    return PermitDocument(
        seq,
        name,
        efficacy="위 십이지장염의 소화기능이상(복통, 구역)",
        sections={"contraindication": "2. 투여하지 말 것: 과민증 환자", "side_effects": "4. 이상반응: 변비, 설사"},
        storage_method="기밀용기, 실온(1~30℃)보관",
    )


def test_target_is_the_prescribed_product(permit):
    item, same = target_item({"name": "포리부틴드라이시럽"}, permit)
    assert (item.item_seq, same) == ("1", True)


def test_target_by_bracket_ingredient_prefers_same_form(permit):
    item, same = target_item({"name": "다른회사트리메부틴정(트리메부틴말레산염)"}, permit)
    assert (item.item_seq, same) == ("2", False)  # 같은 성분 다른 제품 → 요약에 표시


def test_target_with_other_route_is_dropped(permit):
    """귀에 넣는 약 문서를 먹는 약에 붙이지 않는다."""
    assert target_item({"name": "오플록사신정(오플록사신)", "route": "내복"}, permit) == (None, False)


def test_summary_header_and_fields():
    text = summarize_unreviewed(UnreviewedSources(_doc(), "12세 미만 금기"), same_product=True)
    assert text.startswith(UNREVIEWED_HEADER) and is_unreviewed(text)
    assert "효능: 위 십이지장염" in text
    assert "연령 금기(DUR): 12세 미만 금기" in text
    assert "보관: 기밀용기" in text
    assert "같은 성분의 다른 제품" not in text
    assert len(text) <= udr.UNREVIEWED_MAX_CHARS


def test_summary_prefers_easy_drug_sentences_and_marks_other_product():
    easy = EasyDrugInfo("1", "x", {"효능": "배가 아플 때 쓰는 약입니다.", "보관": "실온에서 보관하십시오."})
    text = summarize_unreviewed(UnreviewedSources(_doc(), "", easy), same_product=False)
    assert "효능: 배가 아플 때 쓰는 약입니다." in text
    assert "보관: 실온에서 보관하십시오." in text
    assert "+ e약은요" in text and "같은 성분의 다른 제품" in text


def test_summary_is_cut_to_max_chars():
    long_doc = _doc()
    long_doc.sections = {k: "가" * 500 for k in ("contraindication", "child", "warning", "side_effects")}
    assert len(summarize_unreviewed(UnreviewedSources(long_doc), True)) <= udr.UNREVIEWED_MAX_CHARS


def test_references_only_for_found_items(permit):
    meds = [
        {"medication_id": 1, "name": "포리부틴드라이시럽"},
        {"medication_id": 2, "name": "어디에도없는약"},
    ]
    refs = unreviewed_references(meds, permit=permit, fetch=lambda seq: UnreviewedSources(_doc(seq)))
    assert set(refs) == {1} and is_unreviewed(refs[1])


def test_slow_lookup_is_left_out(permit):
    release = threading.Event()

    def slow(seq):
        release.wait(2)
        return UnreviewedSources(_doc(seq))

    try:
        refs = unreviewed_references(
            [{"medication_id": 1, "name": "포리부틴드라이시럽"}], permit=permit, fetch=slow, budget_seconds=0.05
        )
    finally:
        release.set()
    assert refs == {}


def test_failing_lookup_does_not_break(permit):
    def boom(seq):
        raise RuntimeError("네트워크")

    assert unreviewed_references([{"medication_id": 1, "name": "포리부틴드라이시럽"}], permit=permit, fetch=boom) == {}


def test_no_key_means_no_lookup():
    """conftest가 lookup_enabled를 끈다. 그러면 fetch를 넘기지 않은 호출은 아무것도 하지 않는다."""
    assert unreviewed_references([{"medication_id": 1, "name": "포리부틴드라이시럽"}]) == {}


def test_fetch_sources_caches_by_item_seq(monkeypatch):
    calls = []

    def fake_doc(client, seq):
        calls.append(seq)
        return _doc(seq), {}

    monkeypatch.setattr(udr, "fetch_permit_document", fake_doc)
    monkeypatch.setattr(udr, "fetch_dur_age_taboo", lambda c, s: "")
    monkeypatch.setattr(udr, "fetch_easy_drug", lambda c, s: None)
    udr._cache.clear()
    try:
        assert udr.fetch_sources("77").doc.item_seq == "77"
        assert udr.fetch_sources("77").doc.item_seq == "77"
    finally:
        udr._cache.clear()
    assert calls == ["77"]


# ------------------------------------------------------------------ 가이드에서 약사 확인 켜기


def test_require_pharmacist_check_keeps_llm_reason():
    guide = {
        "medications": [
            {"medication_id": 1, "pharmacist_check": {"needed": False, "reason": None}},
            {"medication_id": 2, "pharmacist_check": {"needed": True, "reason": "알레르기 확인"}},
            {"medication_id": 3, "pharmacist_check": {"needed": False, "reason": None}},
            {"medication_id": 4, "pharmacist_check": {"needed": True, "reason": None}},
        ]
    }
    out = service.require_pharmacist_check(guide, {1, 2, 4})
    checks = {c["medication_id"]: c["pharmacist_check"] for c in out["medications"]}
    assert checks[1] == {"needed": True, "reason": UNREVIEWED_REASON}
    assert checks[2] == {"needed": True, "reason": "알레르기 확인"}
    assert checks[3]["needed"] is False
    assert checks[4] == {"needed": True, "reason": UNREVIEWED_REASON}  # LLM이 켜기만 하고 이유를 비운 경우


def test_generate_guide_turns_on_check_for_unreviewed_reference():
    """LLM이 약사 확인을 끄더라도 검수 전 정보로 설명한 약은 켜진다."""
    med = {"medication_id": 3, "name": "포리부틴드라이시럽", "dosage_form": "DRY_SYRUP", "route": "ORAL",
           "dose_per_time": 3, "unit": "mL", "daily_count": 3, "total_days": 3, "as_needed": False,
           "max_daily_count": None, "usage": "식후 30분"}  # fmt: skip
    rx = {"prescription_id": 1, "prescription_date": "2026-11-20", "diagnosis_user_input": "장염"}
    child = {"birth_date": "2024-09-10", "weight_kg": 12.0, "allergies": []}

    def llm(system, user):
        return {
            "summary": "요약이에요. 오늘은 물을 자주 먹여 주세요.",
            "medications": [
                {"medication_id": 3, "purpose": "배 불편을 줄이는 약이에요.", "how_to_give": ["식후에 먹여요."],
                 "cautions": [], "common_side_effects": [], "storage": None, "pharmacist_check_needed": False}
            ],
            "home_care_picks": [],
        }  # fmt: skip

    with patch.object(service, "unreviewed_references", lambda meds: {3: f"{UNREVIEWED_HEADER} — 시험]"}):
        guide = service.generate_guide(child, rx, [med], call_llm=llm)
    card = next(c for c in guide["medications"] if c["medication_id"] == 3)
    assert card["pharmacist_check"] == {"needed": True, "reason": UNREVIEWED_REASON}


# ------------------------------------------------------------------ DUR 연령 금기


def test_dur_age_alert_for_young_child():
    refs = {
        1: f"{UNREVIEWED_HEADER} — x] 효능: 기침 연령 금기(DUR): 12세 미만 소아는 호흡억제 위험. 투여 금기: 과민증",
        2: "[출처: 검수] 효능: 해열 연령 금기(DUR): 6개월 미만 영아 금기 보관: 실온",
        3: "[출처: 검수] 효능: 해열 주의: 12세 미만도 쓸 수 있어요",  # DUR 칸이 아니면 보지 않는다
    }
    alerts = service.dur_age_alerts(refs, age_months=26)  # 2살
    assert set(alerts) == {1}
    assert alerts[1].limit == "12세" and alerts[1].text == "12세 미만 소아는 호흡억제 위험."
    assert "12세 미만" in alerts[1].reason and len(alerts[1].reason) <= 80
    assert set(service.dur_age_alerts(refs, age_months=5)) == {1, 2}
    assert service.dur_age_alerts(refs, age_months=150) == {}  # 12세 6개월


def test_dur_age_alert_puts_official_caution_first_and_drops_soft_one():
    guide = {
        "medications": [
            {
                "medication_id": 1,
                "cautions": ["12세 미만 아이는 특히 조심해야 해요.", "졸릴 수 있어요.", "가", "나"],
                "pharmacist_check": {"needed": True, "reason": "LLM 이유"},
            }
        ]
    }
    alert = service.DurAgeAlert("12세", "12세 미만 소아는 호흡억제 감수성이 큼.")
    card = service.apply_dur_age_alerts(guide, {1: alert})["medications"][0]
    assert card["cautions"][0].startswith("식약처 연령 금기(DUR): 12세 미만 소아는 호흡억제 감수성이 큼.")
    assert not any("조심해야" in c for c in card["cautions"])
    assert len(card["cautions"]) <= service.MAX_CAUTIONS
    assert card["pharmacist_check"] == {"needed": True, "reason": alert.reason}


def test_leading_sentences_keeps_whole_sentences():
    text = "12세 미만 소아는 호흡억제 감수성이 큼.12세 미만 소아에서 중증 호흡억제 위험 보고 있음."
    assert (
        service._leading_sentences(text, 90)
        == "12세 미만 소아는 호흡억제 감수성이 큼. 12세 미만 소아에서 중증 호흡억제 위험 보고 있음."
    )
    assert service._leading_sentences(text, 30) == "12세 미만 소아는 호흡억제 감수성이 큼."
    assert service._leading_sentences("가" * 50, 10).endswith("…")


def test_dur_duplicates_with_different_punctuation_are_joined_once():
    from app.services.guide.mfds_drug_info_api import join_unique

    assert join_unique(["위험이 큼.12세 미만 보고 있음.", "위험이 큼, 12세 미만 보고 있음", "다른 문장"]) == (
        "위험이 큼.12세 미만 보고 있음. 다른 문장"
    )


# ------------------------------------------------------------------ 근거 없는 제형 요령 거르기


def test_unsupported_form_tips_are_dropped():
    guide = {
        "medications": [
            {
                "medication_id": 1,
                "how_to_give": [
                    "식후 30분에 먹여 주세요.",
                    "건조시럽은 물에 녹여 먹여 주세요.",
                    "물을 넣어 잘 섞은 뒤 먹여요.",
                ],
            },
            {
                "medication_id": 2,
                "how_to_give": [
                    "식후에 먹여요.",
                    "계량컵으로 재서 먹여 주세요.",
                    "계량 도구로 재요.",
                    "흔들어 먹여요.",
                ],
            },
            {"medication_id": 3, "how_to_give": ["잘 흔들어 먹여 주세요."]},
            {"medication_id": 4, "how_to_give": ["물에 녹여 먹여 주세요."]},  # 다 빠지면 그대로 둔다
        ]
    }
    meds = [
        {"medication_id": 1, "usage": "식후 30분"},
        {"medication_id": 2, "usage": "식후"},
        {"medication_id": 3, "usage": "식후", "pharmacy_caution": "잘 흔들어 드세요"},  # 약국 안내에 근거 있음
        {"medication_id": 4, "usage": ""},
    ]
    refs = {2: "보관: 실온. 사용 전 흔들어 주세요."}  # reference에 '흔들' 근거 있음
    out = {
        c["medication_id"]: c["how_to_give"]
        for c in service.drop_unsupported_form_tips(guide, meds, refs)["medications"]
    }
    assert out[1] == ["식후 30분에 먹여 주세요."]
    assert out[2] == ["식후에 먹여요.", "흔들어 먹여요."]
    assert out[3] == ["잘 흔들어 먹여 주세요."]
    assert out[4] == ["물에 녹여 먹여 주세요."]


# ------------------------------------------------------------------ 외용 약·귀약 낱말


def test_etc_form_is_inferred_from_name():
    ear = service.normalize_medication({"medication_id": 1, "name": "에펙신이용액(오플록사신)", "dosage_form": "ETC"})
    assert ear["dosage_form"] == "점이액"
    other = service.normalize_medication({"medication_id": 2, "name": "알수없는약", "dosage_form": "ETC"})
    assert other["dosage_form"] == "기타"
    syrup = service.normalize_medication({"medication_id": 3, "name": "코푸시럽", "dosage_form": "SYRUP"})
    assert syrup["dosage_form"] == "시럽"  # DB 값이 있으면 그대로


def test_external_wording_is_fixed():
    guide = {
        "summary": "항생제와 귀 점안약을 끝까지 쓰는 게 중요해요.",
        "medications": [
            {
                "medication_id": 1,
                "route": "외용",
                "dosage_form": "점이액",
                "purpose": "귀의 세균 감염을 치료하는 귀 점안약이에요.",
                "how_to_give": ["아픈 쪽 귀에 넣어요."],
                "cautions": ["과민증이 있었으면 먹이지 않아요.", "두드러기가 나면 먹이기를 멈추고 진료받아요."],
            },
            {
                "medication_id": 2,
                "route": "내복",
                "dosage_form": "시럽",
                "purpose": "열을 내리는 약이에요.",
                "cautions": ["알레르기가 있었으면 먹이지 않아요."],
            },
        ],
    }
    out = service.fix_external_wording(guide)
    ear, oral = out["medications"]
    assert ear["purpose"] == "귀의 세균 감염을 치료하는 귀약이에요."
    assert ear["cautions"] == ["과민증이 있었으면 쓰지 않아요.", "두드러기가 나면 쓰기를 멈추고 진료받아요."]
    assert oral["cautions"] == ["알레르기가 있었으면 먹이지 않아요."]  # 먹는 약은 그대로
    assert out["summary"] == "항생제와 귀약을 끝까지 쓰는 게 중요해요."


def test_ear_drop_tips_need_evidence_but_eye_drop_example_is_kept():
    guide = {
        "medications": [
            {
                "medication_id": 1,
                "dosage_form": "점이액",
                "how_to_give": [
                    "아픈 쪽 귀에 넣어요.",
                    "용기 끝이 귀에 닿지 않게 해요.",
                    "넣은 뒤 귀 입구를 가볍게 눌러요.",
                ],
            },
            {"medication_id": 2, "dosage_form": "점안액", "how_to_give": ["용기 끝이 눈에 닿지 않게 넣어요."]},
        ]
    }
    meds = [{"medication_id": 1, "usage": "아침, 저녁 귀에 넣기"}, {"medication_id": 2, "usage": "하루 3번"}]
    out = {
        c["medication_id"]: c["how_to_give"] for c in service.drop_unsupported_form_tips(guide, meds, {})["medications"]
    }
    assert out[1] == ["아픈 쪽 귀에 넣어요."]
    assert out[2] == ["용기 끝이 눈에 닿지 않게 넣어요."]


# ------------------------------------------------------------------ 아이가 지난 나이 조건 빼기


def test_inapplicable_age_conditions_are_dropped():
    guide = {
        "medications": [
            {
                "medication_id": 1,
                "cautions": [
                    "허가사항상 만 2세 미만은 의사 지시 없이는 먹이지 않는 약이에요. 이 아이는 만 2세 이상이에요.",
                    "1세 미만 영아에게는 안전성이 확립되어 있지 않아요.",
                    "6세 미만에게는 정제 대신 액제를 먹여요.",  # 2살에게 해당 → 둔다
                    "열이 3일 넘게 계속되면 진료를 받아요.",
                ],
                "pharmacist_check": {
                    "needed": True,
                    "reason": "만 2세 미만은 의사 지시 없이 먹이지 않는 약이에요. 복용 간격을 확인해 주세요.",
                },
            },
            {
                "medication_id": 2,
                "cautions": [],
                "pharmacist_check": {"needed": True, "reason": "생후 3개월 미만 아기는 먹이지 않아요."},
            },
        ]
    }
    out = service.drop_inapplicable_age_conditions(guide, age_months=26)["medications"]
    assert out[0]["cautions"] == ["6세 미만에게는 정제 대신 액제를 먹여요.", "열이 3일 넘게 계속되면 진료를 받아요."]
    assert out[0]["pharmacist_check"]["reason"] == service.AGE_FALLBACK_REASON  # 남은 문장만 두면 어색해서 통째로
    assert out[1]["pharmacist_check"] == {"needed": True, "reason": service.AGE_FALLBACK_REASON}


def test_caution_item_is_dropped_whole_and_over_age_is_understood():
    guide = {
        "medications": [
            {
                "medication_id": 1,
                "cautions": [
                    "2세 미만은 의사 지시 없이 먹이지 않아요. 아이 나이가 이 기준에 해당하는지 확인해 주세요.",
                    "10세 이상에서 이상행동이 보고됐어요.",
                    "1세 이상 6세 미만 소아에서 발열·설사가 흔했어요.",
                    "졸릴 수 있어요.",
                ],
            }
        ]
    }
    two = service.drop_inapplicable_age_conditions(guide, age_months=26)["medications"][0]["cautions"]
    assert two == ["1세 이상 6세 미만 소아에서 발열·설사가 흔했어요.", "졸릴 수 있어요."]


def test_applicable_age_condition_is_kept_for_young_child():
    guide = {"medications": [{"medication_id": 1, "cautions": ["1세 미만 영아에게는 안전성이 확립되어 있지 않아요."]}]}
    out = service.drop_inapplicable_age_conditions(guide, age_months=8)["medications"][0]
    assert out["cautions"] == ["1세 미만 영아에게는 안전성이 확립되어 있지 않아요."]


def test_summary_keeps_last_field_instead_of_empty_ellipsis():
    """앞 칸이 길어도 끝 칸이 '흔한 부작용: …'처럼 비지 않는다 (자리가 없으면 아예 뺀다)."""
    long_doc = _doc()
    long_doc.sections = {
        k: "1) 소아에게 투여하지 말 것. " * 60 for k in ("contraindication", "child", "warning", "side_effects")
    }
    text = summarize_unreviewed(UnreviewedSources(long_doc, "12세 미만 금기"), True)
    assert len(text) <= udr.UNREVIEWED_MAX_CHARS
    assert not text.endswith(": …")
