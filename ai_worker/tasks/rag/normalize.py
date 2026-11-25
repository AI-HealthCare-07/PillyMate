"""약 이름 정규화 — 체크리스트 생성과 매칭이 같은 규칙을 쓰도록 한 곳에 둔다."""

import re

# 함량 표기: 125mg, 6mg/mL, 0.1%, 250mg/5mL 등
_STRENGTH = re.compile(r"\d+(\.\d+)?\s*(mg|g|ml|mcg|μg|iu|%)(\s*/\s*\d*(\.\d+)?\s*(ml|g))?", re.I)
# 괄호 안 내용: (아세트아미노펜), [수출명] 등
_BRACKETS = re.compile(r"[\(\[（【].*?[\)\]）】]")
_SPACES = re.compile(r"[\s_\-·.,/]+")


def normalize_name(name: str | None) -> str:
    """'챔프시럽(아세트아미노펜) 32mg/mL' → '챔프시럽'"""
    if not name:
        return ""
    s = _BRACKETS.sub("", str(name))
    s = _STRENGTH.sub("", s)
    s = _SPACES.sub("", s)
    return s.lower()


def bracket_text(name: str | None) -> str:
    """괄호 안 글자 (성분이 적혀 있는 경우가 많음). '챔프시럽(아세트아미노펜)' → '아세트아미노펜'"""
    if not name:
        return ""
    m = re.search(r"[\(（](.*?)[\)）]", str(name))
    return m.group(1).strip() if m else ""
