from datetime import date

from pydantic import BaseModel


class DoseLogResponse(BaseModel):
    """복약 체크 기록 하나. 기록이 없는 먹는 때는 목록에 없다('기록 없음')."""

    prescription_id: int
    medication_id: int
    medication_name: str
    dose_date: date
    slot: str
    is_taken: bool


class DoseCheckItem(BaseModel):
    medication_id: int
    slot: str
    is_taken: bool


class DoseCheckRequest(BaseModel):
    """그날 먹인 약 체크·취소. 같은 약·날·먹는 때를 다시 보내면 덮어쓴다."""

    dose_date: date
    items: list[DoseCheckItem]
