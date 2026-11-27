"""LLM이 돌려줘야 하는 답의 모양 (Structured Output). AI-2 guide_module.py v0.3 1번 섹션."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LLMMedication(BaseModel):
    medication_id: int
    purpose: str = Field(max_length=60, description="어떤 약인지. 병명 추측 금지")
    how_to_give: list[str] = Field(min_length=1, max_length=4)
    cautions: list[str] = Field(max_length=4)
    common_side_effects: list[str] = Field(max_length=3)
    storage: str | None = Field(default=None, max_length=80)
    pharmacist_check_needed: bool
    pharmacist_check_reason: str | None = Field(default=None, max_length=80)


class LLMHomeCarePick(BaseModel):
    template_item_id: str
    personal_note: str | None = Field(default=None, max_length=80)


class LLMGuideOutput(BaseModel):
    summary: str = Field(max_length=200)
    medications: list[LLMMedication]
    home_care_picks: list[LLMHomeCarePick] = Field(max_length=10)
    # v0.3: 오늘 체크리스트는 LLM이 쓰지 않는다. 약 시간표·관리 포인트에서 코드가 구체적인 행동으로 만든다.
