"""약 정보 문서가 없는 약의 초안 만들기: 식약처 허가 상세정보 + DUR 연령금기 + e약은요 → LLM 쉬운 말 초안 → 사람 검수.

    uv run --no-sync --env-file .env python scripts/rag/draft_refs_from_permit.py \\
        --medication data/sample/medication_from_ocr.csv
    ... --dry-run   # 무엇을 만들지 목록만 보기 (API·LLM 부르지 않음)
    ... --no-llm    # API 원문만 받아 검수 시트에 쓰기 (초안 칸은 비움, drug_refs.json은 그대로)
    ... --limit 3   # 처방 많은 약부터 3개만

흐름
  1) 약 목록을 실제 가이드와 같은 경로로 넣어 reference를 못 찾은 약을 고른다
  2) 허가 CSV로 그 약의 성분과 대표 품목을 찾는다. 성분이 같은 약은 한 번만 (처방 많은 순)
     drug_refs.json에 같은 성분 항목이 이미 있으면(review 포함) 건너뛴다
  3) 허가 상세 API(품목기준코드) → 효능·주의사항 단락 (app/services/guide/permit_document_sections.py)
     DUR 특정연령대금기 API(품목기준코드) → 연령 금기 문장 (원문 그대로 dur_age_taboo에 둔다)
     e약은요 API → 쉬운 말 효능·주의·부작용·보관 (app/services/guide/easy_drug_info_fields.py)
       - 대표 품목이 e약은요에 있으면 그 품목 것
       - 없으면(전문의약품은 대부분 없음) 단일 성분일 때 성분 이름으로 찾아, 허가 CSV로 성분이 똑같다고
         확인된 일반의약품 것을 '같은 성분 일반의약품'으로 표시해 넣는다
  4) Claude Haiku로 보호자용 쉬운 말 초안 (원문에 있는 것만, 용량 금지)
  5) drug_refs.json에 status "review"로 추가하고, 검수 시트(md)에 원문과 초안을 나란히 쓴다
     → 사람이 원문과 대조해 고치고 status를 "done"으로 바꿔야 가이드에 쓰인다 (review는 가이드에 안 들어감)

API 키 (.env, app/core/config.py. 키는 출력하지 않는다): MFDS_API_KEY(허가 상세·DUR), DATA_GO_KR_KEY(e약은요)
API 호출은 app/services/guide/mfds_drug_info_api.py를 가이드 생성과 함께 쓴다.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.core import config  # noqa: E402
from app.services.guide.drug_reference import DEFAULT_PATH as REFS_PATH  # noqa: E402
from app.services.guide.drug_reference import DrugRefIndex  # noqa: E402
from app.services.guide.easy_drug_info_fields import EasyDrugInfo, easy_drug_info  # noqa: E402
from app.services.guide.mfds_drug_info_api import (  # noqa: E402
    MfdsApiError,
    fetch_dur_age_taboo,
    fetch_easy_drug,
    fetch_permit_document,
    search_easy_drugs,
)
from app.services.guide.permit_document_sections import PermitDocument  # noqa: E402
from app.services.guide.permit_ingredient_index import (  # noqa: E402
    IngredientSet,
    PermitIngredientIndex,
    PermitItem,
    default_permit_index,
    form_word,
    representative_item,
)
from app.services.guide.service import normalize_medication  # noqa: E402

NEDRUG_URL = "https://nedrug.mfds.go.kr/pbp/CCBBB01/getItemDetail?itemSeq={}"
SOURCE_NAME = "식약처 의약품 제품 허가정보 상세(효능효과·사용상의 주의사항) + DUR 특정연령대금기 (API)"
EASY_SOURCE_NAME = " + 의약품개요정보(e약은요)"
DEFAULT_REVIEW_SHEET = ROOT / "data" / "review" / "drug_refs_draft_review.md"
STYLE_EXAMPLE_KEY = "세노바액"  # 검수 끝난 항목 하나를 문체 예시로 LLM에 보여 준다

DRAFT_SYSTEM = """너는 소아 보호자용 약 안내 문장을 쓰는 약사 보조야. 식약처 허가 문서 원문을 쉬운 말 요약 초안으로 바꿔.
초안은 약사가 원문과 대조해 검수한 뒤에만 쓰인다.

[규칙]
1. 원문에 있는 내용만 쓴다. 원문에 없으면 그 칸은 빈 문자열("")로 둔다. 짐작해서 채우지 않는다.
2. 용량·횟수·사용 기간·mg/kg 같은 용법 숫자는 쓰지 않는다. 나이 조건 숫자(예: "12세 미만")와 보관 온도는 써도 된다.
3. 읽는 사람은 0~18세 아이의 보호자다. 성인에게만 해당하는 내용(임신·수유, 고령자, 운전·기계 조작, 음주)은 뺀다.
4. 해요체, 짧은 문장. 전문 용어는 쉬운 말로 바꾸되 뜻을 바꾸지 않는다.
5. 칸별 길이를 꼭 지킨다: efficacy 80자, cautions 250자(가장 중요한 것부터 최대 5문장), side_effects 100자, storage 60자 이내.
   길이를 넘기면 덜 중요한 내용을 뺀다. 한글로만 쓴다 (한자 금지).
6. cautions 우선순위: 아이에게 먹이면 안 되는 경우(나이 금기 포함) → 경고 → 소아 투여 주의 → 이럴 땐 멈추고 상담.
   DUR 연령 금기가 있으면 반드시 cautions 맨 앞에 쉬운 말로 넣는다.
7. side_effects는 흔한 것 위주로, 단어를 쉼표로 나열한다.
8. 원문에서 판단이 애매했던 점은 reviewer_note에 적는다 (예: "소아 투여 단락이 없음", "제형별 차이 확인 필요").
9. [e약은요 …] 줄은 식약처가 일반의약품을 쉬운 말로 설명한 글이다. 표현은 참고하되, 허가 문서와 다르면 허가 문서를 따른다.
   '같은 성분 일반의약품'이라고 표시된 e약은요는 다른 제품이라, 성분에 대한 내용만 참고하고
   효능 범위·제형·보관 방법은 가져오지 않는다.
10. evidence에 근거를 적는다. efficacy·cautions·storage는 문장마다 하나씩, side_effects는 칸 전체를 하나로.
   source에는 원문 줄 맨 앞 [ ] 안의 이름을 그대로 쓴다 (예: "소아 투여", "이상반응", "DUR 연령 금기", "e약은요 주의").
   근거 칸을 댈 수 없는 문장은 쓰지 않는다."""

DRAFT_TOOL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "efficacy": {"type": "string", "description": "무슨 약인지 한 문장 (…약이에요)"},
        "cautions": {"type": "string", "description": "보호자가 알아야 할 주의"},
        "side_effects": {"type": "string", "description": "흔한 부작용, 쉼표로 나열"},
        "storage": {"type": "string", "description": "보관 방법"},
        "reviewer_note": {"type": "string", "description": "검수자에게 남길 말"},
        "evidence": {
            "type": "array",
            "description": "초안 문장마다 원문의 어느 칸에서 왔는지",
            "items": {
                "type": "object",
                "properties": {
                    "field": {"type": "string", "enum": ["efficacy", "cautions", "side_effects", "storage"]},
                    "sentence": {"type": "string", "description": "초안 문장 그대로 (side_effects는 칸 전체)"},
                    "source": {"type": "string", "description": "원문 줄 맨 앞 [ ] 안의 이름"},
                },
                "required": ["field", "sentence", "source"],
            },
        },
    },
    "required": ["efficacy", "cautions", "side_effects", "storage", "reviewer_note", "evidence"],
}
TEXT_FIELDS = ("efficacy", "cautions", "side_effects", "storage", "reviewer_note")
SENTENCE_FIELDS = ("efficacy", "cautions", "storage")  # 문장마다 근거가 있어야 하는 칸
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
FIELD_LIMITS = {"efficacy": 80, "cautions": 250, "side_effects": 100, "storage": 60}
_HANJA = re.compile(r"[\u4e00-\u9fff]")
_DOSE_LIKE = re.compile(r"\d+(\.\d+)?\s*(mg|㎎|ml|㎖|mcg|g|정|포|캡슐|회|방울|주|일간|일분)", re.I)
SECTION_LABELS = {
    "warning": "경고",
    "contraindication": "투여 금기",
    "child": "소아 투여",
    "stop_signs": "중지하고 상담할 때",
    "side_effects": "이상반응",
    "general": "일반 주의",
    "storage": "보관·취급",
}


@dataclass
class DraftTarget:
    ingredients: IngredientSet
    item: PermitItem  # 대표 품목 (이 품목의 허가 문서로 초안을 만든다)
    prescribed_names: list[str]  # 이 성분으로 처방된 이름 (처방 많은 순)
    count: int  # 측정 목록에서 처방된 횟수


@dataclass
class DraftSources:
    """초안 1개의 원문 묶음."""

    doc: PermitDocument  # 허가 문서 (대표 품목)
    age_taboo: str = ""  # DUR 특정연령대금기 문장
    easy: EasyDrugInfo | None = None  # e약은요
    easy_same_product: bool = False  # e약은요가 대표 품목 자신의 것인지 (아니면 같은 성분 일반의약품)


# (대상, 원문 묶음, LLM 초안 또는 None, 자동 점검 문제)
DraftRow = tuple[DraftTarget, DraftSources, dict[str, Any] | None, list[str]]


# ------------------------------------------------------------------ 1)·2) 초안 만들 약 고르기


def find_targets(medication_csv: Path) -> tuple[list[DraftTarget], list[str]]:
    """(초안을 만들 성분 목록, 허가 CSV에서 성분을 못 찾은 약 이름)"""
    with medication_csv.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    permit = default_permit_index()
    refs = DrugRefIndex(permit=permit)
    all_entries = json.loads(REFS_PATH.read_text(encoding="utf-8"))["drugs"]
    covered = {permit.by_seq[e["item_seq"]].ingredients for e in all_entries if e.get("item_seq") in permit.by_seq}

    targets: dict[IngredientSet, DraftTarget] = {}
    names_by_set: dict[IngredientSet, Counter[str]] = {}
    unresolved: Counter[str] = Counter()
    for i, r in enumerate(rows, 1):
        med = normalize_medication(
            {"medication_id": i, "name": r.get("name"), "insurance_code": r.get("insurance_code") or None}
        )
        doc, _ = refs.find(med)
        if doc:
            continue
        ingredients, items, _ = permit.lookup(med)
        if not ingredients:
            unresolved[med["name"]] += 1
            continue
        if ingredients in covered:
            continue
        names_by_set.setdefault(ingredients, Counter())[med["name"]] += 1
        if ingredients not in targets:
            item = representative_item(items or permit.by_ingredients.get(ingredients, []), ingredients, med["name"])
            if item:
                targets[ingredients] = DraftTarget(ingredients, item, [], 0)
    for s, t in targets.items():
        t.prescribed_names = [n for n, _ in names_by_set[s].most_common()]
        t.count = sum(names_by_set[s].values())
    ordered = sorted(targets.values(), key=lambda t: -t.count)
    return ordered, [n for n, _ in unresolved.most_common()]


# ------------------------------------------------------------------ 3) 식약처 API


def check_keys() -> bool:
    """허가·DUR 키가 없으면 끝낸다. (e약은요를 쓸 수 있는지)"""
    if not config.MFDS_API_KEY:
        sys.exit(".env에 MFDS_API_KEY가 없어요. --env-file .env를 붙였는지도 확인해 주세요.")
    if not config.DATA_GO_KR_KEY:
        print("DATA_GO_KR_KEY가 없어 e약은요는 MFDS_API_KEY로 시도해요.")
    return True


def fetch_easy_same_ingredient(
    client: httpx.Client, target: DraftTarget, permit: PermitIngredientIndex
) -> EasyDrugInfo | None:
    """대표 품목이 e약은요에 없을 때: 성분 이름으로 찾아 허가 CSV로 성분이 똑같은 일반의약품 1개. 복합제는 찾지 않는다."""
    if len(target.ingredients) != 1:
        return None
    items = search_easy_drugs(client, next(iter(target.ingredients)))
    same = [
        it for it in items if (p := permit.by_seq.get(str(it.get("itemSeq")))) and p.ingredients == target.ingredients
    ]
    form = form_word(target.item.item_name)
    pick = next((it for it in same if form and form_word(str(it.get("itemName"))) == form), None) or next(
        iter(same), None
    )
    info = easy_drug_info(pick) if pick else None
    return info if info and not info.is_empty() else None


def fetch_easy(
    client: httpx.Client, target: DraftTarget, permit: PermitIngredientIndex
) -> tuple[EasyDrugInfo | None, bool]:
    """(e약은요, 대표 품목 자신의 것인지). 오류가 나도 초안은 허가 문서만으로 계속 만든다."""
    try:
        own = fetch_easy_drug(client, target.item.item_seq)
        if own:
            return own, True
        return fetch_easy_same_ingredient(client, target, permit), False
    except (MfdsApiError, httpx.HTTPError) as e:
        print(f"  [e약은요 오류, 건너뜀] {target.item.item_name}: {e}")
        return None, False


# ------------------------------------------------------------------ 4) LLM 초안


def source_text(src: DraftSources) -> str:
    doc = src.doc
    parts = [f"[제품] {doc.item_name}", f"[효능효과] {doc.efficacy or '(없음)'}"]
    if src.age_taboo:
        parts.append(f"[DUR 연령 금기] {src.age_taboo}")
    for cat, label in SECTION_LABELS.items():
        if doc.sections.get(cat):
            parts.append(f"[{label}] {doc.sections[cat]}")
    parts.append(f"[저장방법] {doc.storage_method or '(없음)'}")
    if src.easy:
        whose = "같은 제품" if src.easy_same_product else f"같은 성분 일반의약품 {src.easy.item_name}"
        parts += [f"[e약은요 {label} ({whose})] {text}" for label, text in src.easy.sections.items()]
    return "\n".join(parts)


def style_example() -> str:
    data = json.loads(REFS_PATH.read_text(encoding="utf-8"))
    d = next((d for d in data["drugs"] if d["key"] == STYLE_EXAMPLE_KEY), None)
    if not d:
        return ""
    fields = {k: d.get(k, "") for k in ("efficacy", "cautions", "side_effects", "storage")}
    return "검수가 끝난 항목의 문체 예시 (내용은 참고하지 말고 문체만):\n" + json.dumps(fields, ensure_ascii=False)


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_END.split(text or "") if s.strip()]


def _squash(text: str) -> str:
    return re.sub(r"[\s.,·!?]", "", text or "")


def _label(text: str) -> str:
    """'e약은요 주의 (같은 제품)' → 'e약은요주의'. 근거 칸 이름을 비교할 때 괄호·띄어쓰기는 보지 않는다."""
    return _squash(re.sub(r"\(.*?\)", "", text or ""))


def source_labels(src: DraftSources) -> set[str]:
    """원문 줄 맨 앞 [ ] 안의 이름들 (비교용)."""
    return {_label(line.split("]")[0][1:]) for line in source_text(src).split("\n")}


def evidence_for(draft: dict[str, Any], field: str, sentence: str) -> dict | None:
    """초안 문장 1개의 근거 항목. 문장이 서로 들어 있으면 같은 것으로 본다 (띄어쓰기·문장부호 무시)."""
    s = _squash(sentence)
    for ev in draft.get("evidence") or []:
        e = _squash(ev.get("sentence", ""))
        if ev.get("field") == field and s and e and (s in e or e in s):
            return ev
    return None


def evidence_problems(draft: dict[str, Any], labels: set[str]) -> list[str]:
    """문장마다 근거가 있는지, 근거 칸 이름이 원문에 있는지."""
    problems = []
    for field in SENTENCE_FIELDS:
        for s in sentences(draft.get(field, "")):
            if not evidence_for(draft, field, s):
                problems.append(f"{field} 문장에 근거 표시가 없어요: '{s[:30]}'")
    if draft.get("side_effects") and not any(ev.get("field") == "side_effects" for ev in draft.get("evidence") or []):
        problems.append("side_effects에 근거 표시가 없어요")
    bad = sorted(
        {ev.get("source", "") for ev in draft.get("evidence") or [] if _label(ev.get("source", "")) not in labels}
    )
    if bad:
        problems.append(f"원문에 없는 근거 칸 이름: {', '.join(bad)}")
    return problems


def draft_problems(draft: dict[str, Any], labels: set[str] | None = None) -> list[str]:
    """초안을 기계로 점검: 길이 초과, 한자 섞임, 용법 숫자로 보이는 표현, 근거 표시."""
    problems = []
    for field, limit in FIELD_LIMITS.items():
        text = draft.get(field, "")
        if len(text) > limit:
            problems.append(f"{field}가 {len(text)}자예요 ({limit}자 이내로)")
        if _HANJA.search(text):
            problems.append(f"{field}에 한자가 섞였어요")
        if m := _DOSE_LIKE.search(text):
            problems.append(f"{field}에 용법 숫자로 보이는 표현이 있어요: '{m.group(0)}'")
    if labels is not None:
        problems += evidence_problems(draft, labels)
    return problems


def _ask_llm(user: str) -> dict[str, Any]:
    from app.services.guide.llm_client import call_tool  # ANTHROPIC_API_KEY가 필요할 때만 불러온다

    out = call_tool(
        DRAFT_SYSTEM,
        [{"role": "user", "content": user}],
        "submit_drug_ref_draft",
        "보호자용 약 정보 초안 제출",
        DRAFT_TOOL_SCHEMA,
        max_tokens=3000,  # 근거 표시까지 받으니 넉넉하게
    )
    draft: dict[str, Any] = {k: str(out.get(k) or "").strip() for k in TEXT_FIELDS}
    draft["evidence"] = [ev for ev in out.get("evidence") or [] if isinstance(ev, dict)]
    return draft


def draft_with_llm(src: DraftSources) -> tuple[dict[str, Any], list[str]]:
    """(초안, 남은 자동 점검 문제). 점검에 걸리면 문제를 알려 주고 1번 더 쓰게 한다."""
    user = f"{style_example()}\n\n아래 원문으로 초안을 써.\n\n{source_text(src)}"
    labels = source_labels(src)
    draft = _ask_llm(user)
    problems = draft_problems(draft, labels)
    if problems:
        retry = (
            f"{user}\n\n[이전 초안]\n{json.dumps(draft, ensure_ascii=False)}\n\n"
            f"[고칠 점]\n- " + "\n- ".join(problems) + "\n규칙을 지켜 다시 제출해."
        )
        draft = _ask_llm(retry)
        problems = draft_problems(draft, labels)
    return draft, problems


# ------------------------------------------------------------------ 5) 저장


def short_key(item_name: str) -> str:
    """'유시락스시럽(히드록시진염산염)' → '유시락스시럽'"""
    return re.split(r"[\(（]", item_name)[0].strip() or item_name


def ref_entry(src: DraftSources, raw: dict, draft: dict[str, Any], problems: list[str]) -> dict:
    from app.services.guide.llm_client import LLM_LABEL

    doc, today = src.doc, date.today().isoformat()
    source: dict[str, Any] = {"name": SOURCE_NAME, "url": NEDRUG_URL.format(doc.item_seq), "checked_at": today}
    if src.easy:
        source["name"] += EASY_SOURCE_NAME
        source["easy_drug"] = {
            "item_seq": src.easy.item_seq,
            "item_name": src.easy.item_name,
            "same_product": src.easy_same_product,
        }
    return {
        "key": short_key(doc.item_name),
        "names": [doc.item_name],
        "ingredient": str(raw.get("MAIN_INGR_ENG") or "").strip().lower(),
        "dosage_forms": [f] if (f := form_word(doc.item_name)) else [],  # 경로 확인(내복·외용)에 쓴다
        "item_seq": doc.item_seq,
        "efficacy": draft["efficacy"],
        "cautions": draft["cautions"],
        "side_effects": draft["side_effects"],
        "storage": draft["storage"],
        "dur_age_taboo": src.age_taboo,
        "source": source,
        "status": "review",
        "match_basis": "ingredient",
        "review_note": f"{LLM_LABEL} 초안({today}). 검수 시트의 원문과 대조해 고친 뒤 done으로 바꾸기. "
        + (f"[자동 점검] {' / '.join(problems)}. " if problems else "")
        + f"LLM 메모: {draft['reviewer_note'] or '-'}",
    }


DRAFT_FIELD_NAMES = {"efficacy": "효능", "cautions": "주의", "side_effects": "흔한 부작용", "storage": "보관"}


def _with_source(draft: dict[str, Any], field: str, text: str) -> str:
    ev = evidence_for(draft, field, text)
    return f"{text} ← [{ev['source']}]" if ev else f"{text} ⚠ 근거 표시 없음"


def draft_lines(draft: dict[str, Any]) -> list[str]:
    """검수 시트의 초안 줄. 문장마다 근거 칸을 붙인다."""
    out = []
    for field, name in DRAFT_FIELD_NAMES.items():
        text = draft.get(field, "")
        if not text:
            out.append(f"- **{name}** (없음)")
        elif field == "side_effects":
            ev = next((e for e in draft.get("evidence") or [] if e.get("field") == field), None)
            out.append(f"- **{name}** {text}" + (f" ← [{ev['source']}]" if ev else " ⚠ 근거 표시 없음"))
        else:
            out.append(f"- **{name}**")
            out += [f"  - {_with_source(draft, field, s)}" for s in sentences(text)]
    return out


def review_sheet(rows: list[DraftRow], unresolved: list[str]) -> str:
    out = [
        "# 약 정보 초안 검수 시트",
        "",
        f"`scripts/rag/draft_refs_from_permit.py`가 {date.today().isoformat()}에 만들었어요.",
        "원문(식약처 허가 문서·DUR·e약은요)과 초안을 대조해 `app/data/drug_refs.json`의 해당 항목을 고치고 `status`를 `done`으로 바꿔 주세요.",
        "**`review` 상태 항목은 가이드에 쓰이지 않아요.** 용법·용량은 넣지 않아요 (NFR-SAFE-002).",
        "",
        "- 초안 문장 뒤의 `← [칸 이름]`은 LLM이 그 문장을 가져왔다고 표시한 원문 칸이에요. 그 칸만 펼쳐서 대조하면 돼요.",
        "- `⚠ 근거 표시 없음`인 문장은 원문 어디서 왔는지 LLM이 대지 못한 문장이에요. 특히 확인해 주세요.",
        "- 원문은 식약처 허가 문서에서 고른 단락을 자르지 않고 그대로 실었어요 (상호작용·임부·고령자·과량투여·용법용량은 뺌).",
        "",
    ]
    for t, src, draft, problems in rows:
        doc = src.doc
        out += [
            f"## {short_key(doc.item_name)} — {', '.join(sorted(t.ingredients))}",
            "",
            f"- 품목: {doc.item_name} (품목기준코드 [{doc.item_seq}]({NEDRUG_URL.format(doc.item_seq)}))",
            f"- 처방된 이름 ({t.count}건): {', '.join(t.prescribed_names)}",
            "",
        ]
        if draft:
            out += ["### 초안", "", *draft_lines(draft), f"- **LLM 메모** {draft['reviewer_note'] or '-'}"]
            out += [f"- **자동 점검** {' / '.join(problems)}"] if problems else []
            out += [""]
        lines = source_text(src).split("\n")
        out += [
            f"<details><summary>원문 ({sum(len(x) for x in lines):,}자)</summary>",
            "",
            *[f"- **{line.split(']')[0][1:]}** {line.split(']', 1)[1].strip()}" for line in lines],
            "",
            "</details>",
            "",
        ]
    if unresolved:
        out += ["## 허가 CSV에서 성분을 못 찾은 약 (초안 못 만듦)", "", *[f"- {n}" for n in unresolved], ""]
    return "\n".join(out)


def save_entries(entries: list[dict]) -> None:
    data = json.loads(REFS_PATH.read_text(encoding="utf-8"))
    have = {e.get("item_seq") for e in data["drugs"]}
    data["drugs"].extend(e for e in entries if e["item_seq"] not in have)
    # 원래 파일 모양(들여쓰기 2칸, 끝 줄바꿈 없음)을 지켜야 기존 항목이 diff에 안 잡힌다
    REFS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def make_drafts(targets: list[DraftTarget], use_llm: bool) -> tuple[list[DraftRow], list[dict]]:
    """대상마다 원문(허가 문서·DUR·e약은요)을 받고 LLM 초안을 만든다. (검수 시트 줄, drug_refs.json에 넣을 항목)"""
    check_keys()
    permit = default_permit_index()
    rows: list[DraftRow] = []
    entries: list[dict] = []
    with httpx.Client(timeout=30) as client:
        for t in targets:
            doc, raw = fetch_permit_document(client, t.item.item_seq)
            if not doc or doc.is_empty():
                print(f"  [허가 문서 없음] {t.item.item_name}")
                continue
            src = DraftSources(doc, fetch_dur_age_taboo(client, t.item.item_seq))
            src.easy, src.easy_same_product = fetch_easy(client, t, permit)
            draft, problems = draft_with_llm(src) if use_llm else (None, [])
            rows.append((t, src, draft, problems))
            if draft:
                entries.append(ref_entry(src, raw, draft, problems))
            notes = [n for n, on in [("DUR 연령 금기", src.age_taboo), ("e약은요", src.easy)] if on]
            print(f"  [완료] {doc.item_name}" + (f" ({', '.join(notes)})" if notes else ""))
            time.sleep(0.2)  # 공공 API에 부담을 덜 주게
    return rows, entries


def main() -> None:
    ap = argparse.ArgumentParser(description="허가 문서로 약 정보 초안(status: review) 만들기")
    ap.add_argument("--medication", type=Path, default=ROOT / "data" / "sample" / "medication_from_ocr.csv")
    ap.add_argument("--limit", type=int, help="처방 많은 성분부터 이만큼만")
    ap.add_argument("--dry-run", action="store_true", help="목록만 보기 (API·LLM 부르지 않음)")
    ap.add_argument("--no-llm", action="store_true", help="원문만 받아 검수 시트에 쓰기 (drug_refs.json은 그대로)")
    ap.add_argument("--review-sheet", type=Path, default=DEFAULT_REVIEW_SHEET)
    args = ap.parse_args()

    targets, unresolved = find_targets(args.medication)
    if args.limit:
        targets = targets[: args.limit]
    print(f"초안 만들 성분 {len(targets)}개, 허가 CSV에서 성분을 못 찾은 약 {len(unresolved)}개")
    for t in targets:
        print(f"  {t.count:>3}건  {', '.join(sorted(t.ingredients))}  ← {t.item.item_name} ({t.item.item_seq})")
    if args.dry_run:
        for n in unresolved:
            print(f"  [성분 못 찾음] {n}")
        return

    rows, entries = make_drafts(targets, use_llm=not args.no_llm)
    args.review_sheet.parent.mkdir(parents=True, exist_ok=True)
    args.review_sheet.write_text(review_sheet(rows, unresolved), encoding="utf-8")
    print(f"검수 시트: {args.review_sheet.relative_to(ROOT)}")
    if entries:
        save_entries(entries)
        print(
            f"drug_refs.json에 status 'review'로 {len(entries)}개 추가했어요. 검수 뒤 done으로 바꿔야 가이드에 쓰여요."
        )


if __name__ == "__main__":
    main()
