"""BE-2가 부르는 가이드 생성 입구: generate_guide(child, prescription, medications, references).

BE-2는 확정 API(PUT /prescriptions/{id}/confirm)로 저장한 값을 DB 모양 그대로 넘기면 된다.
이 파일이 그 값을 가이드 모듈(generator.generate)이 쓰는 모양으로 바꾼다.

- route·dosage_form: DB 코드값(ORAL, SYRUP …) → 가이드 스키마의 한글 값(내복, 시럽 …)
- ingredient(성분): DB에 칸이 없으므로 약 이름에서 찾는다 (merge.ingredient_of, 모르면 None)
- disease_group(질환군): 보호자가 입력한 병명(diagnosis_user_input)을 템플릿의 match_user_input과 비교해 정한다
"""

from __future__ import annotations

from typing import Any

from app.services.guide.generator import TEMPLATE_DIR, CallLLM, generate, load
from app.services.guide.merge import ingredient_of

# 확정 API·ERD의 코드값 → 가이드 스키마(guide_content.schema.json)의 값
ROUTE_KO = {"ORAL": "내복", "EXTERNAL": "외용"}
DOSAGE_FORM_KO = {
    "SYRUP": "시럽",
    "DRY_SYRUP": "건조시럽",
    "POWDER": "산제",
    "TABLET": "정제",
    "CAPSULE": "캡슐",
    "OINTMENT": "연고",
    "CREAM": "크림",
    "EYE_DROP": "점안액",
    "SUPPOSITORY": "좌제",
    "ETC": "기타",
}
GROUP_ORDER = ["cold_bronchitis", "otitis_sinusitis", "enteritis", "dermatitis", "conjunctivitis"]


def normalize_medication(m: dict[str, Any]) -> dict[str, Any]:
    """DB 모양의 약 1개 → 가이드 모듈 모양. 원래 dict는 바꾸지 않는다."""
    out = dict(m)
    route = m.get("route")
    form = m.get("dosage_form")
    out["route"] = ROUTE_KO.get(route, route) if route else None
    out["dosage_form"] = DOSAGE_FORM_KO.get(form, form) if form else None
    if not out.get("ingredient"):
        out["ingredient"] = ingredient_of(m.get("name"))
    return out


def disease_groups_of(diagnosis_user_input: str | None) -> list[str]:
    """보호자 입력 병명 → 질환군 목록 (입력에 먼저 나온 순서). 약 이름으로 병명을 추측하지 않는다 (NFR-SAFE-002)."""
    text = (diagnosis_user_input or "").replace(" ", "")
    found: list[tuple[int, str]] = []
    for group in GROUP_ORDER:
        path = TEMPLATE_DIR / f"DATA-REF-006_{group}.json"
        if not path.exists():
            continue
        words = [w.replace(" ", "") for w in load(path.name).get("match_user_input", [])]
        hits = [text.find(w) for w in words if w and w in text]
        if hits:
            found.append((min(hits), group))
    return [g for _, g in sorted(found)]


def generate_guide(
    child: dict[str, Any],
    prescription: dict[str, Any],
    medications: list[dict[str, Any]],
    references: dict[int, str] | None = None,
    call_llm: CallLLM | None = None,
) -> dict[str, Any]:
    """확정된 처방 1건으로 가이드를 만든다. API 명세 G1(POST /prescriptions/{id}/guide)에서 BE-2가 부른다.

    child        : CHILD 행 (birth_date, weight_kg, allergies 문자열 그대로 OK)
    prescription : PRESCRIPTION 행 (prescription_id, prescription_date, diagnosis_user_input, symptom_notes)
    medications  : 그 처방의 MEDICATION 행 목록 (route·dosage_form 코드값 그대로 OK)
    references   : {medication_id: 참조 정보 요약}. RAG 전에는 비워도 된다 (그러면 약사 확인이 켜짐)
    call_llm     : 테스트용. 비우면 Claude Haiku를 부른다.
    """
    groups = disease_groups_of(prescription.get("diagnosis_user_input"))
    llm_label = "LLM"
    if call_llm is None:
        from app.services.guide.llm_client import LLM_LABEL, call_haiku  # 키가 필요할 때만 불러온다

        call_llm, llm_label = call_haiku, LLM_LABEL
    return generate(
        call_llm=call_llm,
        child=child,
        prescription=prescription,
        medications=[normalize_medication(m) for m in medications],
        references=references or {},
        disease_group=groups[0] if groups else "other",  # 1차: 처음 나온 질환군 1개. 여러 개 함께 보여 주기는 다음 단계
        llm_label=llm_label,
    )
