from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.models.guardians import Guardian
from app.repositories.guardian_repository import GuardianRepository
from app.services.jwt import JwtService

LOGIN_REQUIRED_MESSAGE = "로그인이 필요해요."

# auto_error=False: 토큰이 없을 때 FastAPI 기본 응답(버전에 따라 403) 대신 아래에서 직접 401을 보낸다.
security = HTTPBearer(auto_error=False)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=LOGIN_REQUIRED_MESSAGE,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_request_user(
    credential: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> Guardian:
    """Authorization: Bearer <access_token>을 검증하고 로그인한 보호자를 돌려준다.

    토큰이 없거나, 만료됐거나, 잘못됐거나, 사용자가 없으면 모두 401 "로그인이 필요해요."
    """
    if credential is None or not credential.credentials:
        raise _unauthorized()

    try:
        verified = JwtService().verify_access_token(credential.credentials)
    except HTTPException as err:
        raise _unauthorized() from err

    guardian_id = verified.payload.get("guardian_id")
    guardian = await GuardianRepository().get_guardian(guardian_id) if guardian_id else None
    if not guardian:
        raise _unauthorized()
    return guardian


# BE-2용 축약형: 라우터 인자에 `guardian: CurrentGuardian`만 적으면 로그인 보호자가 들어온다.
CurrentGuardian = Annotated[Guardian, Depends(get_request_user)]
