"""6번 처방전 상세, 10번 자녀별 처방전 목록 조회.

소유권 확인은 라우터의 MyChild·MyPrescription 의존성이 한다 (남의 데이터는 404).
"""

from datetime import timedelta

from starlette.concurrency import run_in_threadpool
from tortoise.functions import Count
from tortoise.timezone import now

from app.dtos.prescription_query import PrescriptionDetailResponse, PrescriptionSummaryResponse
from app.dtos.prescription_registration import RegisteredMedication
from app.models.children import Child
from app.models.guides import Guide
from app.models.medications import Medication
from app.models.prescriptions import Prescription
from app.services.prescription_registration import image_url_of, low_confidence_of

# 명세 6번: 원본 사진은 S3 Lifecycle Rule로 7일 뒤 지워진다. 서버는 키가 아니라 생성일로 판단한다.
IMAGE_RETENTION = timedelta(days=7)


def to_registered_medication(medication: Medication) -> RegisteredMedication:
    return RegisteredMedication(
        medication_id=medication.id,
        name=medication.name,
        insurance_code=medication.insurance_code,
        dose_per_time=None if medication.dose_per_time is None else float(medication.dose_per_time),
        unit=medication.unit,
        daily_count=medication.daily_count,
        total_days=medication.total_days,
        as_needed=medication.as_needed,
        max_daily_count=medication.max_daily_count,
        usage=medication.usage,
        route=medication.route,
        dosage_form=medication.dosage_form,
        confidence=None if medication.confidence is None else float(medication.confidence),
        low_confidence=low_confidence_of(medication),
        is_user_edited=medication.is_user_edited,
    )


async def retained_image_url_of(prescription: Prescription) -> str | None:
    """보관 기간(7일)이 지났거나 가이드 생성 후 키를 지웠으면 None."""
    if now() - prescription.created_at >= IMAGE_RETENTION:
        return None
    return await run_in_threadpool(image_url_of, prescription)


async def get_prescription_detail(prescription: Prescription) -> PrescriptionDetailResponse:
    medications = await Medication.filter(prescription_id=prescription.id).order_by("id")
    return PrescriptionDetailResponse(
        prescription_id=prescription.id,
        child_id=prescription.child_id,  # type: ignore[attr-defined]
        source_type=prescription.source_type,
        status=prescription.status,
        prescription_date=prescription.prescription_date,
        hospital_name=prescription.hospital_name,
        diagnosis_extracted=prescription.diagnosis_extracted,
        diagnosis_user_input=prescription.diagnosis_user_input,
        symptom_notes=prescription.symptom_notes,
        image_url=await retained_image_url_of(prescription),
        has_guide=await Guide.exists(prescription_id=prescription.id),
        created_at=prescription.created_at,
        medications=[to_registered_medication(medication) for medication in medications],
    )


async def list_child_prescriptions(child: Child) -> list[PrescriptionSummaryResponse]:
    """최신 등록순. 없으면 []."""
    prescriptions = (
        await Prescription.filter(child_id=child.id)
        .annotate(medication_count=Count("medications"))
        .order_by("-created_at", "-id")
    )
    return [
        PrescriptionSummaryResponse(
            prescription_id=prescription.id,
            source_type=prescription.source_type,
            status=prescription.status,
            prescription_date=prescription.prescription_date,
            diagnosis_user_input=prescription.diagnosis_user_input,
            hospital_name=prescription.hospital_name,
            medication_count=prescription.medication_count,  # type: ignore[attr-defined]
            created_at=prescription.created_at,
        )
        for prescription in prescriptions
    ]
