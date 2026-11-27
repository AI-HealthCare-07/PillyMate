from fastapi import APIRouter, status

from app.dependencies.ownership import MyChild, MyPrescription
from app.dtos.medication_alarms import PrescriptionAlarmResponse, PrescriptionAlarmUpdateRequest
from app.services.medication_alarms import list_child_alarms, update_prescription_alarms

medication_alarm_router = APIRouter(tags=["alarms"])


@medication_alarm_router.get(
    "/children/{child_id}/alarms", response_model=list[PrescriptionAlarmResponse], status_code=status.HTTP_200_OK
)
async def get_child_alarms(child: MyChild) -> list[PrescriptionAlarmResponse]:
    """아이의 확정된 처방마다 복약 알림 설정(켜짐, 먹는 때별 시각, 기간). 남의 아이는 404."""
    return await list_child_alarms(child)


@medication_alarm_router.patch(
    "/prescriptions/{prescription_id}/alarms", response_model=PrescriptionAlarmResponse, status_code=status.HTTP_200_OK
)
async def edit_prescription_alarms(
    prescription: MyPrescription, data: PrescriptionAlarmUpdateRequest
) -> PrescriptionAlarmResponse:
    """처방의 복약 알림 켜기/끄기와 먹는 때별 시각 저장. 확정 전이면 409, 남의 처방은 404."""
    return await update_prescription_alarms(prescription, data)
