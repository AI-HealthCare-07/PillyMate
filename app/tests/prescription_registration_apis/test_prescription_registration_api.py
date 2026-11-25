from typing import Any
from unittest.mock import Mock, patch

from httpx import ASGITransport, AsyncClient, Response
from starlette import status
from tortoise.contrib.test import TestCase
from tortoise.timezone import now

from app.main import app
from app.models.children import Child
from app.models.medications import Medication
from app.models.prescriptions import Prescription
from app.tests.auth_apis.helpers import BASE_URL, post, signup_payload
from ocr import OcrRequestError

SERVICE = "app.services.prescription_registration"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32
IMAGE_KEY = "prescriptions/1/abc.png"


def ocr_result(*confidences: float | None) -> dict[str, Any]:
    return {
        "prescription_date": "2026-11-12",
        "hospital_name": "해솔소아청소년과의원",
        "diagnosis_extracted": "J00",
        "medications": [
            {
                "name": f"세토펜현탁액{i}",
                "insurance_code": "643901230",
                "dose_per_time": 4.2,
                "unit": "mL",
                "daily_count": 3,
                "total_days": 5,
                "max_daily_count": None,
                "as_needed": False,
                "usage": "식후 30분",
                "route": "ORAL",
                "dosage_form": "SYRUP",
                "confidence": confidence,
            }
            for i, confidence in enumerate(confidences)
        ],
    }


async def login(email: str) -> dict[str, str]:
    await post("/auth/signup", json=signup_payload(email=email))
    response = await post("/auth/login", json={"email": email, "password": "pilly1234!"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


async def make_child(email: str) -> Child:
    from app.models.guardians import Guardian

    guardian = await Guardian.get(email=email)
    return await Child.create(guardian=guardian, name="하윤", birth_date="2023-05-12", consent_agreed_at=now())


async def upload(
    headers: dict[str, str], child_id: int, image: bytes = PNG_BYTES, content_type: str = "image/png"
) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
        return await client.post(
            "/api/v1/prescriptions",
            headers=headers,
            data={"child_id": str(child_id), "source_type": "PRESCRIPTION", "symptom_notes": "열이 나요"},
            files={"image": ("rx.png", image, content_type)},
        )


class TestPrescriptionRegistrationAPI(TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.storage = {
            "upload_image": Mock(return_value=IMAGE_KEY),
            "delete_image": Mock(),
            "get_presigned_url": Mock(return_value="https://example.com/rx.png"),
        }
        self.patches = [patch(f"{SERVICE}.{name}", mock) for name, mock in self.storage.items()]
        for patcher in self.patches:
            patcher.start()

    async def asyncTearDown(self) -> None:
        for patcher in self.patches:
            patcher.stop()
        await super().asyncTearDown()

    async def register(self, email: str, result: Any) -> tuple[Response, Child]:
        headers = await login(email)
        child = await make_child(email)
        run_ocr = Mock(side_effect=result) if isinstance(result, Exception) else Mock(return_value=result)
        with patch(f"{SERVICE}.run_ocr", run_ocr):
            return await upload(headers, child.id), child

    async def test_confident_result_is_saved_without_raw_text(self) -> None:
        response, child = await self.register("ok@example.com", ocr_result(0.95, 0.8))

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["status"] == "OCR_DONE"
        assert body["ocr_confidence"] == {"level": "OK", "min_confidence": 0.8, "low_confidence_count": 0}
        assert [m["low_confidence"] for m in body["medications"]] == [False, False]
        assert "raw_text_masked" not in body

        prescription = await Prescription.get(id=body["prescription_id"], child_id=child.id)
        assert prescription.hospital_name == "해솔소아청소년과의원"
        assert prescription.symptom_notes == "열이 나요"
        assert prescription.image_storage_key == IMAGE_KEY
        assert "raw_text_masked" not in Prescription._meta.fields_map
        medications = await Medication.filter(prescription_id=prescription.id).order_by("id")
        assert [float(m.dose_per_time or 0) for m in medications] == [4.2, 4.2]
        assert medications[0].ocr_value_snapshot is not None
        assert medications[0].ocr_value_snapshot["name"] == "세토펜현탁액0"
        self.storage["delete_image"].assert_not_called()

    async def test_medium_confidence_is_saved_and_low_medications_are_flagged(self) -> None:
        response, _ = await self.register("review@example.com", ocr_result(0.95, 0.65))

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert body["ocr_confidence"]["level"] == "REVIEW"
        assert [m["low_confidence"] for m in body["medications"]] == [False, True]

    async def test_low_confidence_asks_for_retake_and_saves_nothing(self) -> None:
        response, child = await self.register("retake@example.com", ocr_result(0.95, 0.59))

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["code"] == "OCR_LOW_CONFIDENCE"
        assert await Prescription.filter(child_id=child.id).count() == 0
        self.storage["delete_image"].assert_called_once_with(IMAGE_KEY)

    async def test_no_medications_asks_for_retake(self) -> None:
        response, child = await self.register("empty@example.com", ocr_result())

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json()["code"] == "OCR_LOW_CONFIDENCE"
        assert await Prescription.filter(child_id=child.id).count() == 0

    async def test_ocr_failure_is_502_and_saves_nothing(self) -> None:
        response, child = await self.register("fail@example.com", OcrRequestError("timeout"))

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.json() == {"detail": "처방전을 읽지 못했어요. 다시 찍어 주세요."}
        assert await Prescription.filter(child_id=child.id).count() == 0
        self.storage["delete_image"].assert_called_once_with(IMAGE_KEY)

    async def test_non_image_file_is_422_before_ocr(self) -> None:
        headers = await login("type@example.com")
        child = await make_child("type@example.com")
        run_ocr = Mock()
        with patch(f"{SERVICE}.run_ocr", run_ocr):
            response = await upload(headers, child.id, image=b"GIF89a", content_type="image/gif")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert response.json() == {"detail": "jpg 또는 png 사진만 올릴 수 있어요."}
        run_ocr.assert_not_called()
        self.storage["upload_image"].assert_not_called()

    async def test_other_guardians_child_is_404(self) -> None:
        await login("owner@example.com")
        child = await make_child("owner@example.com")
        stranger = await login("stranger@example.com")

        response = await upload(stranger, child.id)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "자녀 정보를 찾을 수 없어요."}
