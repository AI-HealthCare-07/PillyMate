"""PillyMate AI-2 가이드 모듈: 가이드 조립과 생성 (v0.3)

역할 분리 원칙
- LLM이 쓰는 것: 요약, 약별 설명(목적·먹이는 법·주의·부작용·보관), 생활 템플릿 문장 고르기 + 한 줄 보충
- 코드가 채우는 것: 용량·횟수·일수, 위험 신호, 나이별 주의, 약 계열 팁, 오늘 체크리스트, 면책 문구, 출처
→ 숫자와 안전 문구는 LLM이 바꿀 수 없다 (NFR-SAFE-001·002).

v0.1 → v0.2 (1순위 안전 수정, 2026-11-19)
① merge_documents(): 처방전 OCR + 약봉투 OCR을 약 하나씩 짝지어 합치고, 서로 다른 값을 확인 단계에서 찾아낸다.
   - 문서 단위 오류(교부번호·환자·생년월일 불일치)는 "error" → 가이드를 만들지 말고 S-04에서 보호자 확인
   - 약 단위 불일치(필요시 여부·용량·횟수·일수)는 "warn" → rule_flags로 넘겨 약사 확인을 켠다
② schedule_of(): 횟수만 보지 않고 용법 문구에서 시간대(아침·점심·저녁·자기 전)와 복용 시점(식전·식후 등)을 읽는다.
   필요시 약은 하루 최대 횟수와 약봉투의 복용 간격(예: 간격 4시간)을 함께 담는다.
③ prepare_child(): 나이는 자녀 프로필의 생년월일과 처방일(prescription_date)로 계산한다. OCR의 나이 값은 쓰지 않는다.
v0.2 → v0.3 (팀 피드백 6가지 반영, 2026-11-20)
- 생성 근거(basis): 진료 문서, 진단코드, 교차 확인 결과, 나이·체중·알레르기·증상이 가이드에 어떻게 쓰였는지
- 오늘의 관리 포인트(focus_points): 생활 관리 3개를 항목 → 이유 → 행동으로, 이 아이에게 고른 이유와 함께
- 복약/생활 경계: 약 이야기는 약 카드·'이번 약과 함께 챙길 것'에만, 생활 안내에는 넣지 않음
- 오늘 체크리스트를 코드가 행동 목표로 만듦 (복약·생활·관찰)
- 검증 정보(verification)와 실제로 쓴 출처만 표시, 약봉투 약국 안내를 LLM 참조로 사용
+ 스키마 v0.2에 맞춤: schedule.timing·min_interval_hours 추가, 제형 이름을 스키마 목록으로 통일
  (정→정제, 가루→산제, 흡입기·흡입액→흡입제), 템플릿이 없는 질환군은 "other"로 처리.
v0.3 보완 (2026-11-27)
- 약사 확인 이유: 코드 규칙 이유와 LLM 이유(알레르기 등)를 함께 남긴다 (전에는 코드 이유가 있으면 LLM 이유가 사라짐)
- 해열제 간격 팁(숫자 고정 문장)은 처방 용법에 간격이 있으면 붙이지 않는다 (처방 숫자와 달라 헷갈리지 않게)
- 알레르기 약사 확인: 검수한 성분-알레르기 짝(ALLERGY_RULES)에 맞을 때 코드가 켠다
- 공통 위험 신호에도 나이 필터(usable)를 건다 (10세 아이에게 '생후 3개월 미만'·'기저귀' 문장이 나오던 문제)
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.dtos.guide import LLMGuideOutput, LLMHomeCarePick
from app.services.guide.merge import interval_hours
from app.services.guide.prompts import SYSTEM_PROMPT

# 이 파일 위치(app/services/guide/) 기준으로 찾는다. 실행 위치가 달라도 깨지지 않는다.
RESOURCE_DIR = Path(__file__).resolve().parents[2] / "resources" / "guide"
TEMPLATE_DIR = RESOURCE_DIR / "templates"
logger = logging.getLogger(__name__)
DISCLAIMER = (
    "이 안내는 의료진의 진단과 처방을 대신하지 않습니다. 약의 용량이나 복용법은 처방전과 약사 안내를 따르고, "
    "아이 상태가 걱정되면 바로 진료를 받으세요."
)


# ------------------------------------------------------------------ ③ 나이: 프로필 생년월일 기준
def age_months_on(birth: dt.date, on: dt.date) -> int:
    m = (on.year - birth.year) * 12 + (on.month - birth.month)
    return m - (1 if on.day < birth.day else 0)


def allergy_list(value: Any) -> list[str]:
    """알레르기를 목록으로. DB(CHILD.allergies)는 "계란, 우유" 같은 글자 하나라서 쉼표 등으로 나눈다.

    글자를 그대로 목록처럼 다루면 "계란"이 "계", "란"으로 쪼개진다.
    """
    if not value:
        return []
    if isinstance(value, str):
        parts = re.split(r"[,，、/·;\n]+", value)
    else:
        parts = [str(v) for v in value]
    return [p.strip() for p in parts if p and p.strip()]


def prepare_child(child: dict, on: str | dt.date | None = None) -> dict:
    """자녀 프로필(S-02) → 가이드용 child. birth_date가 있으면 age_months를 항상 다시 계산한다.
    OCR이 읽은 나이(약봉투의 '만 N세')는 개월을 놓치므로 쓰지 않는다."""
    out = dict(child)
    out["allergies"] = allergy_list(child.get("allergies"))
    if child.get("birth_date"):
        on_date = dt.date.fromisoformat(on) if isinstance(on, str) else (on or dt.date.today())
        out["age_months"] = age_months_on(dt.date.fromisoformat(child["birth_date"]), on_date)
    if out.get("age_months") is None:
        raise ValueError("아이 나이를 알 수 없어요: 자녀 프로필에 birth_date가 필요해요")
    return out


# ================================================================== 2. Context 템플릿 (BE-2가 넘겨줄 순서·형식)
def usable(item: dict, age_m: int) -> bool:
    """템플릿 문장을 쓸 수 있는지: 꺼 둔 문장, 출처 없는 문장, 나이가 안 맞는 문장은 뺀다."""
    return (
        not item.get("disabled")
        and item.get("source") != "TODO_SOURCE"
        and item.get("min_months", 0) <= age_m <= item.get("max_months", 227)
    )


def age_text(m: int) -> str:
    return f"생후 {m}개월" if m < 24 else (f"{m // 12}세" + (f" {m % 12}개월" if m % 12 else ""))


def _fmt(v: Any) -> Any:
    return int(v) if v is not None and float(v).is_integer() else v


def build_context(
    child: dict, prescription: dict, medications: list[dict], references: dict[int, str], home_care_template: dict
) -> str:
    """LLM에 넣는 user 메시지. 아이 이름·생년월일·병원명·주민번호·OCR 원문은 넣지 않는다."""
    meds = []
    for m in medications:
        meds.append(
            {
                "medication_id": m["medication_id"],
                "name": m["name"],
                "dosage_form": m.get("dosage_form"),
                "dose": f"{_fmt(m['dose_per_time'])}{m.get('unit') or ''}"
                if m.get("dose_per_time") is not None
                else "환부에 적당량",
                "daily_count": _fmt(m.get("daily_count")),
                "as_needed": m.get("as_needed"),
                "max_daily_count": _fmt(m.get("max_daily_count")),
                "min_interval_hours": (m.get("min_interval_h") or interval_hours(m.get("usage")))
                if m.get("as_needed")
                else None,
                "total_days": _fmt(m.get("total_days")),
                "usage": m.get("usage"),
                "reference": references.get(m["medication_id"], "참조 정보 없음 → 약사 확인 안내"),
            }
        )
    items = [
        {"template_item_id": i["id"], "section": s["key"], "text": i["text"]}
        for s in home_care_template.get("sections", [])
        for i in s["items"]
        if usable(i, child["age_months"])
    ]
    ctx = {
        "child": {
            "age": age_text(child["age_months"]),
            "age_band": age_band(child["age_months"]),
            "weight_kg": child.get("weight_kg"),
            "allergies": child.get("allergies") or [],
        },
        "diagnosis_label_from_guardian": prescription["diagnosis_user_input"],
        "symptom_notes": prescription.get("symptom_notes"),
        "medications": meds,
        "home_care_candidates": items,
    }
    text = json.dumps(ctx, ensure_ascii=False, indent=2)
    if re.search(r"\d{6}-[\d*]{7}", text):  # 개인정보가 섞여 들어가지 않았는지 마지막 확인
        raise ValueError("Context에 주민번호 형식이 들어 있어요")
    return text


# ================================================================== 3. 코드 규칙으로 채우는 부분
SLOTS = {1: ["아침"], 2: ["아침", "저녁"], 3: ["아침", "점심", "저녁"], 4: ["아침", "점심", "저녁", "자기 전"]}
SLOT_ORDER = ["아침", "점심", "저녁", "자기 전"]
SLOT_WORDS = {
    "아침": "아침",
    "점심": "점심",
    "저녁": "저녁",
    "취침": "자기 전",
    "자기전": "자기 전",
    "잠들기전": "자기 전",
}
# 복용 시점: 위에 있을수록 우선 (식후 즉시가 식후 30분보다 먼저 걸려야 한다)
TIMING_WORDS = ["식후즉시", "식후2시간", "식전30분", "식전", "수유후30분", "수유후", "식후30분", "식후"]
TIMING_LABEL = {
    "식후즉시": "식후 즉시",
    "식후2시간": "식후 2시간",
    "식전30분": "식전 30분",
    "식전": "식전",
    "수유후30분": "수유 후 30분",
    "수유후": "수유 후",
    "식후30분": "식후 30분",
    "식후": "식후",
}


def load(name: str) -> dict:
    return json.loads((TEMPLATE_DIR / name).read_text(encoding="utf-8"))


def slots_from_usage(usage: str | None, daily_count: int | None) -> list[str] | None:
    """용법 문구에 시간대 단어가 있고 그 개수가 하루 횟수와 맞으면 그 시간대를 쓴다. 아니면 None."""
    text = re.sub(r"\s", "", usage or "")
    found = {slot for word, slot in SLOT_WORDS.items() if word in text}
    slots = [s for s in SLOT_ORDER if s in found]
    return slots if slots and daily_count and len(slots) == daily_count else None


def timing_from_usage(usage: str | None) -> str | None:
    text = re.sub(r"\s", "", usage or "")
    return next((TIMING_LABEL[w] for w in TIMING_WORDS if w in text), None)


def schedule_of(m: dict) -> dict:
    n = int(m["daily_count"]) if m.get("daily_count") is not None else None
    if m.get("as_needed"):
        t, slots = "as_needed", ["필요할 때"]
    elif m.get("dosage_form") == "점안액":
        t, slots = "eye", slots_from_usage(m.get("usage"), n) or []
    elif m.get("route") == "외용":
        t, slots = "topical", slots_from_usage(m.get("usage"), n) or SLOTS.get(n or 0, [])  # noqa: C901
    else:
        t, slots = "fixed", slots_from_usage(m.get("usage"), n) or SLOTS.get(n or 0, [])
    return {
        "type": t,
        "daily_count": None if m.get("as_needed") else n,
        "max_daily_count": int(m["max_daily_count"]) if m.get("max_daily_count") else None,
        "min_interval_hours": (m.get("min_interval_h") or interval_hours(m.get("usage")))
        if m.get("as_needed")
        else None,
        "timing": None if m.get("as_needed") else timing_from_usage(m.get("usage")),
        "total_days": _fmt(m.get("total_days")),
        "slots": slots,
        "usage_original": m.get("usage"),
    }


def dose_text(m: dict) -> str:
    if m.get("dose_per_time") is None:
        return "환부에 얇게" if m.get("route") == "외용" else "처방전 확인"
    return f"1회 {_fmt(m['dose_per_time'])}{m.get('unit') or ''}"


FORM_IS_LIQUID = {"시럽", "건조시럽", "현탁액", "액제"}
# 알레르기 → 약 확인 규칙. LLM이 판단하지 않고, 여기 적힌 짝에 맞을 때만 코드가 약사 확인을 켠다.
# (알레르기 입력에 든 단어, 성분 key(merge.ingredient_of 결과), 약 이름에 든 단어, 보호자에게 보일 이유)
# 의료진·약사 검수 전 초안. 짝을 늘릴 때는 출처를 함께 적는다.
ALLERGY_RULES: list[tuple[tuple[str, ...], frozenset[str], tuple[str, ...], str]] = [
    (("계란", "달걀", "난백"), frozenset(), ("리소짐",), "달걀 흰자에서 얻은 성분(리소짐)이 들어 있을 수 있어요"),
    (
        ("페니실린", "아목시실린"),
        frozenset({"amoxicillin", "amoxicillin/clavulanate"}),
        ("아목시실린", "오구멘틴"),
        "페니실린 계열 항생제예요",
    ),
]


def allergy_flags(allergies: list[str], medications: list[dict]) -> dict[int, str]:
    """ALLERGY_RULES에 맞는 약 → {medication_id: 약사 확인 이유}. 규칙에 없는 조합은 추측하지 않는다."""
    flags: dict[int, str] = {}
    for words, ingredients, name_words, why in ALLERGY_RULES:
        hit = [a for a in allergies if any(w in a for w in words)]
        if not hit:
            continue
        for m in medications:
            names = f"{m.get('name') or ''} {m.get('name_on_prescription') or ''}"
            if m.get("ingredient") in ingredients or any(w in names for w in name_words):
                flags.setdefault(m["medication_id"], f"{', '.join(hit)} 알레르기: {why}")
    return flags


# 숫자가 고정된 일반 간격 문장 → 해당 약 계열. 처방 용법에 간격이 있으면 이 문장은 붙이지 않는다.
INTERVAL_TIP_CLASS = {"apap.interval": "antipyretic_apap", "ibu.interval": "antipyretic_ibu"}
DISEASE_GROUPS = {"cold_bronchitis", "otitis_sinusitis", "enteritis", "dermatitis", "conjunctivitis"}
GROUP_KO = {
    "cold_bronchitis": "감기·기관지염",
    "otitis_sinusitis": "중이염·부비동염",
    "enteritis": "장염",
    "dermatitis": "아토피·피부염",
    "conjunctivitis": "결막염",
    "other": "기타",
}
VERB_BY_FORM = {
    "크림": "발랐나요",
    "연고": "발랐나요",
    "로션": "발랐나요",
    "흡입제": "흡입했나요",
    "비강분무제": "뿌렸나요",
    "점안액": "넣었나요",
    "점이액": "넣었나요",
    "좌제": "넣었나요",
}


def age_band(m: int) -> str:
    """연령대: 생활 안내의 방향을 나누는 기준 (영아 0세, 유아 1~6세, 학령기 7~12세, 청소년 13세 이상)."""
    return "영아" if m < 12 else "유아" if m < 84 else "학령기" if m < 156 else "청소년"


CLASS_KO = {
    "antipyretic_apap": "해열제",
    "antipyretic_ibu": "해열제",
    "antibiotic": "항생제",
    "probiotic": "정장제",
    "antidiarrheal": "지사제",
    "antihistamine": "항히스타민제",
    "cough_expectorant": "기침·가래약",
    "topical_steroid": "스테로이드 연고",
    "eye_drop": "안약",
}


def _short(name: str, n: int = 18) -> str:
    """화면용 짧은 약 이름: 괄호 속 성분을 빼고 길면 자른다."""
    name = re.sub(r"\([^)]*\)", "", name).strip() or name
    return name if len(name) <= n else name[: n - 1] + "…"


# 관리 포인트의 행동 문장 → 체크하는 문장 ("~주세요." → "~줬나요?")
_ASK = [
    ("주세요.", "줬나요?"),
    ("보세요.", "봤나요?"),
    ("받으세요.", "받았나요?"),
    ("씻으세요.", "씻었나요?"),
    ("하세요.", "했나요?"),
    ("마세요.", "않았나요?"),
]


def _i_ga(word: str) -> str:
    """받침이 있으면 '이', 없으면 '가'."""
    c = word[-1]
    return "이" if "가" <= c <= "힣" and (ord(c) - 0xAC00) % 28 else "가"


def as_check(action: str) -> str:
    for a, b in _ASK:
        if action.endswith(a):
            return action[: -len(a)] + b
    return action


def pick_focus_points(
    group: str, age_m: int, med_classes: dict[str, list[str]], symptoms: str, focus_tpl: dict
) -> list[dict]:
    """오늘의 관리 포인트 최대 3개 (생활 관리만). 점수 = 기본 순서 + 처방 약 계열(+2) + 보호자 입력 증상(+3).
    각 포인트에 '왜 이 아이에게 이것을 골랐는지'(reason_for_child)를 코드가 적는다."""
    groups = focus_tpl.get("groups", {})
    own = [(it, False) for it in groups.get(group, [])]
    common = [(it, True) for it in groups.get("common", [])]
    scored = []
    for idx, (it, is_common) in enumerate(own + common):
        if not usable(it, age_m):
            continue
        score, reasons = -idx * 0.01, []
        hit_sym = [k for k in it.get("symptom_keywords", []) if k in symptoms]
        if hit_sym:
            score += 3
            reasons.append(f"보호자가 입력한 증상({', '.join(hit_sym)})과 관련 있어요")
        hit_med = list(dict.fromkeys(CLASS_KO.get(c, c) for c in it.get("boost_classes", []) if med_classes.get(c)))
        if hit_med:
            score += 2
            joined = "·".join(hit_med)
            reasons.append(f"오늘 처방에 {joined}{_i_ga(joined)} 있어 함께 챙기면 좋아요")
        if not reasons:
            reasons.append(
                "모든 아이에게 공통으로 안내하는 항목이에요"
                if is_common
                else f"{GROUP_KO.get(group, group)} 관리 수칙에 있는 항목이에요"
            )
        scored.append((score, it, " · ".join(reasons)))
    scored.sort(key=lambda x: -x[0])
    return [
        {
            "id": it["id"],
            "title": it["title"],
            "why": it["why"],
            "actions": it["actions"][:3],
            "reason_for_child": why_child,
            "source": it["source"],
            "_needs_review": it.get("needs_review", False),
        }
        for _, it, why_child in scored[:3]
    ]


def build_checklist(meds_out: list[dict], focus: list[dict]) -> list[dict]:
    """오늘 체크리스트: 막연한 문장 대신 '무엇을 몇 번' 했는지 확인하는 행동 목표. 숫자는 처방 그대로."""
    items = []
    for m in meds_out[:5]:
        s, name = m["schedule"], _short(m["name"])
        if s["type"] == "as_needed":
            gap = f" ({s['min_interval_hours']}시간 이상 간격)" if s.get("min_interval_hours") else ""
            text = f"{name}: 먹였다면 시각 적어 두기{gap}"
        else:
            verb = VERB_BY_FORM.get(m["dosage_form"], "먹였나요")
            slots = "·".join(x for x in s["slots"] if x != "필요할 때")
            count = f"{s['daily_count']}번 " if s.get("daily_count") else ""
            text = f"{name}: {slots + ' ' if slots else ''}{count}{verb}?"
        items.append({"text": text[:60], "category": "복약"})
    for f in focus[:2]:
        items.append({"text": as_check(f["actions"][0])[:60], "category": "생활"})
    items.append({"text": "축 늘어지거나 숨쉬기 힘들어하지 않는지 살펴봤나요?", "category": "관찰"})
    return items


def assemble(  # noqa: C901
    child: dict,
    prescription: dict,
    medications: list[dict],
    llm: LLMGuideOutput | None,  # noqa: C901
    disease_group: str,
    home_care_template: dict,
    rule_flags: dict[int, str] | None = None,
    record: dict | None = None,
    llm_label: str = "LLM",
) -> dict:
    """LLM 결과와 DB·템플릿을 합쳐 guide_content(JSON Schema v0.3)를 만든다. llm=None이면 fallback."""
    common, tips = load("DATA-REF-006_common.json"), load("DATA-REF-007_med_tips.json")
    focus_tpl = load("DATA-REF-006_focus.json") if (TEMPLATE_DIR / "DATA-REF-006_focus.json").exists() else {}
    rule_flags = dict(rule_flags or {})
    # 알레르기 규칙 이유를 앞에 둔다 (화면에 80자까지만 보이므로 가장 중요한 것을 먼저)
    for mid, why in allergy_flags(child.get("allergies") or [], medications).items():
        rule_flags[mid] = "; ".join(r for r in (why, rule_flags.get(mid)) if r)
    age_m = child["age_months"]
    symptoms = (prescription.get("symptom_notes") or "").strip()
    used: dict[str, set] = {}  # 출처 id → 어디에 쓰였는지
    review_count = 0

    def use(src: str, purpose: str, needs_review: bool = False) -> None:
        nonlocal review_count
        used.setdefault(src, set()).add(purpose)
        review_count += 1 if needs_review else 0

    # ---------- 약 카드 (복약 안내)
    by_id = {x.medication_id: x for x in (llm.medications if llm else [])}
    meds_out: list[dict] = []
    med_classes: dict[str, list[str]] = {}
    rx_interval: dict[str, bool] = {}  # 약 계열 → 그 계열 약 모두 처방 용법에 간격이 있는지
    for m in medications:
        x = by_id.get(m["medication_id"])
        need = (x.pharmacist_check_needed if x else True) or m["medication_id"] in rule_flags
        # 코드 규칙 이유(처방전·약봉투 불일치 등)를 앞에, LLM 이유(알레르기·성분 중복 등)를 뒤에 둔다. 같은 말은 한 번만.
        if x is None:
            llm_reason = "자동 설명을 만들지 못했어요"
        else:
            llm_reason = x.pharmacist_check_reason if x.pharmacist_check_needed else None
        reason = "; ".join(dict.fromkeys(r for r in (rule_flags.get(m["medication_id"]), llm_reason) if r))
        cautions = x.cautions if x else ([m["pharmacy_caution"]] if m.get("pharmacy_caution") else [])
        meds_out.append(
            {
                "medication_id": m["medication_id"],
                "name": m["name"],
                "dosage_form": m.get("dosage_form") or "기타",
                "route": m.get("route") or "내복",
                "dose_text": dose_text(m),
                "schedule": schedule_of(m),
                "purpose": x.purpose if x else "처방받은 약이에요",
                "how_to_give": x.how_to_give if x else ["처방전과 약봉투에 적힌 대로 먹이거나 사용하세요."],
                "cautions": cautions,
                "common_side_effects": x.common_side_effects if x else [],
                "storage": m.get("storage") or (x.storage if x else None),  # 약봉투 보관법이 있으면 그것이 우선
                "pharmacist_check": {"needed": bool(need), "reason": ((reason or "")[:80] or None) if need else None},
            }
        )
        cls = tips["ingredient_to_class"].get(m.get("ingredient") or "")
        if cls:
            med_classes.setdefault(cls, []).append(_short(m["name"], 12))
            has_gap = bool(m.get("min_interval_h") or interval_hours(m.get("usage")))
            rx_interval[cls] = rx_interval.get(cls, True) and has_gap
        if m.get("has_pharmacy_info"):
            use("PHARMACY_BAG", "약 설명")

    # ---------- 이번 약과 함께 챙길 것 (약 이야기는 모두 여기로: 복약/생활 경계)
    with_med, seen = [], set()

    def add_tip(item: dict, src_purpose: str = "약 계열 팁") -> None:
        if rx_interval.get(INTERVAL_TIP_CLASS.get(item["id"], "")):
            return  # 처방 용법에 간격이 있으면 숫자 고정 간격 문장은 빼고, 처방 숫자(필요시 안내·복용법 표)만 보여 준다
        if item["id"] not in seen and item.get("source") != "TODO_SOURCE" and not item.get("disabled"):
            seen.add(item["id"])
            with_med.append({"template_item_id": item["id"], "text": item["text"]})
            use(item["source"], src_purpose, item.get("needs_review", False))

    for cls in med_classes:
        for item in tips["classes"].get(cls, []):
            add_tip(item)
    if any(m.get("dosage_form") in FORM_IS_LIQUID for m in medications):
        for item in tips["dosage_form_tips"]["liquid"]:
            add_tip(item)
    for item in tips["classes"]["common"]:
        add_tip(item)

    # ---------- 생활 안내 (집에서 돌보기): 템플릿에 있는 id만, 약 관련 문장(kind=medication)은 복약 쪽으로 보낸다
    all_items = [(s_, i) for s_ in home_care_template.get("sections", []) for i in s_["items"]]
    item_index = {i["id"]: (s_, i) for s_, i in all_items if usable(i, age_m)}
    excluded_by_age = sum(
        1 for _, i in all_items if not i.get("disabled") and i.get("source") != "TODO_SOURCE" and not usable(i, age_m)
    )
    picks = llm.home_care_picks if llm else [LLMHomeCarePick(template_item_id=k) for k in item_index]
    sections: dict[str, dict] = {}
    for p in picks:
        if p.template_item_id not in item_index:
            continue  # 템플릿 밖 문장은 버린다
        s_, i = item_index[p.template_item_id]
        if i.get("kind") == "medication":
            add_tip(i, "약 관련 안내")
            continue
        sec = sections.setdefault(s_["key"], {"key": s_["key"], "title": s_["title"], "items": []})
        sec["items"].append({"template_item_id": i["id"], "text": i["text"], "personal_note": p.personal_note})
        use(i["source"], "생활 안내", i.get("needs_review", False))

    # ---------- 오늘의 관리 포인트 (생활 관리 3개, 코드가 고름)
    focus = pick_focus_points(disease_group, age_m, med_classes, symptoms, focus_tpl)
    for f in focus:
        use(f["source"], "관리 포인트", f.pop("_needs_review"))

    # ---------- 위험 신호·나이별 주의 (템플릿 복사)
    warning = {}
    for k in ("go_to_er", "see_doctor"):
        # 공통 위험 신호도 나이 조건(min_months·max_months)에 맞는 것만 (예: 3개월 미만 발열 문장은 영아에게만)
        ws = [w for w in common["warning_signs"][k] if usable(w, age_m)] + [
            w for w in home_care_template.get("extra_warning_signs", {}).get(k, []) if usable(w, age_m)
        ]
        warning[k] = [w["text"] for w in ws]
        for w in ws:
            use(w["source"], "위험 신호", w.get("needs_review", False))
    age_items = [
        a for a in common["age_notes"] if a["min_months"] <= age_m <= a["max_months"] and a["source"] != "TODO_SOURCE"
    ]
    for a in age_items:
        use(a["source"], "나이별 주의", a.get("needs_review", False))

    checklist = build_checklist(meds_out, focus)

    # ---------- 생성 근거: 아이 정보가 가이드에 어떻게 쓰였는지 (모두 코드가 사실대로 적음)
    weight = child.get("weight_kg")
    allergies = child.get("allergies") or []
    prn = sum(1 for m in medications if m.get("as_needed"))
    personalization = [
        {
            "factor": "나이",
            "value": f"{age_text(age_m)} ({age_band(age_m)})",
            "applied": f"나이에 맞는 생활 안내만 골랐어요 (나이 조건으로 {excluded_by_age}개 제외). 나이별 주의 {len(age_items)}개를 붙였어요.",
        },
        {
            "factor": "체중",
            "value": f"{weight}kg" if weight else "입력 안 됨",
            "applied": "약 용량은 처방 그대로이며 체중으로 다시 계산하지 않아요. 해열제 양은 체중 기준이라, 체중이 바뀌면 약사에게 확인하세요.",
        },
        {
            "factor": "알레르기",
            "value": ", ".join(allergies) if allergies else "없음",
            "applied": "검수한 성분-알레르기 규칙에 맞는 약에 약사 확인을 켜고, 약을 받을 때 알레르기를 알리도록 안내해요.",
        },
        {
            "factor": "보호자 입력 증상",
            "value": symptoms or "입력 안 됨",
            "applied": "증상과 관련된 관리 포인트를 먼저 보여 줘요."
            if symptoms
            else "증상을 입력하면 관련된 관리 포인트를 먼저 보여 줘요.",
        },
        {
            "factor": "처방 약",
            "value": f"{len(medications)}종" + (f" (필요할 때 먹는 약 {prn}종)" if prn else ""),
            "applied": "약 계열에 맞는 팁을 붙이고, 관리 포인트 순서에 반영했어요.",
        },
    ]
    rec = record or {}
    basis = {
        "documents": rec.get("documents", []),
        "diagnosis_codes": rec.get("diagnosis_codes", []),
        "cross_check": rec.get(
            "cross_check", {"done": False, "mismatch_count": 0, "summary": "처방전·약봉투 교차 확인을 거치지 않았어요"}
        ),
        "personalization": personalization,
    }

    # ---------- 검증 정보와 출처
    verification = {
        "generated_by": llm_label if llm else "기본 가이드 (AI 설명 없이 템플릿과 처방 정보만 사용)",
        "template_review": home_care_template.get("review_status") or common.get("review_status", "확인 안 됨"),
        "needs_review_count": review_count,
        "checks": [
            "약 이름·용량·횟수·일수는 처방 그대로 넣었어요 (AI가 바꿀 수 없음)",
            "생활 안내는 출처가 있는 템플릿 문장에서만 골랐어요 (템플릿 밖 문장은 버림)",
            "위험 신호와 나이별 주의는 AI를 거치지 않고 템플릿에서 그대로 넣었어요",
            basis["cross_check"]["summary"],
        ],
    }
    all_src = {
        **home_care_template.get("sources", {}),
        **common["sources"],
        **tips["sources"],
        **focus_tpl.get("sources", {}),
        "PHARMACY_BAG": {"title": "약봉투의 약국 복약 안내 (조제 약국 작성, OCR로 읽음)", "url": None},
    }
    sources = [
        {"id": k, "title": all_src[k]["title"], "url": all_src[k].get("url"), "used_for": ", ".join(sorted(v))}
        for k, v in used.items()
        if k in all_src and k != "TODO_SOURCE"
    ]

    return {
        "schema_version": "0.3",
        "prescription_id": prescription["prescription_id"],
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds"),
        "status": "ok" if llm else "fallback",
        "child": {
            "age_text": age_text(age_m),
            "age_months": age_m,
            "age_band": age_band(age_m),
            "weight_kg": weight,
            "allergies": allergies,
        },
        "diagnosis_label": prescription["diagnosis_user_input"],
        "disease_group": disease_group,
        "symptom_notes": symptoms or None,
        "summary": llm.summary
        if llm
        else f"{age_text(age_m)} 아이의 오늘 처방 약 {len(medications)}가지와 집에서 챙길 것을 정리했어요.",
        "focus_points": focus,
        "medications": meds_out,
        "with_this_medicine": with_med,
        "home_care": {
            "template_id": home_care_template.get("template_id", "none"),
            "sections": list(sections.values()),
        },
        "warning_signs": warning,
        "age_notes": [a["text"] for a in age_items],
        "today_checklist": checklist,
        "basis": basis,
        "verification": verification,
        "disclaimer": DISCLAIMER,
        "sources": sources,
    }


# ================================================================== 4. 호출 + 재시도 + fallback
# call_llm(system, user): JSON 문자열 또는 dict를 돌려주는 함수. 실패하면 ValueError(LLMCallError 포함)를 낸다.
CallLLM = Callable[[str, str], str | dict[str, Any]]


def _shorten(text: str, limit: int) -> str:
    """limit자 안으로. 문장 끝('요.' 등)에서 자를 수 있으면 거기서, 아니면 잘라서 '…'."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("요."), cut.rfind("다."))
    return cut[: end + 2].strip() if end >= limit // 2 else text[: limit - 1] + "…"


def parse_llm_output(raw: str | dict) -> LLMGuideOutput:
    """LLM 답 → LLMGuideOutput. 글자 수만 넘긴 칸은 그 칸만 줄여서 받는다.

    다른 형식 오류(빠진 칸·잘못된 타입·개수 초과)는 그대로 ValidationError — generate()가 다시 시도한다.
    한 문장이 몇 글자 길다고 가이드 전체를 fallback으로 버리지 않기 위해서다.
    """
    data = json.loads(raw) if isinstance(raw, str) else raw
    try:
        return LLMGuideOutput.model_validate(data)
    except ValidationError as e:
        errors = e.errors()
        if not errors or any(err["type"] != "string_too_long" for err in errors):
            raise
        data = json.loads(json.dumps(data))  # 원본은 바꾸지 않는다
        for err in errors:
            *path, last = err["loc"]
            node = data
            for key in path:
                node = node[key]
            node[last] = _shorten(node[last], err["ctx"]["max_length"])
            logger.warning(
                "LLM 답의 %s가 %d자를 넘어 줄였어요", ".".join(map(str, err["loc"])), err["ctx"]["max_length"]
            )
        return LLMGuideOutput.model_validate(data)


def generate(
    call_llm: CallLLM,
    child: dict,
    prescription: dict,
    medications: list[dict],
    references: dict[int, str],
    disease_group: str,
    rule_flags: dict[int, str] | None = None,
    retries: int = 1,
    record: dict | None = None,
    llm_label: str = "LLM",
) -> dict:
    """가이드 1건 생성. 동기 함수이므로 FastAPI에서는 anyio.to_thread.run_sync로 부른다.

    call_llm(system, user) -> str(JSON) 또는 dict. 실서비스는 llm_client.call_haiku를 넣는다.
    LLM 호출이 실패하거나 답이 형식에 맞지 않으면 retries번 다시 시도하고, 그래도 안 되면 fallback 가이드를 돌려준다.

    child: 자녀 프로필(birth_date 포함). 나이는 prescription["prescription_date"](처방일, 없으면 오늘) 기준으로 다시 계산한다.
    medications·rule_flags·references·record: merge_documents() 결과 (S-04에서 보호자가 확정한 것).
    llm_label: 가이드의 '검증 정보'에 적을 생성 방식 (예: "Claude Haiku (claude-haiku-5-5)").
    """
    child = prepare_child(child, prescription.get("prescription_date"))
    if disease_group not in DISEASE_GROUPS or not (TEMPLATE_DIR / f"DATA-REF-006_{disease_group}.json").exists():
        disease_group = "other"  # 천식·변비·외상 등 템플릿이 없는 질환 → 공통 위험 신호·나이별 주의만 쓴다
    tpl = (
        {"template_id": "none", "sections": []}
        if disease_group == "other"
        else load(f"DATA-REF-006_{disease_group}.json")
    )
    user = build_context(child, prescription, medications, references, tpl)
    ids = {m["medication_id"] for m in medications}
    out: LLMGuideOutput | None = None
    for attempt in range(retries + 1):
        try:
            raw = call_llm(SYSTEM_PROMPT, user)
            parsed = parse_llm_output(raw)
            got = [x.medication_id for x in parsed.medications]
            if set(got) != ids or len(got) != len(ids):
                raise ValueError(f"약 목록이 처방과 다름: 받은 {sorted(got)}, 처방 {sorted(ids)}")
            out = parsed
            break
        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            logger.warning("가이드 LLM 시도 %d/%d 실패: %s", attempt + 1, retries + 1, e)
    if out is None:
        logger.warning("LLM 답을 쓰지 못해 기본 가이드(fallback)로 만들어요")
    return assemble(child, prescription, medications, out, disease_group, tpl, rule_flags, record, llm_label)
