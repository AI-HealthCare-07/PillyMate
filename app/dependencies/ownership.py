"""소유권 확인 (명세서 1절 "권한": 내 자녀·내 처방전만 조회·수정, 남의 데이터는 404).

BE-2와 합의할 모델 계약 (BE-2 모델이 머지되기 전에는 호출하지 않는다):
- app.models.children.Child: 보호자 FK 필드 이름 `guardian` (DB 컬럼 guardian_id)
- app.models.prescriptions.Prescription: 자녀 FK 필드 이름 `child` (DB 컬럼 child_id)
모델 경로나 필드 이름이 다르게 정해지면 아래 import와 filter 조건만 고치면 된다.

사용 예 (BE-2):

    # 경로에 {child_id}가 있는 API
    @router.get("/children/{child_id}/prescriptions")
    async def list_prescriptions(child: MyChild): ...

    # 경로에 {prescription_id}가 있는 API
    @router.get("/prescriptions/{prescription_id}")
    async def get_prescription(prescription: MyPrescription): ...

    # child_id가 form/body로 오는 API (5번 처방전 등록)
    child = await get_my_child_or_404(child_id, guardian)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, HTTPException, status

from app.dependencies.security import CurrentGuardian
from app.models.guardians import Guardian

if TYPE_CHECKING:
    from app.models.children import Child  # type: ignore[import-not-found]
    from app.models.prescriptions import Prescription  # type: ignore[import-not-found]

CHILD_NOT_FOUND_MESSAGE = "자녀 정보를 찾을 수 없어요."
PRESCRIPTION_NOT_FOUND_MESSAGE = "처방전을 찾을 수 없어요."


async def get_my_child_or_404(child_id: int, guardian: Guardian) -> Child:
    """로그인한 보호자의 자녀면 돌려주고, 없거나 남의 자녀면 404."""
    from app.models.children import Child  # BE-2 모델 머지 후 동작

    child = await Child.get_or_none(id=child_id, guardian_id=guardian.id)
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=CHILD_NOT_FOUND_MESSAGE)
    return child


async def get_my_prescription_or_404(prescription_id: int, guardian: Guardian) -> Prescription:
    """로그인한 보호자 자녀의 처방전이면 돌려주고, 없거나 남의 처방전이면 404."""
    from app.models.prescriptions import Prescription  # BE-2 모델 머지 후 동작

    prescription = await Prescription.get_or_none(id=prescription_id, child__guardian_id=guardian.id)
    if prescription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PRESCRIPTION_NOT_FOUND_MESSAGE)
    return prescription


async def _child_from_path(child_id: int, guardian: CurrentGuardian) -> Any:
    return await get_my_child_or_404(child_id, guardian)


async def _prescription_from_path(prescription_id: int, guardian: CurrentGuardian) -> Any:
    return await get_my_prescription_or_404(prescription_id, guardian)


# 경로 파라미터 {child_id}, {prescription_id}를 쓰는 라우터용 의존성.
# FastAPI는 실행 중에 타입을 읽기 때문에, BE-2 모델이 생기기 전에는 Any로 둔다.
# 모델이 머지되면 Annotated[Child, ...], Annotated[Prescription, ...]로 바꾼다.
MyChild = Annotated[Any, Depends(_child_from_path)]
MyPrescription = Annotated[Any, Depends(_prescription_from_path)]
