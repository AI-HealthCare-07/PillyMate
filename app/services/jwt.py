from fastapi import HTTPException, status

from app.core import config
from app.core.jwt.exceptions import TokenError
from app.core.jwt.tokens import AccessToken
from app.models.guardians import Guardian


class JwtService:
    """액세스 토큰 발급·검증. 명세서 1절: 유효시간 12시간, 리프레시 토큰 없음."""

    access_token_class = AccessToken

    @property
    def expires_in(self) -> int:
        return config.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    def create_access_token(self, guardian: Guardian) -> AccessToken:
        return self.access_token_class.for_guardian(guardian)

    def verify_access_token(self, token: str) -> AccessToken:
        try:
            return self.access_token_class(token=token)
        except TokenError as err:  # 만료(ExpiredTokenError) 포함
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요해요.") from err
