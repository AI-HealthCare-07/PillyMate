import re
from datetime import date, time
from decimal import Decimal
from unittest.mock import Mock, patch

from httpx import ASGITransport, AsyncClient, Response
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.children import Child
from app.models.guides import Guide
from app.models.medication_alarms import MedicationAlarm
from app.models.medications import Medication
from app.models.prescriptions import Prescription, PrescriptionStatus, SourceType
from app.tests.auth_apis.helpers import BASE_URL, birth_date_years_ago, get, post, signup_payload


async def send(method: str, path: str, json: object | None = None, headers: dict[str, str] | None = None) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
        return await client.request(method, f"/api/v1{path}", json=json, headers=headers)


async def login(email: str) -> dict[str, str]:
    await post("/auth/signup", json=signup_payload(email=email))
    response = await post("/auth/login", json={"email": email, "password": "pilly1234!"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def child_payload(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "name": "민준",
        "birth_date": "2021-03-02",
        "consent_agreed": True,
        "weight_kg": 18.5,
        "allergies": "계란",
        "notes": "열성 경련 이력 있음",
    }
    data.update(overrides)
    return data


class TestChildAPI(TestCase):
    async def test_register_child_and_list_only_mine(self) -> None:
        mine = await login("mom@example.com")
        other = await login("other@example.com")

        created = await post("/children", json=child_payload(), headers=mine)
        await post("/children", json=child_payload(name="서아", weight_kg=None, allergies="", notes=None), headers=mine)
        await post("/children", json=child_payload(name="남의아이"), headers=other)

        assert created.status_code == status.HTTP_201_CREATED
        body = created.json()
        assert body["name"] == "민준"
        assert body["birth_date"] == "2021-03-02"
        assert body["weight_kg"] == 18.5
        assert body["allergies"] == "계란"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00", body["created_at"])
        stored = await Child.get(id=body["child_id"])
        assert stored.consent_agreed_at is not None

        listed = await get("/children", headers=mine)
        assert listed.status_code == status.HTTP_200_OK
        assert [c["name"] for c in listed.json()] == ["민준", "서아"]
        assert listed.json()[1]["weight_kg"] is None
        assert listed.json()[1]["allergies"] is None

    async def test_empty_list(self) -> None:
        headers = await login("empty@example.com")
        response = await get("/children", headers=headers)
        assert response.json() == []

    async def test_requires_login(self) -> None:
        assert (await get("/children")).status_code == status.HTTP_401_UNAUTHORIZED
        assert (await post("/children", json=child_payload())).status_code == status.HTTP_401_UNAUTHORIZED

    async def test_rules_use_spec_messages(self) -> None:
        headers = await login("rules@example.com")
        cases = [
            (child_payload(consent_agreed=False), 422, "보호자 동의 3가지에 모두 동의해 주세요."),
            (child_payload(birth_date=birth_date_years_ago(18)), 422, "만 18세 미만 자녀만 등록할 수 있어요."),
            (child_payload(birth_date=birth_date_years_ago(0, days=3)), 422, "생년월일을 다시 확인해 주세요."),
            (child_payload(weight_kg=0.4), 422, "체중은 0.5~150kg 사이로 입력해 주세요."),
            (child_payload(weight_kg=150.1), 422, "체중은 0.5~150kg 사이로 입력해 주세요."),
            (child_payload(name="  "), 400, "필수 항목을 입력해 주세요: name"),
        ]
        for payload, code, message in cases:
            response = await post("/children", json=payload, headers=headers)
            assert (response.status_code, response.json()) == (code, {"detail": message}), payload

        assert await Child.filter(guardian__email="rules@example.com").count() == 0

    async def test_age_just_under_limit_is_allowed(self) -> None:
        headers = await login("edge@example.com")
        response = await post(
            "/children", json=child_payload(birth_date=birth_date_years_ago(18, days=1)), headers=headers
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_missing_consent_field_is_400(self) -> None:
        headers = await login("missing@example.com")
        payload = child_payload()
        del payload["consent_agreed"]
        response = await post("/children", json=payload, headers=headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "필수 항목을 입력해 주세요: consent_agreed"}


async def seed_records(child_id: int, image_key: str) -> Prescription:
    """처방·약·가이드·복약 알림을 한 벌 만든다 (삭제 시 CASCADE 확인용)."""
    prescription = await Prescription.create(
        child_id=child_id,
        source_type=SourceType.PRESCRIPTION,
        status=PrescriptionStatus.GUIDE_DONE,
        prescription_date="2026-11-12",
        hospital_name="해솔소아청소년과의원",
        diagnosis_user_input="감기",
        image_storage_key=image_key,
    )
    medication = await Medication.create(
        prescription=prescription,
        name="세토펜현탁액",
        dose_per_time=Decimal("4.2"),
        unit="mL",
        daily_count=3,
        total_days=5,
    )
    await Guide.create(prescription=prescription, guide_content={})
    await MedicationAlarm.create(
        medication=medication, notify_time=time(8, 0), start_date=date(2026, 11, 12), end_date=date(2026, 11, 16)
    )
    return prescription


class TestChildEditDeleteAPI(TestCase):
    async def test_patch_changes_only_sent_fields(self) -> None:
        headers = await login("edit@example.com")
        child_id = (await post("/children", json=child_payload(), headers=headers)).json()["child_id"]

        response = await send(
            "PATCH", f"/children/{child_id}", json={"name": " 민준이 ", "weight_kg": 19.25}, headers=headers
        )

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert (body["name"], body["weight_kg"], body["allergies"], body["notes"]) == (
            "민준이",
            19.25,
            "계란",
            "열성 경련 이력 있음",
        )
        stored = await Child.get(id=child_id)
        assert (stored.name, stored.weight_kg, stored.birth_date) == ("민준이", Decimal("19.25"), date(2021, 3, 2))
        # 다시 불러와도(새로고침·재로그인) 바뀐 값
        assert (await get("/children", headers=headers)).json()[0]["name"] == "민준이"

    async def test_patch_null_or_blank_clears_optional_fields(self) -> None:
        headers = await login("clear@example.com")
        child_id = (await post("/children", json=child_payload(), headers=headers)).json()["child_id"]

        response = await send(
            "PATCH", f"/children/{child_id}", json={"weight_kg": None, "allergies": " ", "notes": None}, headers=headers
        )

        body = response.json()
        assert (body["weight_kg"], body["allergies"], body["notes"]) == (None, None, None)

    async def test_patch_uses_registration_rules(self) -> None:
        headers = await login("patchrules@example.com")
        child_id = (await post("/children", json=child_payload(), headers=headers)).json()["child_id"]
        cases = [
            ({"name": "  "}, 400, "필수 항목을 입력해 주세요: name"),
            ({"birth_date": None}, 400, "필수 항목을 입력해 주세요: birth_date"),
            ({"birth_date": birth_date_years_ago(18)}, 422, "만 18세 미만 자녀만 등록할 수 있어요."),
            ({"birth_date": birth_date_years_ago(0, days=3)}, 422, "생년월일을 다시 확인해 주세요."),
            ({"weight_kg": 150.1}, 422, "체중은 0.5~150kg 사이로 입력해 주세요."),
        ]
        for payload, code, message in cases:
            response = await send("PATCH", f"/children/{child_id}", json=payload, headers=headers)
            assert (response.status_code, response.json()) == (code, {"detail": message}), payload

        stored = await Child.get(id=child_id)
        assert (stored.name, stored.weight_kg) == ("민준", Decimal("18.50"))

    async def test_someone_elses_child_is_404(self) -> None:
        mine = await login("owner@example.com")
        other = await login("stranger@example.com")
        child_id = (await post("/children", json=child_payload(), headers=mine)).json()["child_id"]

        for method, payload in (("PATCH", {"name": "바꿈"}), ("DELETE", None)):
            response = await send(method, f"/children/{child_id}", json=payload, headers=other)
            assert (response.status_code, response.json()) == (404, {"detail": "자녀 정보를 찾을 수 없어요."})
        assert (await send("PATCH", "/children/999999", json={"name": "x"}, headers=mine)).status_code == 404

        stored = await Child.get(id=child_id)
        assert stored.name == "민준"

    async def test_requires_login(self) -> None:
        assert (await send("PATCH", "/children/1", json={"name": "x"})).status_code == status.HTTP_401_UNAUTHORIZED
        assert (await send("DELETE", "/children/1")).status_code == status.HTTP_401_UNAUTHORIZED

    async def test_delete_removes_child_records_and_original_photo(self) -> None:
        headers = await login("delete@example.com")
        child_id = (await post("/children", json=child_payload(), headers=headers)).json()["child_id"]
        sibling_id = (await post("/children", json=child_payload(name="서아"), headers=headers)).json()["child_id"]
        gone = await seed_records(child_id, "prescriptions/1/gone.png")
        kept = await seed_records(sibling_id, "prescriptions/2/kept.png")

        with patch("app.services.children.delete_image", Mock()) as delete_image:
            response = await send("DELETE", f"/children/{child_id}", headers=headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""
        delete_image.assert_called_once_with("prescriptions/1/gone.png")
        assert not await Child.exists(id=child_id)
        assert not await Prescription.exists(id=gone.id)
        assert not await Medication.exists(prescription_id=gone.id)
        assert not await Guide.exists(prescription_id=gone.id)
        assert not await MedicationAlarm.exists(medication__prescription_id=gone.id)
        # 다른 아이 기록은 그대로
        assert await Prescription.exists(id=kept.id)
        assert await MedicationAlarm.exists(medication__prescription_id=kept.id)
        assert [c["child_id"] for c in (await get("/children", headers=headers)).json()] == [sibling_id]
        # 지운 아이는 다시 조회·수정·삭제할 수 없다
        assert (await get(f"/children/{child_id}/prescriptions", headers=headers)).status_code == 404
        assert (await send("DELETE", f"/children/{child_id}", headers=headers)).status_code == 404

    async def test_delete_succeeds_even_if_photo_removal_fails(self) -> None:
        headers = await login("photofail@example.com")
        child_id = (await post("/children", json=child_payload(), headers=headers)).json()["child_id"]
        await seed_records(child_id, "prescriptions/1/x.png")

        with patch("app.services.children.delete_image", Mock(side_effect=RuntimeError("s3 down"))):
            response = await send("DELETE", f"/children/{child_id}", headers=headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not await Child.exists(id=child_id)
