from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from httpx import ASGITransport, AsyncClient, Response
from starlette import status
from tortoise.contrib.test import TestCase
from tortoise.timezone import now

from app.main import app
from app.models.children import Child
from app.models.guides import Guide
from app.models.medications import Medication
from app.models.prescriptions import Prescription, PrescriptionStatus, SourceType
from app.tests.auth_apis.helpers import BASE_URL
from app.tests.prescription_registration_apis.test_prescription_registration_api import login, make_child

PRESIGNED_URL = "https://example.com/rx.png"


async def get(path: str, headers: dict[str, str]) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
        return await client.get(f"/api/v1{path}", headers=headers)


async def make_prescription(child: Child, hospital: str = "해솔소아청소년과의원") -> Prescription:
    prescription = await Prescription.create(
        child=child,
        source_type=SourceType.PRESCRIPTION,
        status=PrescriptionStatus.OCR_DONE,
        prescription_date="2026-11-12",
        hospital_name=hospital,
        diagnosis_extracted="J00",
        image_storage_key="prescriptions/1/abc.png",
    )
    for name, confidence in (("세토펜현탁액", "0.95"), ("코대원시럽", "0.70")):
        await Medication.create(
            prescription=prescription,
            name=name,
            dose_per_time=Decimal("4.2"),
            unit="mL",
            daily_count=3,
            total_days=5,
            usage="식후 30분",
            confidence=Decimal(confidence),
        )
    return prescription


class TestPrescriptionQueryAPI(TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.presign = patch(
            "app.services.prescription_registration.get_presigned_url", Mock(return_value=PRESIGNED_URL)
        )
        self.presign.start()

    async def asyncTearDown(self) -> None:
        self.presign.stop()
        await super().asyncTearDown()

    async def test_detail_returns_medications_in_saved_order(self) -> None:
        headers = await login("detail@example.com")
        prescription = await make_prescription(await make_child("detail@example.com"))

        response = await get(f"/prescriptions/{prescription.id}", headers)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["prescription_id"] == prescription.id
        assert body["hospital_name"] == "해솔소아청소년과의원"
        assert body["image_url"] == PRESIGNED_URL
        assert body["has_guide"] is False
        assert body["created_at"].endswith("+09:00")
        assert "ocr_confidence" not in body
        assert [m["name"] for m in body["medications"]] == ["세토펜현탁액", "코대원시럽"]
        assert [m["low_confidence"] for m in body["medications"]] == [False, True]
        assert body["medications"][0]["dose_per_time"] == 4.2

    async def test_detail_hides_image_after_retention_and_reports_guide(self) -> None:
        headers = await login("old@example.com")
        prescription = await make_prescription(await make_child("old@example.com"))
        await Prescription.filter(id=prescription.id).update(created_at=now() - timedelta(days=7))
        await Guide.create(prescription=prescription, guide_content={})

        body = (await get(f"/prescriptions/{prescription.id}", headers)).json()

        assert body["image_url"] is None
        assert body["has_guide"] is True

    async def test_detail_of_someone_elses_prescription_is_404(self) -> None:
        await login("owner@example.com")
        prescription = await make_prescription(await make_child("owner@example.com"))
        stranger = await login("stranger@example.com")

        response = await get(f"/prescriptions/{prescription.id}", stranger)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "처방전을 찾을 수 없어요."

    async def test_list_is_newest_first_with_medication_count(self) -> None:
        headers = await login("list@example.com")
        child = await make_child("list@example.com")
        older = await make_prescription(child, hospital="예전의원")
        await Prescription.filter(id=older.id).update(created_at=now() - timedelta(days=3))
        newer = await make_prescription(child, hospital="요즘의원")

        response = await get(f"/children/{child.id}/prescriptions", headers)

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert [p["prescription_id"] for p in body] == [newer.id, older.id]
        assert body[0]["hospital_name"] == "요즘의원"
        assert body[0]["medication_count"] == 2
        assert body[0]["status"] == "OCR_DONE"

    async def test_list_of_child_without_prescriptions_is_empty(self) -> None:
        headers = await login("none@example.com")
        child = await make_child("none@example.com")

        response = await get(f"/children/{child.id}/prescriptions", headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    async def test_list_of_someone_elses_child_is_404(self) -> None:
        await login("parent-a@example.com")
        child = await make_child("parent-a@example.com")
        stranger = await login("parent-b@example.com")

        response = await get(f"/children/{child.id}/prescriptions", stranger)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_requires_login(self) -> None:
        response = await get("/prescriptions/1", {})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
