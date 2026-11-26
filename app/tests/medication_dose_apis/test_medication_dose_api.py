from datetime import date, datetime, timedelta
from decimal import Decimal

from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.models.medication_dose_logs import MedicationDoseLog
from app.models.medications import Medication
from app.models.prescriptions import Prescription, PrescriptionStatus, SourceType
from app.tests.auth_apis.helpers import post
from app.tests.child_apis.test_child_api import child_payload, login
from app.tests.medication_alarm_apis.test_medication_alarm_api import make_child, send

TODAY = datetime.now(tz=config.TIMEZONE).date()
START = TODAY - timedelta(days=2)  # 오늘이 복용 3일째


async def make_prescription(child_id: int, status_: PrescriptionStatus = PrescriptionStatus.CONFIRMED) -> Prescription:
    prescription = await Prescription.create(
        child_id=child_id,
        source_type=SourceType.PRESCRIPTION,
        status=status_,
        prescription_date=START,
        hospital_name="해솔소아청소년과의원",
        diagnosis_user_input="감기",
    )
    for med in (
        dict(name="세토펜현탁액", daily_count=3, total_days=5, usage="식후 30분"),  # 아침·점심·저녁
        dict(name="코대원시럽", daily_count=1, total_days=3, usage="자기 전"),  # 자기 전, 3일
        dict(name="부루펜시럽", daily_count=None, total_days=None, as_needed=True, max_daily_count=4),  # 필요시
    ):
        await Medication.create(prescription=prescription, dose_per_time=Decimal("4"), unit="mL", **med)
    return prescription


async def med_id(prescription: Prescription, name: str) -> int:
    return (await Medication.get(prescription=prescription, name=name)).id


class TestMedicationDoseAPI(TestCase):
    async def test_check_cancel_and_restore(self) -> None:
        headers = await login("dose@example.com")
        child_id = await make_child(headers)
        prescription = await make_prescription(child_id)
        syrup, bedtime = await med_id(prescription, "세토펜현탁액"), await med_id(prescription, "코대원시럽")
        path = f"/prescriptions/{prescription.id}/doses"

        checked = await send(
            "PUT",
            path,
            json={
                "dose_date": TODAY.isoformat(),
                "items": [
                    {"medication_id": syrup, "slot": "아침", "is_taken": True},
                    {"medication_id": bedtime, "slot": "자기 전", "is_taken": True},
                ],
            },
            headers=headers,
        )
        assert checked.status_code == status.HTTP_200_OK
        assert [(d["medication_name"], d["slot"], d["is_taken"]) for d in checked.json()] == [
            ("세토펜현탁액", "아침", True),
            ("코대원시럽", "자기 전", True),
        ]
        # 어제 아침은 안 먹임으로 기록, 어제 점심은 기록 없음
        yesterday = (TODAY - timedelta(days=1)).isoformat()
        await send(
            "PUT",
            path,
            json={"dose_date": yesterday, "items": [{"medication_id": syrup, "slot": "아침", "is_taken": False}]},
            headers=headers,
        )
        # 오늘 아침 체크 취소 — 같은 행을 덮어쓴다
        await send(
            "PUT",
            path,
            json={
                "dose_date": TODAY.isoformat(),
                "items": [{"medication_id": syrup, "slot": "아침", "is_taken": False}],
            },
            headers=headers,
        )
        assert await MedicationDoseLog.filter(medication_id=syrup, dose_date=TODAY, slot="아침").count() == 1

        listed = await send("GET", f"/children/{child_id}/doses", headers=headers)
        assert listed.status_code == status.HTTP_200_OK
        assert [(d["dose_date"], d["medication_name"], d["slot"], d["is_taken"]) for d in listed.json()] == [
            (yesterday, "세토펜현탁액", "아침", False),
            (TODAY.isoformat(), "세토펜현탁액", "아침", False),
            (TODAY.isoformat(), "코대원시럽", "자기 전", True),
        ]
        assert listed.json()[0]["prescription_id"] == prescription.id

        ranged = await send(
            "GET", f"/children/{child_id}/doses?from={TODAY.isoformat()}&to={TODAY.isoformat()}", headers=headers
        )
        assert len(ranged.json()) == 2

    async def test_rejects_wrong_medication_slot_and_date(self) -> None:
        headers = await login("doserules@example.com")
        child_id = await make_child(headers)
        prescription = await make_prescription(child_id)
        other = await make_prescription(child_id)
        pending = await make_prescription(child_id, PrescriptionStatus.OCR_DONE)
        syrup, bedtime = await med_id(prescription, "세토펜현탁액"), await med_id(prescription, "코대원시럽")
        prn = await med_id(prescription, "부루펜시럽")
        path = f"/prescriptions/{prescription.id}/doses"

        def body(medication_id: int, slot: str, day: date = TODAY) -> dict[str, object]:
            return {
                "dose_date": day.isoformat(),
                "items": [{"medication_id": medication_id, "slot": slot, "is_taken": True}],
            }

        cases = [
            (path, body(await med_id(other, "세토펜현탁액"), "아침"), 422, "이 처방에 없는 약이 포함돼 있어요."),
            (path, body(syrup, "자기 전"), 422, "이 약을 먹이는 때가 아니에요: 세토펜현탁액 자기 전"),
            (path, body(prn, "아침"), 422, "이 약을 먹이는 때가 아니에요: 부루펜시럽 아침"),
            (path, body(syrup, "아침", START - timedelta(days=1)), 422, "복용 기간이 아닌 날이에요: 세토펜현탁액"),
            # 코대원시럽은 3일 — 오늘(3일째)까지만
            (path, body(bedtime, "자기 전", TODAY + timedelta(days=1)), 422, "앞으로 먹일 약은 미리 체크할 수 없어요."),
            (path, {"dose_date": TODAY.isoformat(), "items": []}, 422, "체크할 약을 1개 이상 보내 주세요."),
            (f"/prescriptions/{pending.id}/doses", body(syrup, "아침"), 409, "처방을 먼저 확정해 주세요."),
        ]
        for target, payload, code, message in cases:
            response = await send("PUT", target, json=payload, headers=headers)
            assert (response.status_code, response.json()) == (code, {"detail": message}), payload
        assert not await MedicationDoseLog.exists()

    async def test_course_end_is_inclusive(self) -> None:
        headers = await login("doseend@example.com")
        child_id = await make_child(headers)
        prescription = await Prescription.create(
            child_id=child_id,
            source_type=SourceType.PRESCRIPTION,
            status=PrescriptionStatus.GUIDE_DONE,
            prescription_date=TODAY - timedelta(days=3),
            diagnosis_user_input="감기",
        )
        medication = await Medication.create(prescription=prescription, name="코대원시럽", daily_count=2, total_days=3)
        path = f"/prescriptions/{prescription.id}/doses"

        def body(day: date) -> dict[str, object]:
            return {
                "dose_date": day.isoformat(),
                "items": [{"medication_id": medication.id, "slot": "저녁", "is_taken": True}],
            }

        assert (await send("PUT", path, json=body(TODAY - timedelta(days=1)), headers=headers)).status_code == 200
        assert (await send("PUT", path, json=body(TODAY), headers=headers)).status_code == 422

    async def test_only_my_child_and_prescription(self) -> None:
        mine = await login("doseowner@example.com")
        other = await login("dosestranger@example.com")
        child_id = await make_child(mine)
        prescription = await make_prescription(child_id)
        syrup = await med_id(prescription, "세토펜현탁액")
        payload = {
            "dose_date": TODAY.isoformat(),
            "items": [{"medication_id": syrup, "slot": "아침", "is_taken": True}],
        }

        assert (await send("GET", f"/children/{child_id}/doses", headers=other)).status_code == 404
        response = await send("PUT", f"/prescriptions/{prescription.id}/doses", json=payload, headers=other)
        assert (response.status_code, response.json()) == (404, {"detail": "처방전을 찾을 수 없어요."})
        assert (await send("GET", f"/children/{child_id}/doses")).status_code == 401
        assert (await send("PUT", f"/prescriptions/{prescription.id}/doses", json=payload)).status_code == 401
        assert not await MedicationDoseLog.exists()

    async def test_deleting_child_removes_dose_logs(self) -> None:
        headers = await login("dosedelete@example.com")
        child_id = (await post("/children", json=child_payload(name="지울아이"), headers=headers)).json()["child_id"]
        prescription = await make_prescription(child_id)
        syrup = await med_id(prescription, "세토펜현탁액")
        await send(
            "PUT",
            f"/prescriptions/{prescription.id}/doses",
            json={
                "dose_date": TODAY.isoformat(),
                "items": [{"medication_id": syrup, "slot": "아침", "is_taken": True}],
            },
            headers=headers,
        )
        assert await MedicationDoseLog.exists()

        assert (await send("DELETE", f"/children/{child_id}", headers=headers)).status_code == 204
        assert not await MedicationDoseLog.exists()
