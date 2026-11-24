"""진짜 Claude Haiku로 가이드 1건을 만들어 보는 개발용 스크립트.

실행 (저장소 루트에서):
    uv run --env-file .env python -m app.scripts.try_guide

- 가상 데이터 15번과 비슷한 기침감기 사례(3세 7개월, 16.9kg, 약 3개)를 씀. 실제 환자 자료가 아님.
- 결과는 루트의 guide_try_result.json 에 저장. 커밋하지 않음.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any

from app.services.guide.generator import generate
from app.services.guide.llm_client import LLM_LABEL, call_haiku

CHILD: dict[str, Any] = {
    "birth_date": "2023-04-05",  # 조제일 기준 3세 7개월
    "weight_kg": 16.9,
    "allergies": [],
}

PRESCRIPTION: dict[str, Any] = {
    "prescription_id": 15,
    "prescription_date": "2026-11-12",
    "diagnosis_user_input": "기침감기",
    "symptom_notes": "기침, 콧물, 미열",
}

MEDICATIONS: list[dict[str, Any]] = [
    {
        "medication_id": 1501,
        "name": "뮤코펙트시럽",
        "ingredient": "암브록솔",
        "dosage_form": "시럽",
        "route": "내복",
        "dose_per_time": 2.5,
        "unit": "mL",
        "daily_count": 3,
        "total_days": 5,
        "as_needed": False,
        "max_daily_count": None,
        "usage": "식후 30분",
    },
    {
        "medication_id": 1502,
        "name": "지르텍시럽",
        "ingredient": "세티리진",
        "dosage_form": "시럽",
        "route": "내복",
        "dose_per_time": 2.5,
        "unit": "mL",
        "daily_count": 2,
        "total_days": 5,
        "as_needed": False,
        "max_daily_count": None,
        "usage": "아침, 자기 전",
    },
    {
        "medication_id": 1503,
        "name": "챔프시럽",
        "ingredient": "아세트아미노펜",
        "dosage_form": "시럽",
        "route": "내복",
        "dose_per_time": 6,
        "unit": "mL",
        "daily_count": None,
        "total_days": 5,
        "as_needed": True,
        "max_daily_count": 5,
        "usage": "열 날 때, 4시간 이상 간격",
    },
]

# RAG(약 정보 검색)는 아직 연결 전이라 비워 둠 → 모든 약에 '약사 확인'이 켜지는 게 정상
REFERENCES: dict[int, str] = {}

OUTPUT = Path("guide_try_result.json")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    start = time.perf_counter()
    guide = generate(
        call_llm=call_haiku,
        child=CHILD,
        prescription=PRESCRIPTION,
        medications=MEDICATIONS,
        references=REFERENCES,
        disease_group="cold_bronchitis",
        llm_label=LLM_LABEL,
    )
    elapsed = time.perf_counter() - start

    OUTPUT.write_text(json.dumps(guide, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"걸린 시간: {elapsed:.1f}초")
    print(f"status: {guide.get('status')}")
    print(f"summary: {guide.get('summary')}")
    for m in guide.get("medications", []):
        print(f"- {m.get('name')}: {m.get('dose_text')} / 약사 확인={m.get('pharmacist_check')}")
    print(f"저장: {OUTPUT.resolve()}")


if __name__ == "__main__":
    main()
