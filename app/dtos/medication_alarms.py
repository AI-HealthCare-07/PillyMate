from datetime import date

from pydantic import BaseModel


class PrescriptionAlarmResponse(BaseModel):
    """처방 하나의 복약 알림 설정.

    times는 알림을 보내는 먹는 때만 담는다 (예: {"아침": "08:00", "저녁": "18:30"}). 자기 전·필요시 약은 없다.
    start_date·end_date는 알림을 보내는 첫날·마지막 날(포함)이다. 알림 대상 약이 없으면 times는 {}이고 날짜는 null.
    """

    prescription_id: int
    enabled: bool
    times: dict[str, str]
    start_date: date | None
    end_date: date | None


class PrescriptionAlarmUpdateRequest(BaseModel):
    """보낸 항목만 바꾼다. times에는 바꿀 먹는 때만 넣어도 된다 (예: {"점심": "13:10"})."""

    enabled: bool | None = None
    times: dict[str, str] | None = None
