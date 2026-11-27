"""DELETE /prescriptions/{prescription_id} 처방 이력 삭제 (명세 9절, 요구사항 MED-002).

명세에는 경로만 있어 아래 동작은 테스트로 정한다.
- 성공하면 204, 본문 없음
- 약·가이드·복약 알림도 함께 지운다
- 원본 사진이 남아 있으면 저장소에서도 지운다. 사진 삭제가 실패해도 처방 삭제는 성공한다
  (사진은 S3 Lifecycle Rule로 7일 뒤 어차피 지워진다)
- 없거나 남의 처방전이면 404, 남의 처방전은 그대로 남는다
"""

from datetime import date, time
from unittest.mock import Mock, patch

from httpx import ASGITransport, AsyncClient, Response
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.guides import Guide
from app.models.medication_alarms import MedicationAlarm
from app.models.medications import Medication
from app.models.prescriptions import Prescription
from app.tests.auth_apis.helpers import BASE_URL
from app.tests.prescription_query_apis.test_prescription_query_api import make_prescription
from app.tests.prescription_registration_apis.test_prescription_registration_api import login, make_child

# 서비스가 delete_image를 어떻게 가져오든 결국 이 함수로 저장소를 얻는다.
IMAGE_STORAGE = "app.core.storage.factory.get_image_storage"


async def delete(path: str, headers: dict[str, str]) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
        return await client.delete(f"/api/v1{path}", headers=headers)


class TestPrescriptionDeletionAPI(TestCase):
    async def asyncSetUp(self) -> None:
        await super().asyncSetUp()
        self.storage = Mock()
        self.storage_patch = patch(IMAGE_STORAGE, Mock(return_value=self.storage))
        self.storage_patch.start()

    async def asyncTearDown(self) -> None:
        self.storage_patch.stop()
        await super().asyncTearDown()

    async def test_delete_returns_204_and_removes_prescription(self) -> None:
        headers = await login("delete@example.com")
        prescription = await make_prescription(await make_child("delete@example.com"))

        response = await delete(f"/prescriptions/{prescription.id}", headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert response.content == b""
        assert not await Prescription.exists(id=prescription.id)

    async def test_delete_removes_medications_guide_and_alarms(self) -> None:
        headers = await login("cascade@example.com")
        prescription = await make_prescription(await make_child("cascade@example.com"))
        await Guide.create(prescription=prescription, guide_content={})
        medication = await Medication.filter(prescription_id=prescription.id).first()
        assert medication is not None
        await MedicationAlarm.create(
            medication=medication, notify_time=time(8, 0), start_date=date(2026, 11, 12), end_date=date(2026, 11, 16)
        )

        await delete(f"/prescriptions/{prescription.id}", headers)

        assert not await Medication.exists(prescription_id=prescription.id)
        assert not await Guide.exists(prescription_id=prescription.id)
        assert not await MedicationAlarm.exists(medication_id=medication.id)

    async def test_delete_removes_original_image_from_storage(self) -> None:
        headers = await login("image@example.com")
        prescription = await make_prescription(await make_child("image@example.com"))

        await delete(f"/prescriptions/{prescription.id}", headers)

        self.storage.delete_image.assert_called_once_with("prescriptions/1/abc.png")

    async def test_delete_without_image_key_does_not_touch_storage(self) -> None:
        headers = await login("noimage@example.com")
        prescription = await make_prescription(await make_child("noimage@example.com"))
        await Prescription.filter(id=prescription.id).update(image_storage_key=None)  # 가이드 생성 후 상태

        response = await delete(f"/prescriptions/{prescription.id}", headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.storage.delete_image.assert_not_called()

    async def test_delete_succeeds_even_if_image_delete_fails(self) -> None:
        headers = await login("s3down@example.com")
        prescription = await make_prescription(await make_child("s3down@example.com"))
        self.storage.delete_image.side_effect = RuntimeError("S3 unavailable")

        response = await delete(f"/prescriptions/{prescription.id}", headers)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not await Prescription.exists(id=prescription.id)

    async def test_delete_keeps_other_prescriptions_of_same_child(self) -> None:
        headers = await login("sibling@example.com")
        child = await make_child("sibling@example.com")
        target = await make_prescription(child, hospital="지울의원")
        other = await make_prescription(child, hospital="남길의원")

        await delete(f"/prescriptions/{target.id}", headers)

        assert not await Prescription.exists(id=target.id)
        assert await Prescription.exists(id=other.id)
        assert await Medication.filter(prescription_id=other.id).count() == 2

    async def test_delete_someone_elses_prescription_is_404_and_keeps_it(self) -> None:
        await login("rx-owner@example.com")
        prescription = await make_prescription(await make_child("rx-owner@example.com"))
        stranger = await login("rx-stranger@example.com")

        response = await delete(f"/prescriptions/{prescription.id}", stranger)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "처방전을 찾을 수 없어요."
        assert await Prescription.exists(id=prescription.id)
        self.storage.delete_image.assert_not_called()

    async def test_delete_missing_prescription_is_404(self) -> None:
        headers = await login("missing@example.com")

        response = await delete("/prescriptions/999999", headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json()["detail"] == "처방전을 찾을 수 없어요."

    async def test_delete_requires_login(self) -> None:
        response = await delete("/prescriptions/1", {})

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
