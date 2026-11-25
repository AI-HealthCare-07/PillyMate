from fastapi import APIRouter, status

from app.dependencies.security import CurrentGuardian
from app.dtos.children import ChildCreateRequest, ChildResponse
from app.services.children import create_child, list_children, to_child_response

child_router = APIRouter(prefix="/children", tags=["children"])


@child_router.post("", response_model=ChildResponse, status_code=status.HTTP_201_CREATED)
async def register_child(guardian: CurrentGuardian, data: ChildCreateRequest) -> ChildResponse:
    """3. 자녀 등록 — 보호자 동의(consent_agreed=true)가 있어야 하고, 만 18세 미만만 등록한다."""
    return to_child_response(await create_child(guardian, data))


@child_router.get("", response_model=list[ChildResponse], status_code=status.HTTP_200_OK)
async def get_my_children(guardian: CurrentGuardian) -> list[ChildResponse]:
    """4. 내 자녀 목록 — 로그인한 보호자의 자녀만 등록 순서대로. 없으면 []."""
    return [to_child_response(child) for child in await list_children(guardian)]
