"""챗봇을 진짜 Claude Haiku로 한 번 시험해 봐요. (질문 1개 = LLM 호출 1번, 응급 질문은 0번)

실행 (저장소 루트에서, .env에 ANTHROPIC_API_KEY가 있어야 해요):
    uv run --env-file .env python -m app.scripts.try_chat "해열제는 언제 다시 먹여요?"

DB는 쓰지 않아요. 예시 처방으로 기본 가이드를 만든 뒤(LLM 안 부름) 그 가이드를 근거로 답해요.
"""

import json
import logging
import sys

from app.services.chat.bot import answer_chat
from app.services.guide.service import generate_guide
from app.services.guide.view import to_view

CHILD = {"birth_date": "2023-04-02", "weight_kg": 16.9, "allergies": "계란"}
PRESCRIPTION = {
    "prescription_id": 1,
    "prescription_date": "2026-11-12",
    "diagnosis_user_input": "감기, 급성 기관지염",
}
MEDICATIONS = [
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
    raise ValueError("가이드는 LLM 없이 기본 가이드로 만들어요 (비용 아끼기)")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    question = " ".join(sys.argv[1:]) or "해열제는 언제 다시 먹여요?"
    guide = to_view(generate_guide(CHILD, PRESCRIPTION, MEDICATIONS, call_llm=no_llm))
    result = answer_chat(guide, {"prescription_date": "2026-11-12"}, question)
    print(f"\n질문: {question}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
