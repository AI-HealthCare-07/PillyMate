from datetime import date, time
from decimal import Decimal

from httpx import ASGITransport, AsyncClient, Response
from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.main import app
from app.models.medication_alarms import MedicationAlarm
from app.models.medications import Medication
from app.models.prescriptions import Prescription, PrescriptionStatus, SourceType
from app.services.medication_alarms import _as_time
from app.tests.auth_apis.helpers import BASE_URL, post
from app.tests.child_apis.test_child_api import child_payload, login


async def send(method: str, path: str, json: object | None = None, headers: dict[str, str] | None = None) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
        return await client.request(method, f"/api/v1{path}", json=json, headers=headers)


async def make_child(headers: dict[str, str]) -> int:
    response = await post("/children", json=child_payload(), headers=headers)
    return int(response.json()["child_id"])


async def make_prescription(
    child_id: int,
    status_: PrescriptionStatus = PrescriptionStatus.CONFIRMED,
    prescription_date: str | None = "2026-11-20",
) -> Prescription:
    prescription = await Prescription.create(
        child_id=child_id,
        source_type=SourceType.PRESCRIPTION,
        status=status_,
        prescription_date=prescription_date,
        hospital_name="해솔소아청소년과의원",
        diagnosis_user_input="감기",
    )
    meds = [
        # 하루 3번·5일 → 아침·점심·저녁 알림
        dict(name="세토펜현탁액", daily_count=3, total_days=5, usage="식후 30분"),
        # 하루 1번 자기 전 → 화면에서 알림을 보내지 않는 때라 알림 없음
        dict(name="코대원시럽", daily_count=1, total_days=3, usage="자기 전"),
        # 필요시 약 → 알림 없음
        dict(name="부루펜시럽", daily_count=None, total_days=None, as_needed=True, max_daily_count=4),
        # 기간이 없으면 종료일을 알 수 없어 알림 없음 (명세 7절)
        dict(name="뮤코펙트시럽", daily_count=2, total_days=None),
    ]
    for med in meds:
        await Medication.create(prescription=prescription, dose_per_time=Decimal("4"), unit="mL", **med)
    return prescription


class TestMedicationAlarmAPI(TestCase):
    async def test_first_read_creates_default_alarms_for_scheduled_meds_only(self) -> None:
        headers = await login("alarm@example.com")
        child_id = await make_child(headers)
        prescription = await make_prescription(child_id)
        await make_prescription(child_id, PrescriptionStatus.OCR_DONE)  # 확정 전 처방은 알림 없음

        response = await send("GET", f"/children/{child_id}/alarms", headers=headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == [
            {
                "prescription_id": prescription.id,
                "enabled": True,
                "times": {"아침": "08:00", "점심": "12:30", "저녁": "18:30"},
                "start_date": "2026-11-20",
                "end_date": "2026-11-24",  # 5일 복용, 종료일 포함
            }
        ]
        alarms = await MedicationAlarm.filter(medication__prescription_id=prescription.id).order_by("id")
        assert [_as_time(a.notify_time) for a in alarms] == [time(8, 0), time(12, 30), time(18, 30)]
        assert {a.medication_id for a in alarms} == {  # type: ignore[attr-defined]
            (await Medication.get(prescription=prescription, name="세토펜현탁액")).id
        }
        # 다시 읽어도 새로 만들지 않는다 (새로고침·재로그인)
        await send("GET", f"/children/{child_id}/alarms", headers=headers)
        assert [
            a.id for a in await MedicationAlarm.filter(medication__prescription_id=prescription.id).order_by("id")
        ] == [a.id for a in alarms]

    async def test_time_and_onoff_are_saved_and_restored(self) -> None:
        headers = await login("save@example.com")
        child_id = await make_child(headers)
        prescription = await make_prescription(child_id)
        path = f"/prescriptions/{prescription.id}/alarms"

        changed = await send("PATCH", path, json={"times": {"점심": "13:10"}}, headers=headers)
        assert changed.status_code == status.HTTP_200_OK
        assert changed.json()["times"] == {"아침": "08:00", "점심": "13:10", "저녁": "18:30"}

        # 아침·저녁 시각을 맞바꿔도 (약, 시각, 시작일) unique에 걸리지 않는다
        swapped = await send("PATCH", path, json={"times": {"아침": "18:30", "저녁": "08:00"}}, headers=headers)
        assert swapped.json()["times"] == {"아침": "18:30", "점심": "13:10", "저녁": "08:00"}

        off = await send("PATCH", path, json={"enabled": False}, headers=headers)
        assert off.json()["enabled"] is False
        assert not await MedicationAlarm.filter(medication__prescription_id=prescription.id, is_enabled=True).exists()

        restored = (await send("GET", f"/children/{child_id}/alarms", headers=headers)).json()[0]
        assert (restored["enabled"], restored["times"]) == (False, {"아침": "18:30", "점심": "13:10", "저녁": "08:00"})

        on = await send("PATCH", path, json={"enabled": True}, headers=headers)
        assert on.json()["enabled"] is True
        assert on.json()["times"]["점심"] == "13:10"

    async def test_changed_medications_keep_prescription_settings(self) -> None:
        """다시 확정해서 약이 바뀌어도(약 행이 새로 생김) 먹는 때별 시각과 켜짐은 그대로 이어진다."""
        headers = await login("reconfirm@example.com")
        child_id = await make_child(headers)
        prescription = await make_prescription(child_id)
        path = f"/prescriptions/{prescription.id}/alarms"
        await send("PATCH", path, json={"times": {"저녁": "19:40"}, "enabled": False}, headers=headers)

        await Medication.filter(prescription=prescription, name="뮤코펙트시럽").update(total_days=3)

        body = (await send("GET", f"/children/{child_id}/alarms", headers=headers)).json()[0]
        assert body["enabled"] is False
        assert body["times"] == {"아침": "08:00", "점심": "12:30", "저녁": "19:40"}
        new_alarms = await MedicationAlarm.filter(medication__name="뮤코펙트시럽").order_by("id")
        assert [(_as_time(a.notify_time), a.end_date, a.is_enabled) for a in new_alarms] == [
            (time(8, 0), date(2026, 11, 22), False),
            (time(19, 40), date(2026, 11, 22), False),
        ]

    async def test_start_date_falls_back_to_upload_day(self) -> None:
        headers = await login("pillbag@example.com")
        child_id = await make_child(headers)
        prescription = await make_prescription(child_id, prescription_date=None)

        body = (await send("GET", f"/children/{child_id}/alarms", headers=headers)).json()[0]

        await prescription.refresh_from_db()
        uploaded = prescription.created_at.astimezone(config.TIMEZONE)
        assert body["start_date"] == uploaded.date().isoformat()

    async def test_rejects_bad_requests_with_messages(self) -> None:
        headers = await login("rules@example.com")
        child_id = await make_child(headers)
        prescription = await make_prescription(child_id)
        pending = await make_prescription(child_id, PrescriptionStatus.OCR_DONE)
        path = f"/prescriptions/{prescription.id}/alarms"
        cases = [
            (path, {"times": {"점심": "1310"}}, 422, "알림 시각은 08:30처럼 입력해 주세요."),
            (path, {"times": {"점심": "24:00"}}, 422, "알림 시각은 08:30처럼 입력해 주세요."),
            (path, {"times": {"자기 전": "21:00"}}, 422, "알림을 보낼 수 없는 먹는 때예요: 자기 전"),
            (path, {"times": {"점심": "08:00"}}, 422, "먹는 때마다 다른 시각을 골라 주세요."),
            (f"/prescriptions/{pending.id}/alarms", {"enabled": False}, 409, "처방을 먼저 확정해 주세요."),
        ]
        for target, payload, code, message in cases:
            response = await send("PATCH", target, json=payload, headers=headers)
            assert (response.status_code, response.json()) == (code, {"detail": message}), payload
        body = (await send("GET", f"/children/{child_id}/alarms", headers=headers)).json()[0]
        assert body["times"] == {"아침": "08:00", "점심": "12:30", "저녁": "18:30"}

    async def test_only_my_child_and_prescription(self) -> None:
        mine = await login("owner@example.com")
        other = await login("stranger@example.com")
        child_id = await make_child(mine)
        prescription = await make_prescription(child_id)

        assert (await send("GET", f"/children/{child_id}/alarms", headers=other)).status_code == 404
        response = await send(
            "PATCH", f"/prescriptions/{prescription.id}/alarms", json={"enabled": False}, headers=other
        )
        assert (response.status_code, response.json()) == (404, {"detail": "처방전을 찾을 수 없어요."})
        assert (await send("GET", f"/children/{child_id}/alarms")).status_code == 401
        assert (await send("PATCH", f"/prescriptions/{prescription.id}/alarms", json={})).status_code == 401
        assert not await MedicationAlarm.filter(is_enabled=False).exists()
