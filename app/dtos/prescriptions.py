"""처방 확정·가이드 API의 요청/응답 형식 (API 명세서 v1.0 7·8·9번).

필수값 누락(400)과 약 규칙(422)은 명세서 문구 그대로 내려고 서비스에서 검사한다.
그래서 여기서는 대부분 None을 허용해 두었다.

요청·응답 형식 (명세서 7·8·9번)
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from app.dtos.base import BaseSerializerModel
from app.models.prescriptions import DosageForm, PrescriptionStatus, Route, SourceType

Unit = Literal["mL", "포", "정", "캡슐", "g", "방울", "개"]


class MedicationConfirmItem(BaseModel):
    medication_id: Annotated[
        int | None, Field(None, description="OCR로 만들어진 약이면 그 id, 사용자가 새로 넣은 약이면 null")
    ]
    name: Annotated[str | None, Field(None, max_length=100)]
    dose_per_time: Annotated[Decimal | None, Field(None, gt=0, max_digits=7, decimal_places=2)]
    unit: Unit | None = None
    daily_count: Annotated[int | None, Field(None, ge=1, le=24, description="필요시 약이면 null")]
    total_days: Annotated[int | None, Field(None, ge=1, le=365)]
    as_needed: bool = False
    max_daily_count: Annotated[int | None, Field(None, ge=1, le=24, description="필요시 약이면 필수")]
    usage: Annotated[str | None, Field(None, max_length=100)]
    route: Route | None = None
    dosage_form: DosageForm | None = None


class PrescriptionConfirmRequest(BaseModel):
    prescription_date: date | None = None
    hospital_name: Annotated[str | None, Field(None, max_length=100)]
    diagnosis_user_input: Annotated[str | None, Field(None, max_length=200)]
    symptom_notes: str | None = None
    medications: list[MedicationConfirmItem] = Field(default_factory=list)


class MedicationResponse(BaseSerializerModel):
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
    route: Route | None
    dosage_form: DosageForm | None
    confidence: float | None
    is_user_edited: bool


class PrescriptionDetailResponse(BaseSerializerModel):
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
    medications: list[MedicationResponse]


class GuideResponse(BaseSerializerModel):
    guide_id: int
    prescription_id: int
    created_at: datetime
    guide_content: dict[str, Any]
