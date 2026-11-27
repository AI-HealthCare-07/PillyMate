from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

# 서버가 이 주소로 직접 요청을 보내므로 브라우저 푸시 서비스 주소만 받는다 (내부망 주소로 요청을 보내게 만드는 공격 방지)
ALLOWED_PUSH_HOSTS = (
    "fcm.googleapis.com",  # 크롬, 안드로이드
    "push.services.mozilla.com",  # 파이어폭스
    "push.apple.com",  # 사파리, iPhone
    "notify.windows.com",  # 엣지(윈도우)
)


class PushSubscriptionKeys(BaseModel):
    p256dh: str = Field(min_length=1, max_length=255)
    auth: str = Field(min_length=1, max_length=255)


class PushSubscriptionRequest(BaseModel):
    """브라우저 PushSubscription.toJSON() 모양 그대로 받는다 (expirationTime은 무시)."""

    endpoint: str = Field(max_length=512)
    keys: PushSubscriptionKeys

    @field_validator("endpoint")
    @classmethod
    def check_push_service(cls, value: str) -> str:
        url = urlparse(value)
        host = url.hostname or ""
        allowed = any(host == h or host.endswith("." + h) for h in ALLOWED_PUSH_HOSTS)
        if url.scheme != "https" or not allowed:
            raise ValueError("지원하지 않는 푸시 주소예요.")
        return value


class PushUnsubscribeRequest(BaseModel):
    endpoint: str = Field(max_length=512)


class VapidPublicKeyResponse(BaseModel):
    public_key: str


class PushSendResult(BaseModel):
    sent: int  # 보낸 수
    expired: int  # 만료돼서 꺼진 구독 수 (404/410)
    failed: int  # 그 밖의 이유로 실패한 수
