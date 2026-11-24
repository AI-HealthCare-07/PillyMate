"""챗봇 답변 로직 테스트 (REQ-CHAT-001·002). LLM 대신 가짜 함수를 넣어 비용 없이 돈다."""

from typing import Any

import pytest

from app.dtos.chat import ChatTurn
from app.services.chat.bot import EMERGENCY_REPLY, SAFETY_NOTES, answer_chat, chat_context, is_emergency
from app.services.guide.service import generate_guide
from app.services.guide.view import to_view

CHILD = {"birth_date": "2023-04-02", "weight_kg": 16.9, "allergies": "계란"}
PRESCRIPTION = {"prescription_id": 1, "prescription_date": "2026-11-12", "diagnosis_user_input": "중이염"}
MEDS = [
    {
        "medication_id": 1,
        "name": "세파클러건조시럽(내복)/60(1)mL/병",
        "dose_per_time": 4.2,
        "unit": "mL",
        "daily_count": 3,
        "total_days": 5,
        "as_needed": False,
        "usage": "1일 3회 식후 30분",
        "route": "ORAL",
        "dosage_form": "DRY_SYRUP",
    },
    {
        "medication_id": 2,
        "name": "세토펜현탁액(아세트아미노펜)",
        "dose_per_time": 5,
        "unit": "mL",
        "daily_count": None,
        "total_days": 3,
        "as_needed": True,
        "max_daily_count": 4,
        "usage": "열날 때 4시간 이상 간격",
        "route": "ORAL",
        "dosage_form": "SYRUP",
    },
]


def no_llm(system: str, user: str) -> dict:
    raise ValueError("offline")


GUIDE = to_view(generate_guide(CHILD, PRESCRIPTION, MEDS, call_llm=no_llm))
RX = {"prescription_date": "2026-11-12"}


class FakeLLM:
    def __init__(self, answer: str, category: str) -> None:
        self.answer, self.category = answer, category
        self.calls: list[tuple[str, list[dict[str, Any]]]] = []

    def __call__(self, system: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self.calls.append((system, messages))
        return {"answer": self.answer, "category": self.category}


@pytest.mark.parametrize(
    "text",
    [
        "아이가 숨을 잘 못 쉬어요",
        "경련을 해요",
        "축 늘어져서 깨워도 안 깨요",
        "입술이 파랗게 됐어요",
        "실수로 해열제를 두 번 먹였어요",
    ],
)
def test_emergency_skips_llm(text):
    llm = FakeLLM("무시됨", "general")
    out = answer_chat(GUIDE, RX, text, call_llm=llm)
    assert out == {"reply": EMERGENCY_REPLY, "category": "emergency", "needs_professional": True}
    assert llm.calls == []  # LLM을 부르지 않음


@pytest.mark.parametrize("text", ["약을 먹고 토했어요", "시럽은 어떻게 보관해요?", "자는 애 안 깨우고 먹여도 돼요?"])
def test_normal_questions_are_not_emergency(text):
    assert not is_emergency(text)


def test_normal_answer_and_context():
    llm = FakeLLM("열이 날 때만 5mL를 먹이고 4시간 넘게 띄워 주세요.", "medication_use")
    history = [ChatTurn(role="assistant", text="무엇이 궁금하세요?")]
    out = answer_chat(GUIDE, RX, "해열제는 언제 다시 먹여요?", history, call_llm=llm)
    assert out["category"] == "medication_use"
    assert out["needs_professional"] is False
    assert out["reply"].startswith("열이 날 때만")

    _, messages = llm.calls[0]
    user = messages[0]["content"]
    assert "세토펜현탁액" in user.split("<지난_대화>")[0]  # 처방 내용은 처방_정보 안에
    assert "챗봇: 무엇이 궁금하세요?" in user
    assert user.endswith("보호자 질문: 해열제는 언제 다시 먹여요?")


def test_dose_change_and_diagnosis_get_safety_note():
    dose = answer_chat(
        GUIDE, RX, "열이 안 내리는데 두 배로 늘려도 돼요?", call_llm=FakeLLM("처방은 1회 5mL예요.", "dose_change")
    )
    assert dose["reply"].endswith(SAFETY_NOTES["dose_change"]) and dose["needs_professional"] is True
    diag = answer_chat(GUIDE, RX, "중이염 다 나은 거죠?", call_llm=FakeLLM("판단하기 어려워요.", "diagnosis"))
    assert diag["reply"].endswith(SAFETY_NOTES["diagnosis"])


def test_llm_emergency_category_replaced():
    out = answer_chat(GUIDE, RX, "애가 이상해요", call_llm=FakeLLM("괜찮아요", "emergency"))
    assert out["reply"] == EMERGENCY_REPLY


def test_bad_llm_output_raises_value_error():
    def broken(system: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
        return {"answer": "답", "category": "없는종류"}

    with pytest.raises(ValueError):
        answer_chat(GUIDE, RX, "보관은요?", call_llm=broken)


def test_context_has_no_child_name_or_birth_date():
    ctx = chat_context(GUIDE, RX)
    assert set(ctx["child"]) == {"age_text", "weight_kg", "allergies"}
    assert "birth_date" not in str(ctx)
    assert [m["name"] for m in ctx["medications"]] == [m["name"] for m in MEDS]
