"""Claude Haiku 호출 (가이드 생성·챗봇 공용).

- API 키: 환경변수 ANTHROPIC_API_KEY (루트 .env → docker compose env_file로 컨테이너에 전달됨)
- 1회 호출 25초 제한, SDK 자체 재시도는 끈다. 재시도는 generator.generate()가 1번만 한다.
  → 최악의 경우 25초 × 2회 = 50초로, 서버 가이드 타임아웃(60초) 안에 끝난다.
- 답은 tool 호출로 받아 LLMGuideOutput 모양을 강제한다 (Structured Output).
- 실패하면 LLMCallError(ValueError)를 내고, generate()가 이를 잡아 재시도 → fallback 가이드로 넘어간다.
"""

from __future__ import annotations

import logging
from typing import Any, cast

import anthropic
from anthropic.types import MessageParam, ToolChoiceToolParam, ToolParam

from app.dtos.guide import LLMGuideOutput

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-5-5"
LLM_LABEL = f"Claude Haiku ({MODEL})"  # generate(llm_label=...)에 넘겨 가이드 '검증 정보'에 표시
TIMEOUT_SECONDS = 25.0
MAX_TOKENS = 3000
TOOL_NAME = "submit_guide"


class LLMCallError(ValueError):
    """LLM 호출 실패 (타임아웃·API 오류·답 형식 오류)."""


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    # 처음 호출할 때 만든다. import만 해도 API 키를 요구하지 않도록.
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=TIMEOUT_SECONDS, max_retries=0)
    return _client


def call_tool(
    system: str,
    messages: list[dict[str, Any]],
    tool_name: str,
    description: str,
    input_schema: dict[str, Any],
    max_tokens: int = MAX_TOKENS,
) -> dict[str, Any]:
    """Haiku를 1번 불러 tool 입력(dict)을 받는다. 가이드·챗봇이 함께 쓴다. 실패하면 LLMCallError."""
    tool: ToolParam = {"name": tool_name, "description": description, "input_schema": input_schema}
    tool_choice: ToolChoiceToolParam = {"type": "tool", "name": tool_name}
    try:
        res = _get_client().messages.create(
            model=MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=cast(list[MessageParam], messages),
            tools=[tool],
            tool_choice=tool_choice,
        )
    except anthropic.APIError as e:  # 타임아웃·연결 오류·4xx/5xx 모두 포함
        raise LLMCallError(f"LLM 호출 실패: {type(e).__name__}") from e
    u = res.usage
    logger.info(
        "LLM usage(%s): input=%s output=%s cache_write=%s cache_read=%s stop=%s",
        tool_name,
        u.input_tokens,
        u.output_tokens,
        u.cache_creation_input_tokens,
        u.cache_read_input_tokens,
        res.stop_reason,
    )
    for block in res.content:
        if block.type == "tool_use" and block.name == tool_name:
            return dict(block.input)  # type: ignore[arg-type]
    raise LLMCallError(f"LLM이 답을 제출하지 않았어요 (tool={tool_name}, stop_reason={res.stop_reason})")


def call_haiku(system: str, user: str) -> dict[str, Any]:
    """generate(call_llm=call_haiku, ...)에 넣는 함수. LLMGuideOutput 모양의 dict를 돌려준다."""
    return call_tool(
        system,
        [{"role": "user", "content": user}],
        TOOL_NAME,
        "완성한 가이드를 제출한다.",
        LLMGuideOutput.model_json_schema(),
    )
