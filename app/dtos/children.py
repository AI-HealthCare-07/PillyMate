from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_serializer

from app.core import config


class ChildCreateRequest(BaseModel):
    """3. 자녀 등록. 나이·동의·체중 범위는 명세 8절 문구로 답하려고 서비스에서 검사한다."""

    name: Annotated[str, Field(max_length=50)]
    birth_date: date
    consent_agreed: bool
    weight_kg: float | None = None
    allergies: str | None = None
    notes: str | None = None


class ChildUpdateRequest(BaseModel):
    """자녀 정보 수정 (명세 9절 PATCH /children/{child_id}).

    보낸 항목만 바꾼다. weight_kg·allergies·notes는 null(또는 빈 문자열)을 보내면 비운다.
    name·birth_date는 비울 수 없다. 동의 시각(consent_agreed_at)은 등록 때 값을 그대로 둔다.
    """

    name: Annotated[str | None, Field(max_length=50)] = None
    birth_date: date | None = None
    weight_kg: float | None = None
    allergies: str | None = None
    notes: str | None = None


class ChildResponse(BaseModel):
    """3번 등록 응답이자 4번 목록의 한 줄.

    명세 4번 목록은 child_id·name·birth_date·weight_kg만 정했지만, 처방 올리기 화면이 알레르기를 보여 주므로
    3번 응답과 같은 값을 모두 돌려준다.
    """

    child_id: int
    name: str
    birth_date: date
    weight_kg: float | None
    allergies: str | None
    notes: str | None
    created_at: datetime

    @field_serializer("created_at")
    def _serialize_kst(self, value: datetime) -> str:
        # 명세서 1절: 일시는 ISO 8601 + KST (2026-11-20T10:30:00+09:00)
        if value.tzinfo is None:
            value = value.replace(tzinfo=config.TIMEZONE)
        return value.astimezone(config.TIMEZONE).isoformat(timespec="seconds")
