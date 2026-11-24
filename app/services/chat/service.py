"""챗봇 API의 규칙: 내 처방인지, 가이드가 있는지 확인하고 bot.answer_chat을 부른다."""

import logging

import anyio
from fastapi import HTTPException, status

from app.dtos.chat import ChatRequest, ChatResponse
from app.repositories.prescription_repository import PrescriptionRepository
from app.services.chat.bot import answer_chat

logger = logging.getLogger(__name__)

CHAT_TIMEOUT_SECONDS = 30  # LLM 1번(25초 제한) + 여유

MSG_NOT_FOUND = "처방전을 찾을 수 없어요."
MSG_NO_GUIDE = "가이드를 먼저 만들어 주세요."
MSG_FAILED = "답변을 만들지 못했어요. 잠시 후 다시 물어봐 주세요."


class ChatService:
    def __init__(self) -> None:
        self.repo = PrescriptionRepository()

    async def ask(self, prescription_id: int, guardian_id: int, request: ChatRequest) -> ChatResponse:
        p = await self.repo.get_for_guardian(prescription_id, guardian_id)
        if p is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_NOT_FOUND)
        guide = await self.repo.get_guide(p.id)
        if guide is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=MSG_NO_GUIDE)

        content: dict = guide.guide_content  # type: ignore[assignment]
        prescription = {"prescription_date": p.prescription_date.isoformat() if p.prescription_date else None}
        try:
            with anyio.fail_after(CHAT_TIMEOUT_SECONDS):
                result = await anyio.to_thread.run_sync(
                    lambda: answer_chat(content, prescription, request.message, request.history),
                    abandon_on_cancel=True,
                )
        except (ValueError, TimeoutError) as e:  # LLMCallError·형식 오류·시간 초과
            logger.warning("챗봇 답변 실패: prescription_id=%s (%s)", p.id, type(e).__name__)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=MSG_FAILED) from e
        return ChatResponse(**result)
