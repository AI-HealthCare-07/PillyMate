from fastapi import APIRouter, Response, status

from app.dependencies.security import CurrentGuardian
from app.dtos.push import PushSendResult, PushSubscriptionRequest, PushUnsubscribeRequest, VapidPublicKeyResponse
from app.services.push import delete_subscription, get_vapid_public_key, save_subscription, send_test_push

push_router = APIRouter(prefix="/push", tags=["push"])


@push_router.get("/vapid-public-key", response_model=VapidPublicKeyResponse, status_code=status.HTTP_200_OK)
async def read_vapid_public_key() -> VapidPublicKeyResponse:
    """P1. 구독할 때 쓸 VAPID 공개 키 — 공개 값이라 로그인 없이 준다."""
    return VapidPublicKeyResponse(public_key=get_vapid_public_key())


@push_router.post("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def subscribe_push(guardian: CurrentGuardian, data: PushSubscriptionRequest) -> Response:
    """P2. 구독 저장 — 같은 브라우저로 다시 보내면 갱신만 한다."""
    await save_subscription(guardian, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@push_router.delete("/subscriptions", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_push(guardian: CurrentGuardian, data: PushUnsubscribeRequest) -> Response:
    """P3. 구독 해제 — 내 구독만 지운다. 없어도 204."""
    await delete_subscription(guardian, data.endpoint)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@push_router.post("/test", response_model=PushSendResult, status_code=status.HTTP_200_OK)
async def test_push(guardian: CurrentGuardian) -> PushSendResult:
    """P4. 나에게 테스트 발송 — 활성 구독이 없으면 404 "알림 받기를 먼저 켜 주세요." """
    return await send_test_push(guardian)
