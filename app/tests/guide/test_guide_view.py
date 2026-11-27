"""가이드 → 프론트 화면 형식(view.to_view) 변환 테스트. DB·LLM 없이 돈다."""

from app.services.guide.service import generate_guide
from app.services.guide.view import short_name, to_view

CHILD = {"birth_date": "2023-04-02", "weight_kg": 16.9, "allergies": "계란"}
PRESCRIPTION = {
    "prescription_id": 1,
    "prescription_date": "2026-11-12",
    "diagnosis_user_input": "감기, 급성 기관지염",
    "symptom_notes": "기침",
}
MEDS = [
    {
        "medication_id": 1,
        "name": "세파클러건조시럽(내복)/60(1)mL/병",
        "dose_per_time": 4.2,
        "unit": "mL",
        "daily_count": 3,
        "total_days": 5,
        "as_needed": False,
        "usage": "1일 3회 식후 30분",
        "route": "ORAL",
        "dosage_form": "DRY_SYRUP",
    },
    {
        "medication_id": 2,
        "name": "지르텍시럽",
        "dose_per_time": 2.5,
        "unit": "mL",
        "daily_count": 1,
        "total_days": 5,
        "as_needed": False,
        "usage": "1일 1회 자기 전",
        "route": "ORAL",
        "dosage_form": "SYRUP",
    },
    {
        "medication_id": 3,
        "name": "세토펜현탁액(아세트아미노펜)",
        "dose_per_time": 5,
        "unit": "mL",
        "daily_count": None,
        "total_days": 3,
        "as_needed": True,
        "max_daily_count": 4,
        "usage": "열날 때 4시간 이상 간격",
        "route": "ORAL",
        "dosage_form": "SYRUP",
    },
]


def no_llm(system: str, user: str) -> dict:
    raise ValueError("offline")


def view(prescription: dict = PRESCRIPTION) -> dict:
    return to_view(generate_guide(CHILD, prescription, MEDS, call_llm=no_llm))


def test_short_name_strips_spec():
    assert short_name("세파클러건조시럽(내복)/60(1)mL/병") == "세파클러건조시럽"
    assert short_name("지르텍시럽") == "지르텍시럽"


def test_frontend_keys():
    v = view()
    for key in (
        "schedule",
        "asNeeded",
        "howTo",
        "life",
        "medTips",
        "allergyNotice",
        "danger",
        "summary",
        "disclaimer",
        "detail",
    ):
        assert key in v
    assert v["title"] == "감기, 급성 기관지염"
    assert v["detail"]["schema_version"] == "0.3"


def test_schedule_slots_and_items():
    schedule = {s["slot"]: s["items"] for s in view()["schedule"]}
    assert list(schedule) == ["아침", "점심", "저녁", "자기 전"]
    assert schedule["아침"] == [["세파클러건조시럽", "4.2mL", "5일"]]
    assert schedule["자기 전"] == [["지르텍시럽", "2.5mL", "5일"]]
    assert all("세토펜" not in i[0] for items in schedule.values() for i in items)  # 필요시 약은 시간표에 없음


def test_as_needed_line():
    line = view()["asNeeded"]
    assert line.startswith("세토펜현탁액: 필요할 때만 1회 5mL.")
    assert "4시간" in line and "하루 4번" in line


def test_how_to_life_danger():
    v = view()
    assert [h["name"] for h in v["howTo"]] == [m["name"] for m in MEDS]
    assert all(h["how"] for h in v["howTo"])
    assert 0 < len(v["life"]) <= 8 and len(v["life"]) == len(set(v["life"]))
    assert any(d.startswith("바로 응급실:") for d in v["danger"])


def test_how_to_has_table_facts_for_regular_and_as_needed():
    """약별 복용법 표 칸 — 필요시 약도 1회 양·하루 최대 횟수가 보여야 한다(일정표에 없어서 비던 문제)."""
    how_to = {h["name"]: h for h in view()["howTo"]}
    regular = how_to["세파클러건조시럽(내복)/60(1)mL/병"]
    assert (regular["dose"], regular["perDay"], regular["days"], regular["asNeeded"]) == ("4.2mL", "3번", "5일", False)
    assert regular["timing"].startswith("아침·점심·저녁")
    prn = how_to["세토펜현탁액(아세트아미노펜)"]
    assert (prn["dose"], prn["perDay"], prn["days"], prn["timing"], prn["asNeeded"]) == (
        "5mL",
        "최대 4번",
        "3일",
        "",
        True,
    )


def test_old_view_is_rebuilt_from_detail():
    from app.services.prescriptions import current_view

    new = view()
    old = {k: v for k, v in new.items() if k != "howTo"} | {
        "schema_version": "fe-1",
        "howTo": [{"name": h["name"], "how": h["how"], "note": h["note"]} for h in new["howTo"]],
    }
    rebuilt = current_view(old)
    assert rebuilt["schema_version"] == new["schema_version"]
    assert all("dose" in h for h in rebuilt["howTo"])
    assert current_view({"schema_version": "fe-1", "howTo": []}) == {"schema_version": "fe-1", "howTo": []}


def test_life_has_no_medicine_tips():
    """생활 습관(life)에는 집에서 돌보기·관리 포인트만, 약 계열 팁은 medTips로 따로 나간다."""
    v = view()
    assert v["schema_version"] == "fe-3"
    assert v["life"] and v["medTips"]
    assert not set(v["life"]) & set(v["medTips"])


def test_life_follows_disease_group():
    cold = view()["life"]
    other = view({**PRESCRIPTION, "diagnosis_user_input": "변비"})["life"]  # 템플릿 없는 질환군(other)
    assert cold != other


def test_interval_tip_skipped_when_prescription_has_interval():
    """세토펜 용법에 '4시간 이상 간격'이 있으므로 숫자가 고정된 일반 간격 문장(4~6시간)은 붙이지 않는다."""
    assert not any("4~6시간 간격" in t for t in view()["medTips"])


def test_allergy_rule_flags_matching_medicine():
    from app.services.guide.generator import allergy_flags

    meds = [
        {"medication_id": 1, "name": "리소짐시럽", "ingredient": None},
        {"medication_id": 2, "name": "오구멘틴시럽", "ingredient": "amoxicillin/clavulanate"},
        {"medication_id": 3, "name": "세토펜현탁액", "ingredient": "acetaminophen"},
    ]
    assert set(allergy_flags(["계란"], meds)) == {1}
    assert set(allergy_flags(["페니실린"], meds)) == {2}
    assert allergy_flags(["우유"], meds) == {}  # 규칙에 없는 조합은 추측하지 않는다


def test_allergy_notice():
    assert view()["allergyNotice"] == "약을 받을 때 약사에게 계란 알레르기가 있다고 알려 주세요."


def danger_for(birth_date: str) -> list[str]:
    child = {**CHILD, "birth_date": birth_date}
    return to_view(generate_guide(child, PRESCRIPTION, MEDS, call_llm=no_llm))["danger"]


def test_danger_signs_follow_age():
    """처방일(2026-11-12) 기준 나이에 맞는 위험 신호만 나온다."""
    school = " ".join(danger_for("2016-05-01"))  # 10세
    assert "생후" not in school and "기저귀" not in school
    assert "축 늘어질 때" in school  # 나이와 상관없는 신호는 그대로

    infant = " ".join(danger_for("2026-09-01"))  # 생후 2개월
    assert "생후 3개월 미만" in infant and "기저귀" in infant
    assert "생후 3~6개월" not in infant


def test_danger_signs_keep_both_levels_for_every_age():
    """스키마상 go_to_er·see_doctor는 1개 이상이어야 한다. 나이로 걸러도 둘 다 남는지 확인."""
    for birth in ("2026-09-01", "2026-06-01", "2023-04-02", "2016-05-01", "2010-01-01"):
        danger = danger_for(birth)
        assert any(d.startswith("바로 응급실:") for d in danger), birth
        assert any(d.startswith("진료 필요:") for d in danger), birth
