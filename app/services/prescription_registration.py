"""5번 처방전 등록: 사진 저장 → run_ocr() → 신뢰도 판정 → 정리된 결과만 DB 저장.

신뢰도 판정 (ocr/ocr_confidence_policy.py, 11/24 멘토링 3절):
- RETAKE (가장 낮은 약 신뢰도 0.6 미만, 또는 약을 하나도 못 읽음): 처방 행을 만들지 않고 사진을 지운 뒤
  OcrLowConfidenceError. 프론트는 다시 찍기 모달을 띄운다.
- REVIEW (0.6 이상 0.8 미만 포함) / OK (모두 0.8 이상): prescription(OCR_DONE)과 medication 행을 저장한다.

OCR 원문과 마스킹 원문은 저장하지 않는다 (11/24 멘토링 4절). run_ocr()도 원문을 돌려주지 않는다.
OCR 결과 내용은 로그에 남기지 않는다 (명세 5번).
"""

import logging
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from starlette.concurrency import run_in_threadpool
from tortoise.transactions import in_transaction

from app.core.storage import delete_image, get_presigned_url, upload_image
from app.models.children import Child
from app.models.medications import DosageForm, Medication, MedicationUnit, Route
from app.models.prescriptions import Prescription, PrescriptionStatus, SourceType
from ocr import RETAKE, OcrError, OcrInputError, is_low_confidence, judge_ocr_confidence, run_ocr

logger = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 명세 5번: 10MB 이하

IMAGE_TYPE_MESSAGE = "jpg 또는 png 사진만 올릴 수 있어요."
IMAGE_SIZE_MESSAGE = "10MB 이하 사진만 올릴 수 있어요."
OCR_FAILED_MESSAGE = "처방전을 읽지 못했어요. 다시 찍어 주세요."
OCR_LOW_CONFIDENCE_MESSAGE = (
    "사진이 흐릿해서 약 정보를 정확히 읽지 못했어요. 밝은 곳에서 처방전이나 약봉투 전체가 나오게 다시 찍어 주세요."
)


class PrescriptionImageError(Exception):
    """422: 사진 형식·용량 오류"""


class OcrFailedError(Exception):
    """502: OCR 실패·시간 초과. 처방 행은 만들지 않았다."""


class OcrLowConfidenceError(Exception):
    """422 + code OCR_LOW_CONFIDENCE: 신뢰도가 낮아 다시 찍어야 한다. 처방 행은 만들지 않았다."""

    def __init__(self, judgement: dict[str, Any]) -> None:
        super().__init__(OCR_LOW_CONFIDENCE_MESSAGE)
        self.judgement = judgement


def validate_image(data: bytes, content_type: str | None) -> None:
    if not data:
        raise PrescriptionImageError(IMAGE_TYPE_MESSAGE)
    if len(data) > MAX_IMAGE_BYTES:
        raise PrescriptionImageError(IMAGE_SIZE_MESSAGE)
    if content_type not in ("image/jpeg", "image/png"):
        raise PrescriptionImageError(IMAGE_TYPE_MESSAGE)


def _clip(text: str | None, max_length: int) -> str | None:
    return text[:max_length] if text else None


def _parse_date(text: str | None) -> date | None:
    try:
        return date.fromisoformat(text) if text else None
    except ValueError:
        return None


def _int_within(value: int | None, low: int, high: int) -> int | None:
    return value if isinstance(value, int) and low <= value <= high else None


def _dose(value: float | None) -> Decimal | None:
    # DECIMAL(8,4): 0 ~ 9999.9999. 그 밖의 값은 잘못 읽은 숫자로 보고 비워서 보호자가 채우게 한다.
    if value is None or not 0 <= value < 10_000:
        return None
    return Decimal(str(value)).quantize(Decimal("0.0001"))


def _confidence(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value)).quantize(Decimal("0.01"))


def _enum_value(enum_type: type[StrEnum], value: str | None) -> Any:
    if value is None or value not in enum_type.__members__.values():
        return None
    return enum_type(value)


def medication_fields_from_ocr(medication: dict[str, Any]) -> dict[str, Any]:
    """run_ocr() 약 dict → Medication 컬럼. 컬럼 범위를 벗어나는 값은 None으로 둔다."""
    return {
        "name": _clip(medication.get("name"), 100) or "",
        "insurance_code": _clip(medication.get("insurance_code"), 20),
        "dose_per_time": _dose(medication.get("dose_per_time")),
        "unit": _enum_value(MedicationUnit, medication.get("unit")),
        "daily_count": _int_within(medication.get("daily_count"), 0, 127),
        "total_days": _int_within(medication.get("total_days"), 0, 32_767),
        "as_needed": bool(medication.get("as_needed")),
        "max_daily_count": _int_within(medication.get("max_daily_count"), 0, 127),
        "usage": _clip(medication.get("usage"), 100),
        "route": _enum_value(Route, medication.get("route")),
        "dosage_form": _enum_value(DosageForm, medication.get("dosage_form")),
        "confidence": _confidence(medication.get("confidence")),
        # 보호자가 고치기 전 최초 OCR 값 (ERD: 불변 스냅샷). 정리된 항목만 있고 원문은 없다.
        "ocr_value_snapshot": medication,
    }


async def _delete_image_quietly(key: str) -> None:
    try:
        await run_in_threadpool(delete_image, key)
    except Exception:
        logger.exception("처방 사진 삭제 실패 (key=%s)", key)


async def register_prescription(
    *,
    child: Child,
    source_type: SourceType,
    image: bytes,
    content_type: str,
    diagnosis_user_input: str | None,
    symptom_notes: str | None,
) -> tuple[Prescription, list[Medication], dict[str, Any]]:
    """저장한 처방, 약 목록, 신뢰도 판정을 돌려준다. 실패하면 처방 행을 만들지 않고 사진도 지운다."""
    validate_image(image, content_type)
    image_key = await run_in_threadpool(upload_image, child_id=child.id, data=image, content_type=content_type)

    try:
        result = await run_in_threadpool(run_ocr, image, source_type.value)
    except OcrInputError as error:
        await _delete_image_quietly(image_key)
        raise PrescriptionImageError(IMAGE_TYPE_MESSAGE) from error
    except OcrError as error:
        await _delete_image_quietly(image_key)
        logger.warning("OCR 실패 (child_id=%s): %s", child.id, type(error).__name__)
        raise OcrFailedError(OCR_FAILED_MESSAGE) from error

    judgement = judge_ocr_confidence(result)
    if judgement["level"] == RETAKE:
        await _delete_image_quietly(image_key)
        raise OcrLowConfidenceError(judgement)

    try:
        async with in_transaction():
            prescription = await Prescription.create(
                child=child,
                source_type=source_type,
                status=PrescriptionStatus.OCR_DONE,
                prescription_date=_parse_date(result.get("prescription_date")),
                hospital_name=_clip(result.get("hospital_name"), 100),
                diagnosis_extracted=_clip(result.get("diagnosis_extracted"), 50),
                diagnosis_user_input=_clip((diagnosis_user_input or "").strip(), 200),
                symptom_notes=(symptom_notes or "").strip() or None,
                image_storage_key=image_key,
            )
            medications = [
                await Medication.create(prescription=prescription, **medication_fields_from_ocr(medication))
                for medication in result["medications"]
            ]
    except Exception:
        await _delete_image_quietly(image_key)
        raise
    return prescription, medications, judgement


def image_url_of(prescription: Prescription) -> str | None:
    if not prescription.image_storage_key:
        return None
    return get_presigned_url(prescription.image_storage_key)


def low_confidence_of(medication: Medication) -> bool:
    return is_low_confidence(None if medication.confidence is None else float(medication.confidence))
