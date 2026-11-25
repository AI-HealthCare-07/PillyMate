"""
주소 POST /api/v1/prescriptions/{id}/chat
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.dependencies.security import CurrentGuardian
from app.dtos.chat import ChatRequest, ChatResponse
from app.services.chat.service import ChatService

chat_router = APIRouter(prefix="/prescriptions", tags=["chat"])


@chat_router.post("/{prescription_id}/chat", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    prescription_id: Annotated[int, Path(ge=1, description="처방 id")],
    request: ChatRequest,
    guardian: CurrentGuardian,
    service: Annotated[ChatService, Depends(ChatService)],
) -> ChatResponse:
    """S-06 챗봇. 이 처방의 가이드를 근거로 보호자 질문에 답한다 (대화는 1차에서 저장하지 않음)."""
    return await service.ask(prescription_id, guardian.id, request)
