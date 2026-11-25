from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from app.dependencies.ownership import get_my_child_or_404
from app.dependencies.security import CurrentGuardian
from app.dtos.prescription_registration import (
    OcrConfidenceJudgement,
    PrescriptionRegistrationResponse,
    RegisteredMedication,
)
from app.models.prescriptions import SourceType
from app.services.prescription_registration import (
    OcrFailedError,
    OcrLowConfidenceError,
    PrescriptionImageError,
    image_url_of,
    low_confidence_of,
    register_prescription,
)

prescription_registration_router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

OCR_LOW_CONFIDENCE_CODE = "OCR_LOW_CONFIDENCE"


@prescription_registration_router.post(
    "",
    response_model=PrescriptionRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        422: {"description": "사진 형식·용량 오류, 또는 신뢰도가 낮아 다시 찍어야 함 (code: OCR_LOW_CONFIDENCE)"},
        502: {"description": "OCR 실패·시간 초과"},
    },
)
async def create_prescription(
    guardian: CurrentGuardian,
    child_id: Annotated[int, Form()],
    source_type: Annotated[SourceType, Form()],
    image: Annotated[UploadFile, File()],
    diagnosis_user_input: Annotated[str | None, Form()] = None,
    symptom_notes: Annotated[str | None, Form()] = None,
) -> PrescriptionRegistrationResponse | JSONResponse:
    """5. 처방전 등록 + OCR

    가장 낮은 약 신뢰도가 0.6 미만이거나 약을 하나도 읽지 못하면 저장하지 않고
    `422 {"detail": ..., "code": "OCR_LOW_CONFIDENCE"}`로 다시 찍기를 요청한다.
    """
    child = await get_my_child_or_404(child_id, guardian)
    data = await image.read()

    try:
        prescription, medications, judgement = await register_prescription(
            child=child,
            source_type=source_type,
            image=data,
            content_type=image.content_type or "",
            diagnosis_user_input=diagnosis_user_input,
            symptom_notes=symptom_notes,
        )
    except PrescriptionImageError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error
    except OcrLowConfidenceError as error:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": str(error), "code": OCR_LOW_CONFIDENCE_CODE},
        )
    except OcrFailedError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

    return PrescriptionRegistrationResponse(
        prescription_id=prescription.id,
        child_id=child.id,
        source_type=prescription.source_type,
        status=prescription.status,
        prescription_date=prescription.prescription_date,
        hospital_name=prescription.hospital_name,
        diagnosis_extracted=prescription.diagnosis_extracted,
        diagnosis_user_input=prescription.diagnosis_user_input,
        symptom_notes=prescription.symptom_notes,
        image_url=await run_in_threadpool(image_url_of, prescription),
        has_guide=False,
        created_at=prescription.created_at,
        ocr_confidence=OcrConfidenceJudgement(**judgement),
        medications=[
            RegisteredMedication(
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
            for medication in medications
        ],
    )
