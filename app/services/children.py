"""3. 자녀 등록, 4. 내 자녀 목록 (명세 4절), 자녀 수정·삭제 (명세 9절)."""

import logging
from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from starlette.concurrency import run_in_threadpool
from tortoise.timezone import now

from app.core import config
from app.core.storage import delete_image
from app.core.validators.guardian_validators import international_age
from app.dtos.children import ChildCreateRequest, ChildResponse, ChildUpdateRequest
from app.models.children import Child
from app.models.guardians import Guardian
from app.models.prescriptions import Prescription

logger = logging.getLogger(__name__)

CHILD_AGE_LIMIT = 18  # 만 18세 미만만 등록 (11/24 결정)
WEIGHT_MIN_KG = 0.5
WEIGHT_MAX_KG = 150.0

# 명세서 8절 에러 메시지 문구
MISSING_NAME_MESSAGE = "필수 항목을 입력해 주세요: name"
MISSING_BIRTH_DATE_MESSAGE = "필수 항목을 입력해 주세요: birth_date"
CONSENT_REQUIRED_MESSAGE = "보호자 동의 3가지에 모두 동의해 주세요."
CHILD_TOO_OLD_MESSAGE = "만 18세 미만 자녀만 등록할 수 있어요."
FUTURE_BIRTH_MESSAGE = "생년월일을 다시 확인해 주세요."
WEIGHT_RANGE_MESSAGE = "체중은 0.5~150kg 사이로 입력해 주세요."


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)


def _blank_to_none(text: str | None) -> str | None:
    return (text or "").strip() or None


def _validate_birth_date(birth_date: date) -> None:
    today = datetime.now(tz=config.TIMEZONE).date()
    if birth_date > today:
        raise _unprocessable(FUTURE_BIRTH_MESSAGE)
    if international_age(birth_date, today) >= CHILD_AGE_LIMIT:
        raise _unprocessable(CHILD_TOO_OLD_MESSAGE)


def _validate_weight(weight_kg: float | None) -> None:
    if weight_kg is not None and not WEIGHT_MIN_KG <= weight_kg <= WEIGHT_MAX_KG:
        raise _unprocessable(WEIGHT_RANGE_MESSAGE)


def _to_weight(weight_kg: float | None) -> Decimal | None:
    return None if weight_kg is None else Decimal(str(weight_kg)).quantize(Decimal("0.01"))


def validate_new_child(data: ChildCreateRequest) -> None:
    if not data.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MISSING_NAME_MESSAGE)
    if not data.consent_agreed:
        raise _unprocessable(CONSENT_REQUIRED_MESSAGE)
    _validate_birth_date(data.birth_date)
    _validate_weight(data.weight_kg)


async def create_child(guardian: Guardian, data: ChildCreateRequest) -> Child:
    validate_new_child(data)
    return await Child.create(
        guardian=guardian,
        name=data.name.strip(),
        birth_date=data.birth_date,
        weight_kg=_to_weight(data.weight_kg),
        allergies=_blank_to_none(data.allergies),
        notes=_blank_to_none(data.notes),
        # 화면에서 동의 3항목을 모두 체크했을 때만 true가 온다. 서버는 받은 시각을 동의 시각으로 남긴다.
        consent_agreed_at=now(),
    )


async def list_children(guardian: Guardian) -> list[Child]:
    """등록 순서대로."""
    return await Child.filter(guardian_id=guardian.id).order_by("id")


async def update_child(child: Child, data: ChildUpdateRequest) -> Child:
    """보낸 항목만 바꾼다. 검사 규칙과 문구는 등록(3번)과 같다. child는 소유권 확인을 마친 내 자녀."""
    sent = data.model_fields_set
    if "name" in sent:
        if not (data.name or "").strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MISSING_NAME_MESSAGE)
        child.name = data.name.strip()  # type: ignore[union-attr]
    if "birth_date" in sent:
        if data.birth_date is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MISSING_BIRTH_DATE_MESSAGE)
        _validate_birth_date(data.birth_date)
        child.birth_date = data.birth_date
    if "weight_kg" in sent:
        _validate_weight(data.weight_kg)
        child.weight_kg = _to_weight(data.weight_kg)  # type: ignore[assignment]  # null 허용 컬럼
    if "allergies" in sent:
        child.allergies = _blank_to_none(data.allergies)  # type: ignore[assignment]  # null 허용 컬럼
    if "notes" in sent:
        child.notes = _blank_to_none(data.notes)  # type: ignore[assignment]  # null 허용 컬럼
    await child.save()
    return child


async def delete_child(child: Child) -> None:
    """자녀를 영구 삭제한다 (ERD 4절 삭제 정책).

    처방전·약품·가이드·복약 알림은 DB의 ON DELETE CASCADE로 함께 지워진다.
    저장소(S3·로컬)의 원본 사진은 CASCADE로 지워지지 않으므로, 행을 지운 뒤 남아 있던 키를 직접 지운다.
    사진 삭제가 실패해도 자녀 삭제는 되돌리지 않는다. 남은 사진은 S3 Lifecycle(7일)이 지운다.
    """
    image_keys: list[str] = await Prescription.filter(child_id=child.id, image_storage_key__isnull=False).values_list(
        "image_storage_key", flat=True
    )  # type: ignore[assignment]
    child_id = child.id
    await child.delete()
    for key in image_keys:
        try:
            await run_in_threadpool(delete_image, key)
        except Exception as error:  # noqa: BLE001 — 사진 하나 실패로 응답을 실패시키지 않는다
            logger.warning("자녀 삭제 후 원본 사진 삭제 실패 (child_id=%s): %s", child_id, type(error).__name__)


def to_child_response(child: Child) -> ChildResponse:
    return ChildResponse(
        child_id=child.id,
        name=child.name,
        birth_date=child.birth_date,
        weight_kg=None if child.weight_kg is None else float(child.weight_kg),
        allergies=child.allergies,
        notes=child.notes,
        created_at=child.created_at,
    )
