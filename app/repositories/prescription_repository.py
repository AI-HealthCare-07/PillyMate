"""처방·약·가이드 DB 조회와 저장만 담당한다. 규칙 검사는 services/prescriptions.py에서 한다."""

from typing import Any

from app.models.guides import Guide
from app.models.medications import Medication
from app.models.prescriptions import Prescription


class PrescriptionRepository:
    async def get_for_guardian(self, prescription_id: int, guardian_id: int) -> Prescription | None:
        """보호자 본인 자녀의 처방만 찾는다. 남의 처방이면 None (→ 404, 있는지조차 알려주지 않음)."""
        return await Prescription.get_or_none(id=prescription_id, child__guardian_id=guardian_id).prefetch_related(
            "child"
        )

    async def get_medications(self, prescription_id: int) -> list[Medication]:
        return await Medication.filter(prescription_id=prescription_id).order_by("id")

    async def has_guide(self, prescription_id: int) -> bool:
        return await Guide.exists(prescription_id=prescription_id)

    async def get_guide(self, prescription_id: int) -> Guide | None:
        return await Guide.get_or_none(prescription_id=prescription_id)

    async def update_prescription(self, prescription: Prescription, data: dict[str, Any]) -> None:
        for key, value in data.items():
            setattr(prescription, key, value)
        await prescription.save(update_fields=[*data.keys(), "updated_at"])

    async def update_medication(self, medication: Medication, data: dict[str, Any]) -> None:
        for key, value in data.items():
            setattr(medication, key, value)
        await medication.save(update_fields=[*data.keys(), "updated_at"])

    async def create_medication(self, prescription_id: int, data: dict[str, Any]) -> Medication:
        return await Medication.create(prescription_id=prescription_id, **data)

    async def delete_medications(self, medication_ids: list[int]) -> None:
        if medication_ids:
            await Medication.filter(id__in=medication_ids).delete()

    async def create_guide(self, prescription_id: int, guide_content: dict[str, Any]) -> Guide:
        return await Guide.create(prescription_id=prescription_id, guide_content=guide_content)
