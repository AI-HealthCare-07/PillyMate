"""6번 처방전 상세, 10번 자녀별 처방전 목록 응답."""

from datetime import date, datetime

from pydantic import BaseModel, field_serializer

from app.core import config
from app.dtos.prescription_registration import RegisteredMedication
from app.models.prescriptions import PrescriptionStatus, SourceType


def _to_kst_iso(value: datetime) -> str:
    # 명세서 1절: 일시는 ISO 8601 + KST (2026-11-20T10:30:00+09:00)
    if value.tzinfo is None:
        value = value.replace(tzinfo=config.TIMEZONE)
    return value.astimezone(config.TIMEZONE).isoformat(timespec="seconds")


class PrescriptionDetailResponse(BaseModel):
    """6번 처방전 상세. 5번 등록 응답에서 ocr_confidence만 뺀 형식이다."""

    prescription_id: int
    child_id: int
    source_type: SourceType
    status: PrescriptionStatus
    prescription_date: date | None
    hospital_name: str | None
    diagnosis_extracted: str | None
    diagnosis_user_input: str | None
    symptom_notes: str | None
    image_url: str | None
    has_guide: bool
    created_at: datetime
    medications: list[RegisteredMedication]

    @field_serializer("created_at")
    def _serialize_kst(self, value: datetime) -> str:
        return _to_kst_iso(value)


class PrescriptionSummaryResponse(BaseModel):
    """10번 처방전 목록의 한 줄. 약 내용은 6번 상세로 받는다."""

    prescription_id: int
    source_type: SourceType
    status: PrescriptionStatus
    prescription_date: date | None
    diagnosis_user_input: str | None
    hospital_name: str | None
    medication_count: int
    created_at: datetime

    @field_serializer("created_at")
    def _serialize_kst(self, value: datetime) -> str:
        return _to_kst_iso(value)
