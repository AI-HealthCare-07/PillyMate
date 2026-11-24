from fastapi import HTTPException, status
from tortoise.exceptions import IntegrityError

from app.core import config
from app.core.utils.security import hash_password, verify_password
from app.core.validators import is_adult_guardian, is_valid_password_length
from app.dtos.auth import GuardianSummary, LoginRequest, LoginResponse, SignUpRequest
from app.models.guardians import Guardian
from app.repositories.guardian_repository import GuardianRepository
from app.services.jwt import JwtService

# 명세서 8절 에러 메시지 문구
EMAIL_TAKEN_MESSAGE = "이미 가입된 이메일이에요."
PASSWORD_LENGTH_MESSAGE = "비밀번호는 8~64자로 입력해 주세요."
UNDER_AGE_MESSAGE = "만 19세 이상만 가입할 수 있어요."
LOGIN_FAILED_MESSAGE = "이메일 또는 비밀번호가 맞지 않아요."
DEMO_LOGIN_UNAVAILABLE_MESSAGE = "데모 로그인을 사용할 수 없어요."


class AuthService:
    def __init__(self) -> None:
        self.repo = GuardianRepository()
        self.jwt_service = JwtService()

    async def signup(self, data: SignUpRequest) -> Guardian:
        if not is_valid_password_length(data.password):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=PASSWORD_LENGTH_MESSAGE)
        if not is_adult_guardian(data.birth_date):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=UNDER_AGE_MESSAGE)

        email = str(data.email)
        if await self.repo.exists_by_email(email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN_MESSAGE)

        try:
            return await self.repo.create_guardian(
                email=email,
                password_hash=hash_password(data.password),
                name=data.name,
                birth_date=data.birth_date,
            )
        except IntegrityError as err:  # 동시에 같은 이메일로 가입한 경우 (UNIQUE 제약)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=EMAIL_TAKEN_MESSAGE) from err

    async def authenticate(self, data: LoginRequest) -> Guardian:
        guardian = await self.repo.get_by_email(data.email)
        # 이메일·비밀번호 중 어느 쪽이 틀렸는지 알려 주지 않는다.
        if not guardian or not verify_password(data.password, guardian.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=LOGIN_FAILED_MESSAGE)
        return guardian

    async def demo_guardian(self) -> Guardian:
        if not config.DEMO_LOGIN_ENABLED:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=DEMO_LOGIN_UNAVAILABLE_MESSAGE)
        guardian = await self.repo.get_by_email(config.DEMO_GUARDIAN_EMAIL.lower())
        if not guardian:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=DEMO_LOGIN_UNAVAILABLE_MESSAGE)
        return guardian

    async def login(self, guardian: Guardian) -> LoginResponse:
        token = self.jwt_service.create_access_token(guardian)
        return LoginResponse(
            access_token=str(token),
            expires_in=self.jwt_service.expires_in,
            guardian=GuardianSummary(
                guardian_id=guardian.id,
                name=guardian.name,
                child_count=await self.repo.count_children(guardian.id),
            ),
        )
