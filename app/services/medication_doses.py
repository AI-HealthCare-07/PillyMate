"""복약 체크(먹였어요) 저장·조회 — MEDICATION_DOSE_LOG.

행이 없으면 '기록 없음', is_taken=false면 '안 먹임', true면 '먹임'이다.
먹는 때와 복용 기간은 알림과 같은 규칙(medication_alarms.scheduled_slots, course_start)으로 확인한다.
자기 전처럼 알림을 보내지 않는 때도 체크는 저장한다.
"""

from datetime import date, datetime, timedelta

from fastapi import HTTPException, status
from tortoise.exceptions import IntegrityError
from tortoise.transactions import in_transaction

from app.core import config
from app.dtos.medication_doses import DoseCheckRequest, DoseLogResponse
from app.models.children import Child
from app.models.medication_dose_logs import MedicationDoseLog
from app.models.medications import Medication
from app.models.prescriptions import Prescription
from app.services.medication_alarms import ALARM_STATUSES, course_start, scheduled_slots

NOT_CONFIRMED_MESSAGE = "처방을 먼저 확정해 주세요."
EMPTY_ITEMS_MESSAGE = "체크할 약을 1개 이상 보내 주세요."
UNKNOWN_MEDICATION_MESSAGE = "이 처방에 없는 약이 포함돼 있어요."
WRONG_SLOT_MESSAGE = "이 약을 먹이는 때가 아니에요: {name} {slot}"
OUT_OF_COURSE_MESSAGE = "복용 기간이 아닌 날이에요: {name}"
FUTURE_DATE_MESSAGE = "앞으로 먹일 약은 미리 체크할 수 없어요."


def _unprocessable(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)


def _to_response(log: MedicationDoseLog, medication: Medication) -> DoseLogResponse:
    return DoseLogResponse(
        prescription_id=medication.prescription_id,  # type: ignore[attr-defined]
        medication_id=medication.id,
        medication_name=medication.name,
        dose_date=log.dose_date,
        slot=log.slot,
        is_taken=log.is_taken,
    )


async def list_child_doses(child: Child, date_from: date | None, date_to: date | None) -> list[DoseLogResponse]:
    """아이의 복약 체크 기록. 날짜 범위를 주면 그 안(양 끝 포함)만, 날짜·먹는 때 순서."""
    query = MedicationDoseLog.filter(medication__prescription__child_id=child.id)
    if date_from:
        query = query.filter(dose_date__gte=date_from)
    if date_to:
        query = query.filter(dose_date__lte=date_to)
    logs = await query.order_by("dose_date", "id").prefetch_related("medication")
    return [_to_response(log, log.medication) for log in logs]


def _validate_item(medication: Medication | None, slot: str, dose_date: date, start: date) -> Medication:
    if medication is None:
        raise _unprocessable(UNKNOWN_MEDICATION_MESSAGE)
    if slot not in scheduled_slots(medication):
        raise _unprocessable(WRONG_SLOT_MESSAGE.format(name=medication.name, slot=slot))
    end = start + timedelta(days=int(medication.total_days or 0) - 1)
    if not start <= dose_date <= end:
        raise _unprocessable(OUT_OF_COURSE_MESSAGE.format(name=medication.name))
    return medication


async def _upsert(medication: Medication, dose_date: date, slot: str, is_taken: bool) -> MedicationDoseLog:
    log, _ = await MedicationDoseLog.update_or_create(
        defaults={"is_taken": is_taken}, medication_id=medication.id, dose_date=dose_date, slot=slot
    )
    return log


async def save_doses(prescription: Prescription, data: DoseCheckRequest) -> list[DoseLogResponse]:
    """그날 먹인 약을 체크하거나 취소한다. 확정 전 처방은 409, 잘못된 약·때·날짜는 422(아무것도 저장하지 않음)."""
    if prescription.status not in ALARM_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=NOT_CONFIRMED_MESSAGE)
    if not data.items:
        raise _unprocessable(EMPTY_ITEMS_MESSAGE)
    if data.dose_date > datetime.now(tz=config.TIMEZONE).date():
        raise _unprocessable(FUTURE_DATE_MESSAGE)
    medications = {m.id: m for m in await Medication.filter(prescription_id=prescription.id)}
    start = course_start(prescription)
    checked = [
        (_validate_item(medications.get(item.medication_id), item.slot, data.dose_date, start), item)
        for item in data.items
    ]
    for attempt in range(2):
        try:
            async with in_transaction():
                saved = [
                    (await _upsert(medication, data.dose_date, item.slot, item.is_taken), medication)
                    for medication, item in checked
                ]
            return [_to_response(log, medication) for log, medication in saved]
        except IntegrityError:
            # 같은 체크가 동시에 두 번 오면 먼저 들어간 행을 덮어쓴다.
            if attempt:
                raise
    return []
