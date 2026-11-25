from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, field_serializer

from app.core import config
from app.models.prescriptions import PrescriptionStatus, SourceType


class OcrConfidenceJudgement(BaseModel):
    """신뢰도 판정 (ocr.ocr_confidence_policy). RETAKE는 저장하지 않으므로 201 응답에는 OK·REVIEW만 온다."""

    level: Literal["OK", "REVIEW"]
    min_confidence: float | None
    low_confidence_count: int


class RegisteredMedication(BaseModel):
    medication_id: int
    name: str
    insurance_code: str | None
    dose_per_time: float | None
    unit: str | None
    daily_count: int | None
    total_days: int | None
    as_needed: bool
    max_daily_count: int | None
    usage: str | None
    route: str | None
    dosage_form: str | None
    confidence: float | None
    low_confidence: bool
    is_user_edited: bool


class PrescriptionRegistrationResponse(BaseModel):
    """5번 처방전 등록 응답. 6번 상세와 같은 형식에 ocr_confidence를 더했다."""

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
    ocr_confidence: OcrConfidenceJudgement
    medications: list[RegisteredMedication]

    @field_serializer("created_at")
    def _serialize_kst(self, value: datetime) -> str:
        # 명세서 1절: 일시는 ISO 8601 + KST (2026-11-20T10:30:00+09:00)
        if value.tzinfo is None:
            value = value.replace(tzinfo=config.TIMEZONE)
        return value.astimezone(config.TIMEZONE).isoformat(timespec="seconds")
