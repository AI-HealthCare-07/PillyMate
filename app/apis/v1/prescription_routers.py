from typing import Annotated

from fastapi import APIRouter, Depends, Path, status
from fastapi.responses import JSONResponse as Response

from app.dependencies.security import CurrentGuardian
from app.dtos.prescriptions import GuideResponse, PrescriptionConfirmRequest, PrescriptionDetailResponse
from app.services.prescriptions import PrescriptionService

prescription_router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])

PrescriptionId = Annotated[int, Path(ge=1, description="처방 id")]


@prescription_router.put(
    "/{prescription_id}/confirm", response_model=PrescriptionDetailResponse, status_code=status.HTTP_200_OK
)
async def confirm_prescription(
    prescription_id: PrescriptionId,
    request: PrescriptionConfirmRequest,
    guardian: CurrentGuardian,
    service: Annotated[PrescriptionService, Depends(PrescriptionService)],
) -> Response:
    """S-04 확인 화면에서 보호자가 고친 진단명·약 목록으로 처방을 확정한다."""
    detail = await service.confirm(prescription_id, guardian.id, request)
    return Response(detail.model_dump(mode="json"), status_code=status.HTTP_200_OK)


@prescription_router.post(
    "/{prescription_id}/guide",
    response_model=GuideResponse,
    status_code=status.HTTP_201_CREATED,
    responses={200: {"description": "이미 만든 가이드가 있어 그대로 돌려줌"}},
)
async def create_guide(
    prescription_id: PrescriptionId,
    guardian: CurrentGuardian,
    service: Annotated[PrescriptionService, Depends(PrescriptionService)],
) -> Response:
    """확정된 처방으로 가이드를 만든다. 약 20초 걸리고, 이미 있으면 새로 만들지 않는다."""
    guide, created = await service.create_guide(prescription_id, guardian.id)
    return Response(
        guide.model_dump(mode="json"), status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )


@prescription_router.get("/{prescription_id}/guide", response_model=GuideResponse, status_code=status.HTTP_200_OK)
async def get_guide(
    prescription_id: PrescriptionId,
    guardian: CurrentGuardian,
    service: Annotated[PrescriptionService, Depends(PrescriptionService)],
) -> Response:
    guide = await service.get_guide(prescription_id, guardian.id)
    return Response(guide.model_dump(mode="json"), status_code=status.HTTP_200_OK)
