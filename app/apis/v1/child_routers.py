from fastapi import APIRouter, Response, status

from app.dependencies.ownership import MyChild
from app.dependencies.security import CurrentGuardian
from app.dtos.children import ChildCreateRequest, ChildResponse, ChildUpdateRequest
from app.services.children import create_child, delete_child, list_children, to_child_response, update_child

child_router = APIRouter(prefix="/children", tags=["children"])


@child_router.post("", response_model=ChildResponse, status_code=status.HTTP_201_CREATED)
async def register_child(guardian: CurrentGuardian, data: ChildCreateRequest) -> ChildResponse:
    """3. 자녀 등록 — 보호자 동의(consent_agreed=true)가 있어야 하고, 만 18세 미만만 등록한다."""
    return to_child_response(await create_child(guardian, data))


@child_router.get("", response_model=list[ChildResponse], status_code=status.HTTP_200_OK)
async def get_my_children(guardian: CurrentGuardian) -> list[ChildResponse]:
    """4. 내 자녀 목록 — 로그인한 보호자의 자녀만 등록 순서대로. 없으면 []."""
    return [to_child_response(child) for child in await list_children(guardian)]


@child_router.patch("/{child_id}", response_model=ChildResponse, status_code=status.HTTP_200_OK)
async def edit_child(child: MyChild, data: ChildUpdateRequest) -> ChildResponse:
    """자녀 정보 수정 (명세 9절) — 내 자녀만. 보낸 항목만 바꾸고, 규칙·문구는 3번 등록과 같다. 남의 자녀는 404."""
    return to_child_response(await update_child(child, data))


@child_router.delete("/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_child(child: MyChild) -> Response:
    """자녀 삭제 (명세 9절) — 내 자녀만. 처방·약·가이드·알림과 원본 사진까지 영구 삭제. 남의 자녀는 404."""
    await delete_child(child)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
