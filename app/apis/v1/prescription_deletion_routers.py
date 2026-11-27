from fastapi import APIRouter, status

from app.dependencies.ownership import MyPrescription
from app.services.prescription_deletion import delete_prescription

prescription_deletion_router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


@prescription_deletion_router.delete(
    "/{prescription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "없거나 내 처방전이 아님"}},
)
async def remove_prescription(prescription: MyPrescription) -> None:
    """9절 처방 이력 삭제 — 약·가이드·복약 알림과 남아 있는 원본 사진까지 지운다."""
    await delete_prescription(prescription)
