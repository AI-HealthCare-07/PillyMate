from fastapi import APIRouter, status

from app.dependencies.security import CurrentGuardian
from app.dtos.guardians import MeResponse

me_router = APIRouter(prefix="/me", tags=["me"])


@me_router.get("", response_model=MeResponse, status_code=status.HTTP_200_OK)
async def get_me(guardian: CurrentGuardian) -> MeResponse:
    """A2. 내 정보 (저장된 토큰이 유효한지 확인할 때 사용, 401이면 로그인 화면으로)"""
    return MeResponse(
        guardian_id=guardian.id,
        email=guardian.email,
        name=guardian.name,
        birth_date=guardian.birth_date,
        gender=guardian.gender,
        phone_number=guardian.phone_number,
        created_at=guardian.created_at,
    )
