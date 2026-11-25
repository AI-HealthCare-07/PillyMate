from fastapi import APIRouter, status

from app.dependencies.ownership import MyChild, MyPrescription
from app.dtos.prescription_query import PrescriptionDetailResponse, PrescriptionSummaryResponse
from app.services.prescription_query import get_prescription_detail, list_child_prescriptions

prescription_query_router = APIRouter(tags=["prescriptions"])


@prescription_query_router.get(
    "/prescriptions/{prescription_id}",
    response_model=PrescriptionDetailResponse,
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "없거나 내 처방전이 아님"}},
)
async def get_prescription(prescription: MyPrescription) -> PrescriptionDetailResponse:
    """6. 처방전 상세 — OCR로 읽은 약 목록과 원본 사진 주소(7일이 지나면 null)."""
    return await get_prescription_detail(prescription)


@prescription_query_router.get(
    "/children/{child_id}/prescriptions",
    response_model=list[PrescriptionSummaryResponse],
    status_code=status.HTTP_200_OK,
    responses={404: {"description": "내 자녀가 아님"}},
)
async def get_child_prescriptions(child: MyChild) -> list[PrescriptionSummaryResponse]:
    """10. 자녀별 처방전 목록 — 최신 등록순. 없으면 []."""
    return await list_child_prescriptions(child)
