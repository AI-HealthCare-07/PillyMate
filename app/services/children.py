"""3. 자녀 등록, 4. 내 자녀 목록 (명세 4절)."""

from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from tortoise.timezone import now

from app.core import config
from app.core.validators.guardian_validators import international_age
from app.dtos.children import ChildCreateRequest, ChildResponse
from app.models.children import Child
from app.models.guardians import Guardian

CHILD_AGE_LIMIT = 18  # 만 18세 미만만 등록 (11/24 결정)
WEIGHT_MIN_KG = 0.5
WEIGHT_MAX_KG = 150.0

# 명세서 8절 에러 메시지 문구
MISSING_NAME_MESSAGE = "필수 항목을 입력해 주세요: name"
CONSENT_REQUIRED_MESSAGE = "보호자 동의 3가지에 모두 동의해 주세요."
CHILD_TOO_OLD_MESSAGE = "만 18세 미만 자녀만 등록할 수 있어요."
FUTURE_BIRTH_MESSAGE = "생년월일을 다시 확인해 주세요."
WEIGHT_RANGE_MESSAGE = "체중은 0.5~150kg 사이로 입력해 주세요."


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)


def _blank_to_none(text: str | None) -> str | None:
    return (text or "").strip() or None


def validate_new_child(data: ChildCreateRequest) -> None:
    if not data.name.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=MISSING_NAME_MESSAGE)
    if not data.consent_agreed:
        raise _unprocessable(CONSENT_REQUIRED_MESSAGE)
    today = datetime.now(tz=config.TIMEZONE).date()
    if data.birth_date > today:
        raise _unprocessable(FUTURE_BIRTH_MESSAGE)
    if international_age(data.birth_date, today) >= CHILD_AGE_LIMIT:
        raise _unprocessable(CHILD_TOO_OLD_MESSAGE)
    if data.weight_kg is not None and not WEIGHT_MIN_KG <= data.weight_kg <= WEIGHT_MAX_KG:
        raise _unprocessable(WEIGHT_RANGE_MESSAGE)


async def create_child(guardian: Guardian, data: ChildCreateRequest) -> Child:
    validate_new_child(data)
    return await Child.create(
        guardian=guardian,
        name=data.name.strip(),
        birth_date=data.birth_date,
        weight_kg=None if data.weight_kg is None else Decimal(str(data.weight_kg)).quantize(Decimal("0.01")),
        allergies=_blank_to_none(data.allergies),
        notes=_blank_to_none(data.notes),
        # 화면에서 동의 3항목을 모두 체크했을 때만 true가 온다. 서버는 받은 시각을 동의 시각으로 남긴다.
        consent_agreed_at=now(),
    )


async def list_children(guardian: Guardian) -> list[Child]:
    """등록 순서대로."""
    return await Child.filter(guardian_id=guardian.id).order_by("id")


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
