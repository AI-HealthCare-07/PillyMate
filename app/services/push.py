import asyncio
import json
import logging

from fastapi import HTTPException, status
from pywebpush import WebPushException, webpush

from app.core import config
from app.dtos.push import PushSendResult, PushSubscriptionRequest
from app.models.guardians import Guardian
from app.models.push_tokens import PushToken

logger = logging.getLogger(__name__)

# 기기가 꺼져 있을 때 푸시 서비스가 보관해 주는 시간(초). 기본값 0이면 바로 못 받을 때 버려진다
PUSH_TTL_SECONDS = 60 * 60
EXPIRED_STATUS_CODES = {404, 410}


def _check_vapid_config() -> None:
    if not (config.VAPID_PUBLIC_KEY and config.VAPID_PRIVATE_KEY and config.VAPID_SUBJECT):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="알림 설정이 아직 준비되지 않았어요.",
        )


def get_vapid_public_key() -> str:
    _check_vapid_config()
    return config.VAPID_PUBLIC_KEY


async def save_subscription(guardian: Guardian, data: PushSubscriptionRequest) -> None:
    """같은 브라우저(endpoint)로 다시 구독하면 새로 만들지 않고 키·보호자·활성 여부만 갱신한다."""
    await PushToken.update_or_create(
        token=data.endpoint,
        defaults={
            "guardian": guardian,
            "p256dh": data.keys.p256dh,
            "auth": data.keys.auth,
            "is_active": True,
        },
    )


async def delete_subscription(guardian: Guardian, endpoint: str) -> None:
    """내 구독만 지운다. 없으면 아무것도 안 한다."""
    await PushToken.filter(guardian=guardian, token=endpoint).delete()


def _send(token: PushToken, payload: str) -> None:
    webpush(
        subscription_info={"endpoint": token.token, "keys": {"p256dh": token.p256dh, "auth": token.auth}},
        data=payload,
        vapid_private_key=config.VAPID_PRIVATE_KEY,
        vapid_claims={"sub": config.VAPID_SUBJECT},  # 매번 새 dict로 (pywebpush가 안에 aud·exp를 써 넣음)
        ttl=PUSH_TTL_SECONDS,
    )


async def send_to_guardian(guardian: Guardian, title: str, body: str) -> PushSendResult:
    """보호자의 활성 구독 전체에 보낸다. 404/410이면 만료된 구독이라 is_active=False."""
    _check_vapid_config()
    tokens = await PushToken.filter(guardian=guardian, is_active=True)
    payload = json.dumps({"title": title, "body": body}, ensure_ascii=False)
    result = PushSendResult(sent=0, expired=0, failed=0)

    for token in tokens:
        try:
            # pywebpush는 동기 라이브러리라 서버가 멈추지 않게 별도 스레드에서 실행
            await asyncio.to_thread(_send, token, payload)
            result.sent += 1
        except WebPushException as err:
            status_code = err.response.status_code if err.response is not None else None
            if status_code in EXPIRED_STATUS_CODES:
                token.is_active = False
                await token.save(update_fields=["is_active", "updated_at"])
                result.expired += 1
            else:
                logger.warning("웹 푸시 발송 실패 push_token_id=%s status=%s", token.id, status_code)
                result.failed += 1
        except Exception:
            logger.exception("웹 푸시 발송 중 오류 push_token_id=%s", token.id)
            result.failed += 1

    return result


async def send_test_push(guardian: Guardian) -> PushSendResult:
    if not await PushToken.exists(guardian=guardian, is_active=True):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="알림 받기를 먼저 켜 주세요.")
    return await send_to_guardian(guardian, "PillyMate", "💊 테스트 알림이에요. 복약 시간이 되면 이렇게 알려 드릴게요.")
