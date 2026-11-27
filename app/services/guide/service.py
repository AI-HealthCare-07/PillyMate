"""BE-2가 부르는 가이드 생성 입구: generate_guide(child, prescription, medications, references).

BE-2는 확정 API(PUT /prescriptions/{id}/confirm)로 저장한 값을 DB 모양 그대로 넘기면 된다.
이 파일이 그 값을 가이드 모듈(generator.generate)이 쓰는 모양으로 바꾼다.

- route·dosage_form: DB 코드값(ORAL, SYRUP …) → 가이드 스키마의 한글 값(내복, 시럽 …)
- ingredient(성분): DB에 칸이 없으므로 약 이름에서 찾는다 (merge.ingredient_of, 모르면 None)
- disease_group(질환군): 보호자가 입력한 병명(diagnosis_user_input)을 템플릿의 match_user_input과 비교해 정한다
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.services.guide.drug_reference import build_references
from app.services.guide.generator import TEMPLATE_DIR, CallLLM, generate, load, prepare_child
from app.services.guide.merge import ingredient_of
from app.services.guide.permit_ingredient_index import form_word
from app.services.guide.unreviewed_drug_reference import UNREVIEWED_REASON, is_unreviewed, unreviewed_references

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
# DB 제형이 ETC(기타)일 때 약 이름의 제형 낱말 → 가이드 스키마의 제형. 귀약을 '기타'로 두면 LLM이 안약·먹는 약으로 착각한다.
FORM_FROM_NAME = {
    "이용액": "점이액",
    "점이액": "점이액",
    "점안액": "점안액",
    "나잘스프레이": "비강분무제",
    "에보할러": "흡입제",
    "흡입액": "흡입제",
    "네뷸": "흡입제",
    "레스풀": "흡입제",
    "터부헬러": "흡입제",
    "좌약": "좌제",
    "좌제": "좌제",
    "크림": "크림",
    "연고": "연고",
    "로션": "로션",
}
GROUP_ORDER = ["cold_bronchitis", "otitis_sinusitis", "enteritis", "dermatitis", "conjunctivitis"]


def normalize_medication(m: dict[str, Any]) -> dict[str, Any]:
    """DB 모양의 약 1개 → 가이드 모듈 모양. 원래 dict는 바꾸지 않는다."""
    out = dict(m)
    route = m.get("route")
    form = m.get("dosage_form")
    out["route"] = ROUTE_KO.get(route, route) if route else None
    out["dosage_form"] = DOSAGE_FORM_KO.get(form, form) if form else None
    if out["dosage_form"] in (None, "기타"):  # '에펙신이용액' → 점이액
        out["dosage_form"] = FORM_FROM_NAME.get(form_word(m.get("name")) or "", out["dosage_form"])
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
    references   : {medication_id: 참조 정보 요약}. 비우면 references_for()로 찾는다 (못 찾은 약은 약사 확인이 켜짐)
    call_llm     : 테스트용. 비우면 Claude Haiku를 부른다.
    """
    groups = disease_groups_of(prescription.get("diagnosis_user_input"))
    llm_label = "LLM"
    if call_llm is None:
        from app.services.guide.llm_client import LLM_LABEL, call_haiku  # 키가 필요할 때만 불러온다

        call_llm, llm_label = call_haiku, LLM_LABEL
    meds = [normalize_medication(m) for m in medications]
    if references is None:  # 넘겨받은 게 없으면 약 정보 파일에서 찾는다 (RAG, GUIDE-004)
        references = references_for(meds)
    guide = generate(
        call_llm=call_llm,
        child=child,
        prescription=prescription,
        medications=meds,
        references=references,
        disease_group=groups[0] if groups else "other",  # 1차: 처음 나온 질환군 1개. 여러 개 함께 보여 주기는 다음 단계
        llm_label=llm_label,
    )
    guide = fix_external_wording(drop_unsupported_form_tips(guide, meds, references))
    age_months = prepare_child(child, prescription.get("prescription_date"))["age_months"]
    guide = drop_inapplicable_age_conditions(guide, age_months)
    guide = require_pharmacist_check(guide, {mid for mid, ref in references.items() if is_unreviewed(ref)})
    return apply_dur_age_alerts(guide, dur_age_alerts(references, age_months))


# how_to_give에서 근거를 확인할 제형 요령: (문장에 이 말이 있으면, 근거 글에 이 말 중 하나가 있어야 남긴다)
# 프롬프트로 막아도 LLM이 건조시럽에 '물에 녹여', 시럽에 '계량컵으로 재서'를 자주 지어내서 코드로 거른다.
# 물약 계량 안내는 med_tips(form.liquid.measure)가 따로 붙인다.
# (문장에 이 말이 있으면, 근거 글에 이 말 중 하나가 있어야 남긴다, 근거 없이도 되는 제형 — 프롬프트의 기본 요령 예시)
FORM_TIP_EVIDENCE: list[tuple[tuple[str, ...], tuple[str, ...], frozenset[str]]] = [
    (("녹여", "녹인", "녹이", "섞어", "섞은", "타서"), ("녹여", "녹인", "녹이", "용해", "물에 타", "섞"), frozenset()),
    (("계량",), ("계량",), frozenset()),  # 계량컵·계량스푼·계량 도구
    (("흔들어", "흔든"), ("흔들", "흔든"), frozenset()),
    (("닿지 않",), ("닿지",), frozenset({"점안액"})),  # 안약의 '용기 끝이 눈에 닿지 않게'만 기본 요령
    (("눌러", "누르"), ("눌러", "누르", "누른"), frozenset()),  # 귀약을 넣고 귀 입구 누르기 등
    (("당겨", "당기"), ("당겨", "당기"), frozenset()),  # 귓바퀴 당기기
    (("기울", "옆으로 눕", "눕혀", "누워", "위로 향하게"), ("기울", "눕", "누워", "향하게"), frozenset()),
]


def drop_unsupported_form_tips(
    guide: dict[str, Any], medications: list[dict[str, Any]], references: dict[int, str]
) -> dict[str, Any]:
    """how_to_give에서 reference·usage에 근거가 없는 제형 요령 문장을 뺀다. 문장이 하나도 안 남으면 그대로 둔다."""
    usage = {
        m["medication_id"]: " ".join(str(m.get(k) or "") for k in ("usage", "pharmacy_caution")) for m in medications
    }
    for card in guide.get("medications", []):
        mid = card.get("medication_id")
        evidence = f"{references.get(mid, '')} {usage.get(mid, '')}"
        form = card.get("dosage_form")
        kept = [
            s
            for s in card.get("how_to_give") or []
            if not any(
                any(w in s for w in words) and not any(e in evidence for e in proof) and form not in forms
                for words, proof, forms in FORM_TIP_EVIDENCE
            )
        ]
        if kept:
            card["how_to_give"] = kept
    return guide


# 외용 약(바르는·넣는 약) 문장에 LLM이 쓴 '먹이다' → '쓰다'. 긴 것부터 바꾼다.
EXTERNAL_VERB_FIXES = [
    ("먹이기를 멈추", "쓰기를 멈추"),
    ("먹이기를 중단", "쓰기를 중단"),
    ("먹이거나 바르지", "쓰지"),
    ("먹이거나 넣지", "쓰지"),
    ("먹이기 전에", "쓰기 전에"),
    ("먹이지 말고", "쓰지 말고"),
    ("먹이지 않아요", "쓰지 않아요"),
    ("먹이지 마세요", "쓰지 마세요"),
    ("먹여 주세요", "써 주세요"),
    ("먹여요", "써요"),
]
# 귀약(점이액)을 안약 낱말로 부른 것
EAR_WORD_FIXES = [("귀 점안약", "귀약"), ("귀점안약", "귀약"), ("점안약", "귀약"), ("점안액", "귀약"), ("안약", "귀약")]
_CARD_TEXT_FIELDS = ("purpose", "how_to_give", "cautions", "common_side_effects", "storage")


def _replace_all(text: str, fixes: list[tuple[str, str]]) -> str:
    for old, new in fixes:
        text = text.replace(old, new)
    return text


def fix_external_wording(guide: dict[str, Any]) -> dict[str, Any]:
    """외용 약 카드의 '먹이다'를 '쓰다'로, 귀약 카드의 '점안약'을 '귀약'으로 바꾼다. 귀약이 있으면 요약도."""
    has_ear = False
    for card in guide.get("medications", []):
        fixes: list[tuple[str, str]] = []
        if card.get("route") == "외용":
            fixes += EXTERNAL_VERB_FIXES
        if card.get("dosage_form") == "점이액":
            fixes += EAR_WORD_FIXES
            has_ear = True
        if not fixes:
            continue
        for key in _CARD_TEXT_FIELDS:
            value = card.get(key)
            if isinstance(value, str):
                card[key] = _replace_all(value, fixes)
            elif isinstance(value, list):
                card[key] = [_replace_all(v, fixes) if isinstance(v, str) else v for v in value]
    if has_ear and isinstance(guide.get("summary"), str):
        guide["summary"] = _replace_all(guide["summary"], EAR_WORD_FIXES[:3])
    return guide


# '만 2세 미만', '생후 3개월 미만', '1세 미만' 같은 나이 조건. 아이가 이미 그 나이를 넘었으면 그 문장은 이 아이와 상관없다.
_AGE_UNDER = re.compile(r"(?:생후\s*|만\s*)?(\d+)\s*(개월|세|살)\s*미만")
_AGE_OVER = re.compile(r"(?:생후\s*|만\s*)?(\d+)\s*(개월|세|살)\s*이상")
_AGE_COMPARE = re.compile(r"이 아이는[^.]*(?:이상|미만|넘)")  # '이 아이는 만 2세 이상이에요' 같은 비교 문장
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
AGE_FALLBACK_REASON = "복용 방법을 약사에게 한 번 확인해 주세요."


def _age_limit_months(num: str, unit: str) -> int:
    return int(num) * (1 if unit == "개월" else 12)


def _applies(sentence: str, age_months: int) -> bool:
    """문장의 나이 조건('N세 미만', 'N세 이상')이 모두 이 아이에게 맞으면 True. 조건이 없으면 True.

    '1세 이상 6세 미만'처럼 범위로 쓴 문장은 두 조건을 다 봐야 해서 '모두'로 본다.
    """
    if _AGE_COMPARE.search(sentence):
        return False
    under = [age_months < _age_limit_months(n, u) for n, u in _AGE_UNDER.findall(sentence)]
    over = [age_months >= _age_limit_months(n, u) for n, u in _AGE_OVER.findall(sentence)]
    return all(under + over)


def _all_applicable(text: str, age_months: int) -> bool:
    return all(_applies(s, age_months) for s in _SENTENCE_END.split(text.strip()) if s)


REASON_MAX = 80  # guide_content.schema.json의 pharmacist_check.reason maxLength
REASON_SEP = "; "  # generator.assemble()이 코드 규칙 이유(알레르기 등)와 LLM 이유를 이을 때 쓰는 구분자


def _reason_parts(reason: str | None) -> list[str]:
    """약사 확인 이유 → 이유 하나씩. assemble()이 '알레르기 이유; LLM 이유'처럼 이어 붙인 것을 나눈다."""
    return [p.strip() for p in (reason or "").split(REASON_SEP) if p.strip()]


def _join_reasons(parts: list[str]) -> str:
    """이유들을 앞에서부터 80자 안에 들어가는 만큼 잇는다. 같은 이유는 한 번만. 첫 이유는 길어도 둔다."""
    out: list[str] = []
    for p in dict.fromkeys(parts):
        if not out or len(REASON_SEP.join([*out, p])) <= REASON_MAX:
            out.append(p)
    return REASON_SEP.join(out)


def drop_inapplicable_age_conditions(guide: dict[str, Any], age_months: int) -> dict[str, Any]:
    """주의·약사 확인 이유에서 이 아이 나이에 맞지 않는 나이 조건('1세 미만 영아는…', '10세 이상은…' — 2살 아이)을 뺀다.

    프롬프트로 막아도 LLM이 reference의 나이 조건을 그대로 옮겨서 코드로 거른다. 해당하는 조건은 그대로 둔다.
    주의는 항목을 통째로 뺀다 — 한 문장만 빼면 '아이 나이가 이 기준에 해당하는지…'처럼 뒷문장이 혼자 남는다.
    약사 확인 이유도 같은 이유로, 이유(REASON_SEP로 나눈 하나) 안에 맞지 않는 문장이 있으면 그 이유를 통째로 뺀다.
    다른 이유(알레르기 규칙 등)는 남기고, 남는 이유가 없으면 기본 문장으로 바꾼다.
    """
    for card in guide.get("medications", []):
        card["cautions"] = [c for c in card.get("cautions") or [] if _all_applicable(c, age_months)]
        check = card.get("pharmacist_check") or {}
        if check.get("needed") and check.get("reason"):
            parts = _reason_parts(check["reason"])
            kept = [p for p in parts if _all_applicable(p, age_months)]
            if len(kept) != len(parts):
                check["reason"] = _join_reasons(kept) if kept else AGE_FALLBACK_REASON
    return guide


def require_pharmacist_check(guide: dict[str, Any], medication_ids: set[int]) -> dict[str, Any]:
    """검수 전 정보로 설명한 약은 '약사 확인'을 반드시 켠다.

    LLM이 다른 이유(알레르기 등)를 적었으면 그 이유를 두고, 이유가 없으면 '검수 전 정보' 이유를 붙인다.
    (프롬프트는 LLM에게 검수 전 이유를 쓰지 말라고 한다 — 두 이유를 이어 붙여 80자를 넘기던 문제)
    """
    for card in guide.get("medications", []):
        check = card.get("pharmacist_check") or {}
        if card.get("medication_id") in medication_ids and not (check.get("needed") and check.get("reason")):
            card["pharmacist_check"] = {"needed": True, "reason": check.get("reason") or UNREVIEWED_REASON}
    return guide


# reference 안의 'DUR 연령 금기' 칸. 다음 칸 이름(예: ' 투여 금기:') 앞까지가 그 칸이다.
_DUR_FIELD = re.compile(r"연령 금기\(DUR\): (.*?)(?= (?:투여 금기|소아|경고|주의\(e약은요\)|보관|흔한 부작용): |$)")
_UNDER_AGE = re.compile(r"(\d+)\s*(세|개월)\s*미만")
DUR_AGE_REASON = "식약처 DUR에 {limit} 미만 연령 금기가 있어요. 먹이기 전에 약사에게 꼭 확인해 주세요."  # 80자 이내
DUR_AGE_REASON_SHORT = "식약처 DUR {limit} 미만 연령 금기예요"  # 다른 이유(알레르기 등)와 함께 80자 안에 넣을 때
DUR_AGE_CAUTION = "식약처 연령 금기(DUR): {text} 먹이기 전에 처방한 곳이나 약사에게 꼭 확인해 주세요."
DUR_CAUTION_TEXT_MAX = 90  # 주의 칸에 옮길 DUR 원문 길이 (문장 단위로 자른다)
MAX_CAUTIONS = 4  # LLMMedication.cautions와 같게


@dataclass(frozen=True)
class DurAgeAlert:
    limit: str  # '12세', '6개월'
    text: str  # DUR 원문 (앞 문장들)

    @property
    def reason(self) -> str:
        return DUR_AGE_REASON.format(limit=self.limit)

    @property
    def short_reason(self) -> str:
        return DUR_AGE_REASON_SHORT.format(limit=self.limit)

    @property
    def caution(self) -> str:
        return DUR_AGE_CAUTION.format(text=self.text)


def _leading_sentences(text: str, limit: int) -> str:
    """문장 단위로 앞에서부터 limit자까지. 첫 문장이 길면 잘라서 '…'."""
    out = ""
    for s in re.split(r"(?<=[.。])\s*", text.strip()):
        if not s:
            continue
        nxt = f"{out} {s}".strip()
        if len(nxt) > limit:
            break
        out = nxt
    if not out:
        out = text[: limit - 1] + "…"
    return out if out.endswith((".", "…")) else out + "."


def dur_age_alerts(references: dict[int, str], age_months: int) -> dict[int, DurAgeAlert]:
    """reference의 DUR 연령 금기('12세 미만' 등)에 아이 나이가 걸리는 약만 {medication_id: DurAgeAlert}.

    LLM이 금기를 '조심해요'로 약하게 옮겨도 화면에는 DUR 원문 주의와 약사 확인 이유가 반드시 남게 한다.
    """
    alerts: dict[int, DurAgeAlert] = {}
    for mid, ref in references.items():
        m = _DUR_FIELD.search(ref or "")
        if not m:
            continue
        for num, unit in _UNDER_AGE.findall(m.group(1)):
            limit_months = int(num) * (12 if unit == "세" else 1)
            if age_months < limit_months:
                alerts[mid] = DurAgeAlert(f"{num}{unit}", _leading_sentences(m.group(1), DUR_CAUTION_TEXT_MAX))
                break
    return alerts


def apply_dur_age_alerts(guide: dict[str, Any], alerts: dict[int, DurAgeAlert]) -> dict[str, Any]:
    """DUR 연령 금기에 걸리는 약: 주의 칸 맨 앞에 DUR 원문을 두고, 약사 확인 이유 맨 앞에 DUR 문장을 둔다.

    LLM이 같은 나이 조건('12세 미만')으로 쓴 주의·이유는 겹치니 뺀다 (약하게 옮긴 문장이 남지 않게).
    다른 이유(알레르기 규칙·같은 성분 등)는 DUR 짧은 문장 뒤에 남긴다. 기본 문장(검수 전·나이 대체)은 DUR 문장이 대신한다.
    """
    generic = {UNREVIEWED_REASON, AGE_FALLBACK_REASON}
    for card in guide.get("medications", []):
        alert = alerts.get(card.get("medication_id"))
        if not alert:
            continue
        same_limit = re.compile(rf"{re.escape(alert.limit)}\s*미만")
        others = [c for c in card.get("cautions") or [] if not same_limit.search(c)]
        card["cautions"] = [alert.caution, *others][:MAX_CAUTIONS]
        check = card.get("pharmacist_check") or {}
        reasons = _reason_parts(check.get("reason")) if check.get("needed") else []
        reasons = [r for r in reasons if r not in generic and not same_limit.search(r)]
        reason = _join_reasons([alert.short_reason, *reasons]) if reasons else alert.reason
        card["pharmacist_check"] = {"needed": True, "reason": reason}
    return guide


def references_for(medications: list[dict[str, Any]]) -> dict[int, str]:
    """약마다 효능·주의·부작용·보관 요약을 찾는다.

    1) 검수된 약 정보 파일(drug_refs.json) — 같은 성분이면 다른 제품 문서도 쓴다
    2) 1)에 없는 약은 식약처 API로 '검수 전' 요약 (unreviewed_drug_reference, MFDS_API_KEY가 있을 때만)
    둘 다 없는 약은 빠진다 → 가이드에서 '참조 정보 없음'·약사 확인.
    """
    refs = build_references(medications)
    missing = [m for m in medications if m["medication_id"] not in refs]
    if missing:
        refs.update(unreviewed_references(missing))
    return refs
