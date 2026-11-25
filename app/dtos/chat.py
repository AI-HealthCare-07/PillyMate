"""챗봇 API 요청/응답 형식 (REQ-CHAT-001·002).

1차에서는 대화를 DB에 저장하지 않는다. 화면(FE)이 최근 대화를 history로 같이 보낸다.
- 요청·응답 형식 -
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# LLM이 질문 종류를 함께 고른다. 코드가 이 값을 보고 안전 문구를 붙인다 (REQ-CHAT-002).
ChatCategory = Literal[
    "medication_use",  # 먹이는 법·시간·보관·빠뜨렸을 때
    "side_effect",  # 부작용·반응
    "home_care",  # 집에서 돌보기
    "dose_change",  # 양을 늘리거나 줄이기, 끊기, 다른 약 더 먹이기
    "diagnosis",  # 무슨 병인지, 낫는 중인지 판단해 달라는 질문
    "emergency",  # 응급 증상
    "out_of_scope",  # 처방·육아와 관계없는 질문
]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    text: Annotated[str, Field(min_length=1, max_length=1000)]


class ChatRequest(BaseModel):
    message: Annotated[str, Field(min_length=1, max_length=500, description="보호자 질문")]
    history: Annotated[
        list[ChatTurn],
        Field(default_factory=list, max_length=10, description="최근 대화(오래된 것부터). 최대 10개"),
    ]


class ChatResponse(BaseModel):
    reply: str
    category: ChatCategory
    needs_professional: bool = Field(description="True면 화면에서 '의사·약사 상담' 강조 표시")


class LLMChatOutput(BaseModel):
    """LLM이 tool 입력으로 채우는 모양."""

    answer: Annotated[str, Field(description="보호자에게 보낼 답. 해요체, 4문장 이내", max_length=600)]
    category: ChatCategory
