"""복약 알림 시간·켜기/끄기 저장 (웹 푸시 P1~P6 자리, ERD 2.7 MEDICATION_ALARM 재사용).

화면은 처방(가이드)마다 먹는 때(아침·점심·저녁)별 알림 시각과 알림 켜기/끄기를 정한다.
DB는 약마다 알림 행을 둔다(MEDICATION_ALARM). 그래서 아래 규칙으로 둘을 잇는다.

- 알림 행은 확정된 처방(CONFIRMED·GUIDE_DONE)을 처음 조회할 때 만든다. 처방 확정 API(7번)는 고치지 않는다.
- 약의 먹는 때는 화면(frontend/src/state/records.jsx scheduleFromMeds)과 같은 규칙으로 정한다.
  하루 1~4번 → 아침 / 아침·저녁 / 아침·점심·저녁 / +자기 전, 하루 1번이면서 용법에 '자기 전·취침'이 있으면 자기 전.
  필요시 약, 하루 횟수나 기간이 없는 약은 알림을 만들지 않는다 (명세 7절 자동 생성 기준).
- 자기 전은 화면에서 알림을 보내지 않는 때라(NO_ALARM_SLOTS) 알림 행을 만들지 않는다.
- MEDICATION_ALARM에는 먹는 때 컬럼이 없다. 약 하나의 알림 행은 먹는 때 순서(아침→점심→저녁)대로 만들고,
  만든 순서(alarm_id)로 먹는 때를 다시 읽는다. 시각을 바꿀 때도 같은 순서로 다시 만든다.
- 시작일은 화면의 복용 시작일과 같다(처방일, 없으면 올린 날 KST). 종료일 = 시작일 + total_days - 1 (종료일 포함).
"""

import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException, status
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.core import config
from app.dtos.medication_alarms import PrescriptionAlarmResponse, PrescriptionAlarmUpdateRequest
from app.models.children import Child
from app.models.medication_alarms import MedicationAlarm
from app.models.medications import Medication
from app.models.prescriptions import Prescription, PrescriptionStatus

SLOTS_BY_COUNT: dict[int, tuple[str, ...]] = {
    1: ("아침",),
    2: ("아침", "저녁"),
    3: ("아침", "점심", "저녁"),
    4: ("아침", "점심", "저녁", "자기 전"),
}
NO_ALARM_SLOTS = frozenset({"자기 전"})
DEFAULT_TIMES: dict[str, time] = {"아침": time(8, 0), "점심": time(12, 30), "저녁": time(18, 30)}
ALARM_STATUSES = (PrescriptionStatus.CONFIRMED, PrescriptionStatus.GUIDE_DONE)
# 화면의 isAsNeeded와 같은 말: 열날 때·필요할 때·아플 때·통증
AS_NEEDED_WORDS = re.compile(r"열|필요|아플|통증")
BEDTIME_WORDS = re.compile(r"자기\s*전|취침")
TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")

NOT_CONFIRMED_MESSAGE = "처방을 먼저 확정해 주세요."
UNKNOWN_SLOT_MESSAGE = "알림을 보낼 수 없는 먹는 때예요: {slot}"
TIME_FORMAT_MESSAGE = "알림 시각은 08:30처럼 입력해 주세요."
DUPLICATE_TIME_MESSAGE = "먹는 때마다 다른 시각을 골라 주세요."


def scheduled_slots(medication: Medication) -> list[str]:
    """이 약을 먹이는 때(복약 달력·복약 체크 기준). 정해진 때가 없는 약(필요시, 횟수·기간 없음)은 []."""
    usage = medication.usage or ""
    if medication.as_needed or not medication.daily_count or not medication.total_days or AS_NEEDED_WORDS.search(usage):
        return []
    count = min(int(medication.daily_count), 4)
    return list(("자기 전",) if count == 1 and BEDTIME_WORDS.search(usage) else SLOTS_BY_COUNT[count])


def medication_slots(medication: Medication) -> list[str]:
    """이 약의 알림을 보내는 먹는 때. 알림 대상이 아니면 []."""
    return [slot for slot in scheduled_slots(medication) if slot not in NO_ALARM_SLOTS]


def course_start(prescription: Prescription) -> date:
    """복용 시작일 — 처방일(약봉투는 조제일), 없으면 올린 날(KST). 화면의 건강기록 날짜와 같다."""
    if prescription.prescription_date:
        return prescription.prescription_date
    created: datetime = prescription.created_at
    return created.astimezone(config.TIMEZONE).date()


def _as_time(value: object) -> time:
    # MySQL TIME을 timedelta로 돌려주는 드라이버도 있어서 맞춰 둔다.
    if isinstance(value, timedelta):
        seconds = int(value.total_seconds())
        return time(seconds // 3600, seconds % 3600 // 60)
    assert isinstance(value, time)
    return value


def _hhmm(value: time) -> str:
    return f"{value.hour:02d}:{value.minute:02d}"


def _current_settings(
    medications: list[Medication], alarms_of: dict[int, list[MedicationAlarm]]
) -> tuple[dict[str, time], bool]:
    """처방 단위 설정(먹는 때별 시각·켜짐)을 이미 있는 알림에서 읽는다. 다시 확정해서 약이 바뀌어도 이어 쓴다."""
    times: dict[str, time] = {}
    existing = [alarm for alarms in alarms_of.values() for alarm in alarms]
    for medication in medications:
        slots, alarms = medication_slots(medication), alarms_of[medication.id]
        if len(slots) == len(alarms):
            for slot, alarm in zip(slots, alarms, strict=True):
                times.setdefault(slot, _as_time(alarm.notify_time))
    return times, all(alarm.is_enabled for alarm in existing) if existing else True


async def _fit_alarms(
    medication: Medication,
    alarms: list[MedicationAlarm],
    slots: list[str],
    start: date,
    times: dict[str, time],
    enabled: bool,
) -> list[MedicationAlarm]:
    """약 하나의 알림 행을 먹는 때·기간에 맞춘다. 개수가 다르면(처음 조회, 약이 바뀜) 먹는 때 순서대로 다시 만든다."""
    end = start + timedelta(days=int(medication.total_days or 1) - 1)
    if len(slots) != len(alarms):
        await MedicationAlarm.filter(medication_id=medication.id).delete()
        return [
            await MedicationAlarm.create(
                medication=medication,
                notify_time=times.get(slot, DEFAULT_TIMES[slot]),
                start_date=start,
                end_date=end,
                is_enabled=enabled,
            )
            for slot in slots
        ]
    for alarm in alarms:
        if (alarm.start_date, alarm.end_date) != (start, end):
            alarm.start_date, alarm.end_date = start, end
            await alarm.save(update_fields=["start_date", "end_date"])
    return alarms


async def _sync_alarms(prescription: Prescription) -> dict[str, list[MedicationAlarm]]:
    """알림 행을 지금 약 목록에 맞추고 먹는 때별로 묶어 돌려준다. 확정 전이면 {}."""
    if prescription.status not in ALARM_STATUSES:
        return {}
    medications = await Medication.filter(prescription_id=prescription.id).order_by("id")
    alarms_of: dict[int, list[MedicationAlarm]] = defaultdict(list)
    for alarm in await MedicationAlarm.filter(medication__prescription_id=prescription.id).order_by("id"):
        alarms_of[alarm.medication_id].append(alarm)  # type: ignore[attr-defined]
    times, enabled = _current_settings(medications, alarms_of)
    start = course_start(prescription)
    by_slot: dict[str, list[MedicationAlarm]] = defaultdict(list)
    for medication in medications:
        slots, alarms = medication_slots(medication), alarms_of[medication.id]
        if not slots and not alarms:
            continue
        fitted = await _fit_alarms(medication, alarms, slots, start, times, enabled)
        for slot, alarm in zip(slots, fitted, strict=True):
            by_slot[slot].append(alarm)
    return by_slot


async def _synced(prescription: Prescription) -> dict[str, list[MedicationAlarm]]:
    """같은 처방을 동시에 처음 조회하면 같은 알림을 두 번 만들 수 있다. 그때는 먼저 만든 쪽을 다시 읽는다."""
    for attempt in range(2):
        try:
            async with in_transaction():
                return await _sync_alarms(prescription)
        except IntegrityError:
            if attempt:
                raise
    return {}


def _to_response(prescription: Prescription, by_slot: dict[str, list[MedicationAlarm]]) -> PrescriptionAlarmResponse:
    alarms = [alarm for slot_alarms in by_slot.values() for alarm in slot_alarms]
    order = list(DEFAULT_TIMES)
    return PrescriptionAlarmResponse(
        prescription_id=prescription.id,
        enabled=all(alarm.is_enabled for alarm in alarms) if alarms else True,
        times={slot: _hhmm(_as_time(by_slot[slot][0].notify_time)) for slot in sorted(by_slot, key=order.index)},
        start_date=min((alarm.start_date for alarm in alarms), default=None),
        end_date=max((alarm.end_date for alarm in alarms), default=None),
    )


async def list_child_alarms(child: Child) -> list[PrescriptionAlarmResponse]:
    """아이의 확정된 처방마다 알림 설정. 처음 조회하는 처방은 기본 시각으로 알림 행을 만든다."""
    prescriptions = await Prescription.filter(child_id=child.id, status__in=list(ALARM_STATUSES)).order_by("id")
    return [_to_response(p, await _synced(p)) for p in prescriptions]


def _parse_time(text: str) -> time:
    matched = TIME_PATTERN.match(text.strip())
    if not matched:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=TIME_FORMAT_MESSAGE)
    return time(int(matched.group(1)), int(matched.group(2)))


def _merged_times(by_slot: dict[str, list[MedicationAlarm]], requested: dict[str, str]) -> dict[str, time]:
    """요청한 시각을 지금 시각 위에 덮는다. 알림이 없는 먹는 때, 잘못된 형식, 같은 시각 두 개는 422."""
    new_times = {}
    for slot, text in requested.items():
        if slot not in by_slot:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=UNKNOWN_SLOT_MESSAGE.format(slot=slot)
            )
        new_times[slot] = _parse_time(text)
    merged = {slot: new_times.get(slot, _as_time(alarms[0].notify_time)) for slot, alarms in by_slot.items()}
    if len(set(merged.values())) != len(merged):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=DUPLICATE_TIME_MESSAGE)
    return merged


async def _rewrite_times(by_slot: dict[str, list[MedicationAlarm]], merged: dict[str, time]) -> None:
    """(약, 시각, 시작일)이 겹치면 안 돼서(unique), 시각을 맞바꿀 때를 생각해 약마다 먹는 때 순서대로 다시 만든다."""
    slots_of: dict[int, list[str]] = defaultdict(list)
    template: dict[int, MedicationAlarm] = {}
    for slot, alarms in by_slot.items():
        for alarm in alarms:
            slots_of[alarm.medication_id].append(slot)  # type: ignore[attr-defined]
            template[alarm.medication_id] = alarm  # type: ignore[attr-defined]
    order = list(DEFAULT_TIMES)
    for medication_id, slots in slots_of.items():
        base = template[medication_id]
        await MedicationAlarm.filter(medication_id=medication_id).delete()
        for slot in sorted(slots, key=order.index):
            await MedicationAlarm.create(
                medication_id=medication_id,
                notify_time=merged[slot],
                start_date=base.start_date,
                end_date=base.end_date,
                is_enabled=base.is_enabled,
            )


async def update_prescription_alarms(
    prescription: Prescription, data: PrescriptionAlarmUpdateRequest
) -> PrescriptionAlarmResponse:
    """알림 켜기/끄기와 먹는 때별 시각을 바꾼다. 보낸 항목만 바꾸고, 처방의 모든 약 알림에 같이 적용한다."""
    if prescription.status not in ALARM_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NOT_CONFIRMED_MESSAGE)
    async with in_transaction():
        by_slot = await _sync_alarms(prescription)
        if data.times:
            await _rewrite_times(by_slot, _merged_times(by_slot, data.times))
        if data.enabled is not None:
            await MedicationAlarm.filter(medication__prescription_id=prescription.id).update(is_enabled=data.enabled)
        by_slot = await _sync_alarms(prescription)
    return _to_response(prescription, by_slot)
