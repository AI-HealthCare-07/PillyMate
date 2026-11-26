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


def view() -> dict:
    return to_view(generate_guide(CHILD, PRESCRIPTION, MEDS, call_llm=no_llm))


def test_short_name_strips_spec():
    assert short_name("세파클러건조시럽(내복)/60(1)mL/병") == "세파클러건조시럽"
    assert short_name("지르텍시럽") == "지르텍시럽"


def test_frontend_keys():
    v = view()
    for key in ("schedule", "asNeeded", "howTo", "life", "danger", "summary", "disclaimer", "detail"):
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
