from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.dependencies.ownership import MyChild, MyPrescription
from app.dtos.medication_doses import DoseCheckRequest, DoseLogResponse
from app.services.medication_doses import list_child_doses, save_doses

medication_dose_router = APIRouter(tags=["doses"])


@medication_dose_router.get(
    "/children/{child_id}/doses", response_model=list[DoseLogResponse], status_code=status.HTTP_200_OK
)
async def get_child_doses(
    child: MyChild,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> list[DoseLogResponse]:
    """아이의 복약 체크 기록 (from·to는 선택, 양 끝 포함). 기록이 없는 먹는 때는 목록에 없다. 남의 아이는 404."""
    return await list_child_doses(child, date_from, date_to)


@medication_dose_router.put(
    "/prescriptions/{prescription_id}/doses", response_model=list[DoseLogResponse], status_code=status.HTTP_200_OK
)
async def put_prescription_doses(prescription: MyPrescription, data: DoseCheckRequest) -> list[DoseLogResponse]:
    """그날 먹인 약 체크·취소 저장(덮어쓰기). 확정 전 409, 잘못된 약·때·날짜 422, 남의 처방 404."""
    return await save_doses(prescription, data)
