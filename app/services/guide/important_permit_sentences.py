"""허가 문서 단락 → 보호자 안내에 중요한 문장만 골라 글자 수 안으로 (가이드의 '검수 전 정보' 요약용).

앞에서부터 자르면 안 되는 이유: 이상반응 단락은 앞부분이 임상시험 통계('2,646명 이상의 성인…')라
정작 '소아에서 가장 빈번하게 보고된 이상반응은 구토였다' 같은 문장이 잘려 나간다.

고르는 방법
  1) 단락을 문장·번호 항목('1) …')으로 나눈다. 맨 앞 단락 제목('4. 이상반응:')은 뗀다
  2) 용법·용량 숫자가 든 문장('40 mg/kg', '1일 2회')은 버린다 (NFR-SAFE-002)
  3) 점수를 매긴다: 소아·나이 조건·금기·'가장 빈번/흔하게'는 올리고, 임상시험 통계·표는 내린다
  4) 점수 높은 순으로 글자 수 안에 들어가는 만큼 고르고, 원래 순서대로 이어 붙인다
"""

from __future__ import annotations

import re
from typing import Literal

Kind = Literal["side_effects", "caution"]

_TITLE = re.compile(r"^\s*\d+\.\s*[^:：]{1,40}[:：]\s*")  # '4. 이상반응: '
# 문장 끝('…다.', '…함.'), 번호 항목('1) ', '③ ') 앞에서 나눈다.
# '가. 나.' 항목 기호로는 나누지 않는다 — '…투여할 것. '의 '것.'도 같은 모양이라 문장이 잘린다.
_SPLIT = re.compile(r"(?<=[.。])\s+|\s+(?=\d+\)\s)|\s+(?=[①-⑳])|(?<=다\.)(?=\S)")
_LIST_MARK = re.compile(r"^(?:[가-하]\.|[①-⑳])\s*$")  # 항목 기호만 남은 조각
_TABLE = re.compile(r"표\s*\d")
MIN_UNIT_CHARS = 6
_DOSE = re.compile(
    r"\d+(?:\.\d+)?\s*(?:mg|㎎|g|mL|ml|㎖|mcg|μg|IU)\s*(?:/\s*kg)?|1일\s*\d+\s*회|\d+\s*회\s*투여|mg/kg",
    re.I,
)
_CHILD = ("소아", "어린이", "영아", "유아", "신생아", "청소년")
_AGE = re.compile(r"\d+\s*(?:세|개월|주)\s*(?:미만|이하|이상)")
_STRONG = ("투여하지 말", "금기", "사망", "호흡억제", "중단", "즉시", "경련", "이상행동", "아나필락시스", "과민")
_COMMON = ("가장 빈번", "가장 흔", "흔하게", "흔한", "자주", "빈번하게", "매우 흔함")
_STATS = (
    "임상시험",
    "대상으로",
    "명 이상",
    "명을",
    "명의",
    "위약",
    "대조",
    "n=",
    "MedDRA",
    "빈도 분류",
    "표 ",
    "외삽",
    "약동학",
    "통계",
    "%",
    "평가하였다",
    "재심사",
    "시판 후",
    "조사결과",
)


def units(text: str) -> list[str]:
    """단락 → 문장·번호 항목 목록. 맨 앞 단락 제목은 뗀다."""
    body = _TITLE.sub("", text or "", count=1)
    out: list[str] = []
    seen: set[str] = set()
    for u in _SPLIT.split(body):
        u = (u or "").strip()
        key = re.sub(r"\s", "", u)
        if len(u) < MIN_UNIT_CHARS or _LIST_MARK.match(u) or key in seen:  # 조각·항목 기호·같은 문장 반복은 뺀다
            continue
        seen.add(key)
        out.append(u)
    return out


def score(unit: str, kind: Kind) -> int:
    s = 0
    s += 2 if any(w in unit for w in _CHILD) else 0
    s += 2 if _AGE.search(unit) else 0
    s += 2 if any(w in unit for w in _STRONG) else 0
    if kind == "side_effects":
        s += 3 if any(w in unit for w in _COMMON) else 0
    s -= 3 * min(2, sum(w in unit for w in _STATS) + bool(_TABLE.search(unit)))
    return s


def pick_important(text: str, limit: int, kind: Kind = "caution") -> str:
    """중요한 문장을 limit자 안으로 골라 원래 순서로 잇는다. 고를 문장이 없으면 ''."""
    parts = [u for u in units(text) if not _DOSE.search(u)]
    if not parts:
        return ""
    ranked = sorted(range(len(parts)), key=lambda i: (-score(parts[i], kind), i))
    chosen: list[int] = []
    used = 0
    for i in ranked:
        if score(parts[i], kind) < 0 and chosen:
            break  # 통계 문장은 다른 문장이 하나도 없을 때만
        cost = len(parts[i]) + 1
        if used + cost <= limit:
            chosen.append(i)
            used += cost
    if not chosen:  # 제일 중요한 문장 하나도 limit보다 길면 그 문장을 잘라서라도 쓴다
        first = parts[ranked[0]]
        return first[: limit - 1] + "…"
    return " ".join(parts[i] for i in sorted(chosen))
