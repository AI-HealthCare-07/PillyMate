from datetime import date, datetime

from pydantic import BaseModel, field_serializer

from app.core import config


class MeResponse(BaseModel):
    guardian_id: int
    email: str
    name: str
    birth_date: date
    created_at: datetime

    @field_serializer("created_at")
    def _serialize_kst(self, value: datetime) -> str:
        # 명세서 1절: 일시는 ISO 8601 + KST (2026-11-20T10:30:00+09:00)
        if value.tzinfo is None:
            value = value.replace(tzinfo=config.TIMEZONE)
        return value.astimezone(config.TIMEZONE).isoformat(timespec="seconds")
