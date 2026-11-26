from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.dtos.auth import LoginRequest, LoginResponse, SignUpRequest, SignUpResponse
from app.services.auth import AuthService

auth_router = APIRouter(prefix="/auth", tags=["auth"])

AuthServiceDep = Annotated[AuthService, Depends(AuthService)]


@auth_router.post("/signup", response_model=SignUpResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignUpRequest, auth_service: AuthServiceDep) -> SignUpResponse:
    """1. 회원가입"""
    guardian = await auth_service.signup(request)
    return SignUpResponse(
        guardian_id=guardian.id,
        email=guardian.email,
        name=guardian.name,
        birth_date=guardian.birth_date,
        gender=guardian.gender,
        phone_number=guardian.phone_number,
    )


@auth_router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def login(request: LoginRequest, auth_service: AuthServiceDep) -> LoginResponse:
    """2. 로그인, 토큰 발급"""
    guardian = await auth_service.authenticate(request)
    return await auth_service.login(guardian)


@auth_router.post("/demo-login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
async def demo_login(auth_service: AuthServiceDep) -> LoginResponse:
    """A1. 시연용 데모 계정 로그인 (DEMO_LOGIN_ENABLED=false면 404)"""
    guardian = await auth_service.demo_guardian()
    return await auth_service.login(guardian)
