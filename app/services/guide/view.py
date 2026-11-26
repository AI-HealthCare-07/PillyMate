"""가이드 결과(generator v0.3)를 프론트 화면 형식으로 바꾼다.

프론트(frontend/src/components/rx/guide.jsx)가 읽는 키를 맨 위에 둔다.
    schedule  : [{"slot": "아침", "items": [["세파클러", "4.2mL", "5일"], ...]}, ...]  → Schedule
    asNeeded  : "세토펜: 필요할 때 1회 5mL. ..." (없으면 "")                           → Schedule 아래 한 줄
    howTo     : [{"name", "how", "note", ...}]                                         → HowTo
                기존 화면용: name·how·note
                카드 윗부분: shortName·purpose·dose·when·keyPoint
                자세히 보기: steps·cautions·sideEffects·storage·pharmacistCheck·form
    life      : [문장, ...]                                                              → LifeTips
    danger    : [문장, ...]                                                              → DangerSignals
그 밖에 title·summary·checklist·disclaimer·sources를 두고,
원래 결과 전체는 detail에 넣어 둔다 (챗봇·근거 화면에서 쓸 수 있게).
"""

from __future__ import annotations

import re
from typing import Any

from app.services.guide.generator import SLOT_ORDER

VIEW_SCHEMA_VERSION = "fe-1"
MAX_LIFE = 8


def short_name(name: str, n: int = 18) -> str:
    """괄호 속 성분·규격을 빼고, 길면 자른다. 예: '세파클러건조시럽(내복)/60(1)mL/병' → '세파클러건조시럽'."""
    base = re.split(r"[(/]", name, maxsplit=1)[0].strip() or name
    return base if len(base) <= n else base[: n - 1] + "…"


def _dose(dose_text: str) -> str:
    return dose_text.removeprefix("1회 ").strip()


def _days(schedule: dict) -> str | None:
    days = schedule.get("total_days")
    return f"{days}일" if days else None


def build_schedule(medications: list[dict]) -> list[dict]:
    """시간대(아침·점심·저녁·자기 전)마다 그때 먹는 약을 모은다. 필요시 약은 여기 넣지 않는다."""
    by_slot: dict[str, list[list[str]]] = {s: [] for s in SLOT_ORDER}
    for m in medications:
        s = m["schedule"]
        if s["type"] == "as_needed":
            continue
        item = [short_name(m["name"]), _dose(m["dose_text"])]
        days = _days(s)
        if days:
            item.append(days)
        for slot in s.get("slots") or []:
            if slot in by_slot:
                by_slot[slot].append(item)
    return [{"slot": slot, "items": items} for slot, items in by_slot.items() if items]


def build_as_needed(medications: list[dict]) -> str:
    """필요할 때 먹는 약 안내 한 줄. 여러 개면 줄바꿈으로 잇는다."""
    lines = []
    for m in medications:
        s = m["schedule"]
        if s["type"] != "as_needed":
            continue
        text = f"{short_name(m['name'])}: 필요할 때만 {m['dose_text']}."
        if s.get("min_interval_hours"):
            text += f" 다음 번까지 {s['min_interval_hours']}시간 넘게 띄워 주세요."
        if s.get("max_daily_count"):
            text += f" 하루 {s['max_daily_count']}번을 넘기지 마세요."
        lines.append(text)
    return "\n".join(lines)


def build_how_to(medications: list[dict]) -> list[dict]:
    out = []
    for m in medications:
        how = " ".join([m["purpose"].rstrip(".") + "."] + list(m.get("how_to_give") or []))
        notes = list(m.get("cautions") or [])
        check = m.get("pharmacist_check") or {}
        if check.get("needed") and check.get("reason"):
            notes.append(f"약사 확인 필요: {check['reason']}")
        out.append(
            {
                # 예전 화면용 (그대로 둠)
                "name": m["name"],
                "how": how.strip(),
                "note": " ".join(notes),
                # 약 카드 자세히 보기용 — 화면이 이 값이 있으면 이것을 보여 줘요
                "purpose": m.get("purpose"),
                "steps": list(m.get("how_to_give") or []),
                "cautions": list(m.get("cautions") or []),
                "sideEffects": list(m.get("common_side_effects") or []),
                "storage": m.get("storage"),
                "pharmacistCheck": check.get("reason") if check.get("needed") else None,
                "form": m.get("dosage_form"),
                "route": m.get("route"),
            }
        )
    return out


def build_life(guide: dict) -> list[str]:
    """약과 함께 챙길 것 → 관리 포인트 행동 → 집에서 돌보기 순서로, 겹치지 않게 MAX_LIFE개까지."""
    texts: list[str] = [t["text"] for t in guide.get("with_this_medicine") or []]
    for f in guide.get("focus_points") or []:
        texts.extend(f.get("actions") or [])
    for sec in (guide.get("home_care") or {}).get("sections") or []:
        texts.extend(i["text"] for i in sec.get("items") or [])
    seen: set[str] = set()
    out = []
    for t in texts:
        if t and t not in seen:
            seen.add(t)
            out.append(t)
    return out[:MAX_LIFE]


def build_danger(guide: dict) -> list[str]:
    w = guide.get("warning_signs") or {}
    return [f"바로 응급실: {t}" for t in w.get("go_to_er") or []] + [
        f"진료 필요: {t}" for t in w.get("see_doctor") or []
    ]


def to_view(guide: dict[str, Any]) -> dict[str, Any]:
    meds = guide.get("medications") or []
    return {
        "schema_version": VIEW_SCHEMA_VERSION,
        "status": guide.get("status"),
        "title": guide.get("diagnosis_label"),
        "summary": guide.get("summary"),
        "schedule": build_schedule(meds),
        "asNeeded": build_as_needed(meds),
        "howTo": build_how_to(meds),
        "life": build_life(guide),
        "danger": build_danger(guide),
        "checklist": [c["text"] for c in guide.get("today_checklist") or []],
        "disclaimer": guide.get("disclaimer"),
        "sources": guide.get("sources") or [],
        "detail": guide,
    }
