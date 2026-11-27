"""처방전 OCR + 약봉투 OCR 합치기와 교차 확인 (S-04 확인 단계에서 사용).

AI-2 guide_module.py v0.3의 0번 섹션을 옮긴 파일. 가이드 생성 전에 BE가 먼저 부른다.
"""

from __future__ import annotations

import datetime as dt
import difflib
import re
import unicodedata
from typing import Any, Literal

Level = Literal["error", "warn", "info"]


def _issue(level: Level, target: str, message: str) -> dict:
    return {"level": level, "target": target, "message": message}


def _num(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _same(a: Any, b: Any) -> bool:
    a, b = _num(a), _num(b)
    return a is not None and b is not None and abs(a - b) < 1e-3


def _norm_name(name: str) -> str:
    """약 이름 비교용: 괄호·규격(/ 뒤)·염 이름을 빼고 밀리그램 표기를 mg로 맞춘다."""
    s = re.sub(r"\([^()]*\)", "", name or "")
    s = s.split("/")[0]
    for a in ("밀리그램", "밀리그림", "밀리그"):
        s = s.replace(a, "mg")
    s = re.sub(r"(염산염|말레산염|황산염|인산염|나트륨)", "", s)
    return re.sub(r"\s", "", s).lower()


def _clean_usage(usage: str | None) -> str | None:
    if not usage:
        return None
    return re.sub(r"^[\s\-·>]+", "", usage).strip() or None


# 제형·경로: 약 이름의 단어로 정한다. 위에 있을수록 우선.
FORM_RULES = [  # (이름에 든 단어, 스키마 dosage_form, route, 기본 단위)
    ("점안", "점안액", "외용", "방울"),
    ("이용액", "점이액", "외용", "방울"),
    ("나잘스프레이", "비강분무제", "외용", "분무"),
    ("할러", "흡입제", "외용", "흡입"),
    ("네뷸", "흡입제", "외용", "관"),
    ("레스풀", "흡입제", "외용", "관"),
    ("레스플", "흡입제", "외용", "관"),
    ("좌약", "좌제", "외용", "개"),
    ("크림", "크림", "외용", None),
    ("연고", "연고", "외용", None),
    ("로션", "로션", "외용", None),
    ("건조시럽", "건조시럽", "내복", "mL"),
    ("건조사립", "건조시럽", "내복", "mL"),
    ("드라이시럽", "산제", "내복", "g"),
    ("현탁액", "현탁액", "내복", "mL"),
    ("시럽", "시럽", "내복", "mL"),
    ("세립", "산제", "내복", "g"),
    ("산", "산제", "내복", "포"),
    ("캡슐", "캡슐", "내복", "캡슐"),
    ("츄정", "정제", "내복", "정"),
    ("정", "정제", "내복", "정"),
]
TOPICAL_NO_DOSE = {"크림", "연고", "로션"}  # 1회량 숫자가 의미 없는 외용제 → "환부에 적당량"


def _form_of(rx_name: str) -> tuple[str | None, str, str | None]:
    base = _norm_name(rx_name)
    for key, form, route, unit in FORM_RULES:
        if key in base:
            return form, route, unit
    return None, "내복", None


def _unit_from_rx_name(rx_name: str) -> str | None:
    """처방전 이름 끝의 포장 단위(/1포, /1정 …)에서 단위를 읽는다."""
    m = re.search(r"/1(포|정|캡슐|개|관|g)$", rx_name or "")
    return m.group(1) if m else None


def interval_hours(*texts: str | None) -> int | None:
    """약봉투 주의사항 등에서 '간격 4시간' 같은 복용 간격을 읽는다. 추측하지 않는다."""
    for t in texts:
        # "간격 4시간" / "4시간 간격" / "4~6시간 간격" / "6시간 이상 간격" → 적힌 가장 짧은 간격(4, 6)
        m = re.search(r"간격\s*(\d+)\s*시간", t or "") or re.search(
            r"(\d+)\s*(?:~\s*\d+\s*)?시간\s*(?:이상\s*)?간격", t or ""
        )
        if m:
            return int(m.group(1))
    return None


# 약 이름에 왼쪽 단어가 들어 있으면 오른쪽 성분으로 본다. 위에서부터 처음 맞는 줄을 쓴다.
# 이름이 겹치는 것은 더 구체적인 쪽을 위에 둔다. (예: 덱시부프로펜 > 이부프로펜, 레보세티리진 > 세티리진)
# 주석 형식: [성분명] 또는 [상품명] + 한글 성분 · 약 종류
INGREDIENT_RULES = [
    ("덱시부프로펜", "dexibuprofen"),  # [성분명] 덱시부프로펜 · 해열진통소염제 ('이부프로펜'보다 위에 둬야 함)
    ("맥시부펜", "dexibuprofen"),  # [상품명] 맥시부펜시럽 = 덱시부프로펜
    ("이부프로펜", "ibuprofen"),  # [성분명] 이부프로펜 · 해열진통소염제
    ("이부펜", "ibuprofen"),  # [상품명 일부] 챔프이부펜 등 = 이부프로펜 ('챔프'보다 위에 둬야 함)
    ("부루펜", "ibuprofen"),  # [상품명] 부루펜시럽 = 이부프로펜
    ("아세트아미노펜", "acetaminophen"),  # [성분명] 아세트아미노펜 · 해열진통제
    ("세토펜", "acetaminophen"),  # [상품명] 세토펜현탁액 = 아세트아미노펜
    ("써스펜", "acetaminophen"),  # [상품명] 써스펜좌약 = 아세트아미노펜 (좌약)
    ("챔프", "acetaminophen"),  # [상품명] 챔프시럽 = 아세트아미노펜
    ("암브록솔", "ambroxol"),  # [성분명] 암브록솔 · 거담제(가래)
    ("뮤코펙트", "ambroxol"),  # [상품명] 뮤코펙트시럽·정 = 암브록솔
    ("레보드로프로피진", "levodropropizine"),  # [성분명] 레보드로프로피진 · 진해제(기침)
    ("사카로", "saccharomyces boulardii"),  # [성분명 앞부분] 사카로마이세스 보울라디 · 정장제
    ("비오플", "saccharomyces boulardii"),  # [상품명] 비오플250산 = 사카로마이세스 보울라디
    ("세프디니르", "cefdinir"),  # [성분명] 세프디니르 · 항생제
    ("옴니세프", "cefdinir"),  # [상품명] 옴니세프세립 = 세프디니르
    ("세파클러", "cefaclor"),  # [성분명] 세파클러 · 항생제 (세파클러건조시럽처럼 성분명이 곧 약 이름)
    ("클래리스로마이신", "clarithromycin"),  # [성분명] 클래리스로마이신 · 항생제
    ("클래리시드", "clarithromycin"),  # [상품명] 클래리시드건조시럽 = 클래리스로마이신
    # [성분명] 클라불란산이 이름에 있으면 아목시실린·클라불란산 복합제 · 항생제
    ("클라불란산", "amoxicillin/clavulanate"),
    ("오구멘틴", "amoxicillin/clavulanate"),  # [상품명] 오구멘틴 = 아목시실린·클라불란산 복합제
    ("오구엔틴", "amoxicillin/clavulanate"),  # OCR 오타 ('오구멘틴'을 잘못 읽은 것)
    ("아목시실린", "amoxicillin"),  # [성분명] 아목시실린 단독 · 항생제 (위 셋에 안 걸릴 때만)
    ("레보세티리진", "levocetirizine"),  # [성분명] 레보세티리진 · 항히스타민제 ('세티리진'보다 위에 둬야 함)
    ("세티리진", "cetirizine"),  # [성분명] 세티리진 · 항히스타민제(콧물·가려움)
    ("히드록시진", "hydroxyzine"),  # [성분명] 히드록시진 · 항히스타민제(가려움)
    ("유시락스", "hydroxyzine"),  # [상품명] 유시락스시럽 = 히드록시진
    # [성분명] 히드로코르티손부티레이트 · 바르는 스테로이드제 (히드로코르티손보다 센 다른 성분. '히드로코르티손'보다 위에 둬야 함)
    ("히드로코르티손부티레이트", "hydrocortisone butyrate"),
    ("로코이드", "hydrocortisone butyrate"),  # [상품명] 로코이드크림 = 히드로코르티손부티레이트
    ("히드로코르티손", "hydrocortisone"),  # [성분명] 히드로코르티손 · 바르는 스테로이드제
    ("토브라마이신", "tobramycin"),  # [성분명] 토브라마이신 · 항생 점안제
    ("토브렉스", "tobramycin"),  # [상품명] 토브렉스점안액 = 토브라마이신
    ("레보플록사신", "levofloxacin"),  # [성분명] 레보플록사신 · 항생 점안제
    ("러보플록사신", "levofloxacin"),  # OCR 오타 ('레보플록사신'을 잘못 읽은 것)
    ("크라비트", "levofloxacin"),  # [상품명] 크라비트점안액 = 레보플록사신
    ("플루오로메톨론", "fluorometholone"),  # [성분명] 플루오로메톨론 · 스테로이드 점안제
    ("플루메토론", "fluorometholone"),  # [상품명] 플루메토론점안액 = 플루오로메톨론
]


def ingredient_of(*names: str | None) -> str | None:
    """처방전 이름(괄호 속 성분 포함)과 약봉투 이름에서 성분을 찾는다. 모르면 None (추측하지 않음)."""
    text = unicodedata.normalize("NFC", " ".join(n for n in names if n))
    return next((key for word, key in INGREDIENT_RULES if word in text), None)


def _clean_bag_text(t: str | None) -> str | None:
    """약봉투 OCR 문장 정리: 앞쪽 잡음 문자 제거, 줄바꿈으로 갈라진 '약입니 다.' 같은 끝말 붙이기."""
    if not t:
        return None
    t = re.sub(r"^[^가-힣A-Za-z0-9\[]+", "", t).strip()
    t = re.sub(r"(\S)\s+(다|요|세요)\.", r"\1\2.", t)
    return t or None


def _pair_bag_items(rx_meds: list[dict], bag_meds: list[dict]) -> dict[int, int]:
    """처방전 약 index → 약봉투 약 index. 이름 유사도에 숫자 일치 가점을 더해 큰 것부터 짝짓는다."""
    scores = []
    for i, r in enumerate(rx_meds):
        for j, b in enumerate(bag_meds):
            s = difflib.SequenceMatcher(None, _norm_name(r["명칭"]), _norm_name(b["명칭"])).ratio()
            if _same(r.get("1회투약량"), b.get("1회용량")):
                s += 0.2
            if _same(r.get("총투약일수"), b.get("일수")):
                s += 0.1
            scores.append((s, i, j))
    pairs, used_i, used_j = {}, set(), set()
    for s, i, j in sorted(scores, reverse=True):
        if s < 0.6 or i in used_i or j in used_j:
            continue
        pairs[i] = j
        used_i.add(i)
        used_j.add(j)
    return pairs


def _birth_from_rrn(rrn: str | None) -> dt.date | None:
    """주민번호 앞 6자리 + 성별자리(1·2 → 1900년대, 3·4 → 2000년대)로 생년월일. 뒷자리가 가려져 있으면 2000년대로 본다."""
    m = re.match(r"(\d{2})(\d{2})(\d{2})-?([0-9*])", rrn or "")
    if not m:
        return None
    century = 1900 if m.group(4) in "12" else 2000
    try:
        return dt.date(century + int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def merge_documents(rx: dict, bag: dict | None, child_profile: dict | None = None) -> dict:  # noqa: C901
    """처방전 OCR + 약봉투 OCR → 확정 전 약 목록 + 확인 결과.

    반환값
      ok           : error가 하나도 없으면 True. False면 가이드를 만들지 말고 S-04에서 보호자에게 확인받는다.
      medications  : build_context()/assemble()이 받는 모양의 약 목록 (medication_id는 1부터 임시 번호)
      rule_flags   : {medication_id: 약사 확인 이유} → generate(rule_flags=...)로 넘긴다
      issues       : 확인 단계에서 찾은 문제 목록 [{level, target, message}] → S-04 화면에 보여 줄 수 있다
    """
    issues: list[dict] = []
    rule_flags: dict[int, str] = {}
    rx_meds = rx.get("처방의약품") or []
    bag_meds = (bag or {}).get("약품") or []
    receipt = {r["명칭"]: r for r in ((bag or {}).get("영수증") or {}).get("약품내역") or []}

    # ---------- 확인 1: 문서 단위 (같은 처방인지, 같은 아이인지)
    if bag is None:
        issues.append(_issue("info", "문서", "약봉투가 없어 처방전만으로 정리했어요."))
    else:
        info = bag.get("복약안내") or {}
        rx_no = (rx.get("교부일") or "").replace("-", "") + (rx.get("교부번호") or "")
        if info.get("교부번호") and rx_no and info["교부번호"] != rx_no:
            issues.append(
                _issue(
                    "error",
                    "문서",
                    f"처방전({rx_no})과 약봉투({info['교부번호']})의 교부번호가 달라요. 같은 처방인지 확인이 필요해요.",
                )
            )
        rx_name, bag_name = (rx.get("환자") or {}).get("성명"), (info.get("환자") or {}).get("성명")
        if rx_name and bag_name and rx_name != bag_name:
            issues.append(_issue("error", "문서", "처방전과 약봉투의 환자 이름이 달라요."))
        if len(bag_meds) != len(rx_meds):
            issues.append(
                _issue("warn", "문서", f"처방전 약 {len(rx_meds)}개, 약봉투 약 {len(bag_meds)}개로 개수가 달라요.")
            )
    if child_profile and child_profile.get("birth_date"):
        rx_birth = _birth_from_rrn((rx.get("환자") or {}).get("주민등록번호"))
        prof_birth = dt.date.fromisoformat(child_profile["birth_date"])
        if rx_birth and rx_birth != prof_birth:
            issues.append(
                _issue(
                    "error",
                    "문서",
                    "처방전의 생년월일이 선택한 아이의 생년월일과 달라요. 다른 아이의 처방전인지 확인해 주세요.",
                )
            )

    # ---------- 확인 2: 약 단위 (짝짓기 + 값 비교)
    pairs = _pair_bag_items(rx_meds, bag_meds) if bag_meds else {}
    for j, b in enumerate(bag_meds):
        if j not in pairs.values():
            issues.append(_issue("warn", b["명칭"], "약봉투에 있는 약을 처방전에서 찾지 못했어요."))

    medications, references = [], {}
    for i, r in enumerate(rx_meds):
        mid = i + 1
        b = bag_meds[pairs[i]] if i in pairs else None
        rc = receipt.get(b["명칭"]) if b else None
        label = (b or {}).get("명칭") or r["명칭"]
        reasons: list[str] = []
        usage = _clean_usage(r.get("용법"))

        if bag_meds and b is None:
            reasons.append("약봉투에서 같은 약을 찾지 못했어요")

        # 필요시 여부: 처방전 용법 문구와 약봉투 표시를 함께 본다. 하나라도 필요시면 필요시.
        rx_prn = None if usage is None else ("필요시" in usage)
        bag_prn = None if b is None else bool(b.get("필요시"))
        as_needed = bool(rx_prn) or bool(bag_prn)
        if usage is None:
            reasons.append("처방전 용법을 읽지 못했어요" + (" (약봉투 기준으로 필요시 여부를 정함)" if b else ""))
        elif bag_prn is not None and rx_prn != bag_prn:
            reasons.append("처방전과 약봉투의 필요시 여부가 달라요")

        # 숫자 비교: 처방전 ↔ 약봉투 복약안내 ↔ 약봉투 영수증
        form, route, unit_by_form = _form_of(r["명칭"])
        bag_dose = (b or {}).get("1회용량")
        no_dose = form in TOPICAL_NO_DOSE or bag_dose == "적당량"
        if not no_dose and b is not None and _num(bag_dose) is not None and not _same(r.get("1회투약량"), bag_dose):
            reasons.append(f"1회 용량이 처방전({r.get('1회투약량')})과 약봉투({bag_dose})에서 달라요")
        if rc is not None:
            for k_rx, k_rc, word in (
                ("1회투약량", "투약량", "1회 용량"),
                ("1일투여횟수", "횟수", "1일 횟수"),
                ("총투약일수", "일수", "일수"),
            ):
                if k_rx == "1회투약량" and no_dose:
                    continue
                if _num(rc.get(k_rc)) is not None and not _same(r.get(k_rx), rc.get(k_rc)):
                    reasons.append(f"{word}가 처방전({r.get(k_rx)})과 영수증({rc.get(k_rc)})에서 달라요")
        if b is not None and not as_needed:
            if b.get("1일횟수") is not None and not _same(r.get("1일투여횟수"), b.get("1일횟수")):
                reasons.append(f"1일 횟수가 처방전({r.get('1일투여횟수')})과 약봉투({b.get('1일횟수')})에서 달라요")
            if b.get("일수") is not None and not _same(r.get("총투약일수"), b.get("일수")):
                reasons.append(f"일수가 처방전({r.get('총투약일수')})과 약봉투({b.get('일수')})에서 달라요")

        unit = (b or {}).get("단위") or unit_by_form or _unit_from_rx_name(r["명칭"])
        if not no_dose and unit is None:
            reasons.append("용량 단위를 알 수 없어요")
        interval = interval_hours((b or {}).get("주의사항"), (b or {}).get("효능"), usage)
        if as_needed and interval is None:
            reasons.append("필요시 복용 간격 정보가 없어요")

        if reasons:
            rule_flags[mid] = "; ".join(reasons)
            for msg in reasons:
                issues.append(_issue("warn", label, msg))

        medications.append(
            {
                "medication_id": mid,
                "code": r.get("코드"),  # 보험코드 9자리: 이후 매칭·성분 조회 키
                "name": label,  # 화면 표시는 약봉투의 짧은 이름 우선
                "name_on_prescription": r["명칭"],
                "dosage_form": form,
                "route": route,
                "dose_per_time": None if no_dose else _num(r.get("1회투약량")),
                "unit": None if no_dose else unit,
                "as_needed": as_needed,
                "daily_count": None if as_needed else _num(r.get("1일투여횟수")),
                "max_daily_count": _num(r.get("1일투여횟수")) if as_needed else None,
                "min_interval_h": interval if as_needed else None,
                "total_days": _num(r.get("총투약일수")),
                "usage": usage or (b or {}).get("복용법"),
                "ingredient": ingredient_of(r["명칭"], (b or {}).get("명칭")),
                "storage": _clean_bag_text((b or {}).get("보관")),  # 보관법은 약국 안내를 그대로 (LLM이 쓰지 않음)
                "pharmacy_caution": _clean_bag_text((b or {}).get("주의사항")),
                "has_pharmacy_info": b is not None,
            }
        )
        if b is not None:  # 약봉투의 약국 복약 안내 → LLM 참조 정보 (지어내지 않게)
            parts = [
                f"[{_clean_bag_text(b.get('분류')) or '분류 없음'}] {_clean_bag_text(b.get('효능')) or ''}".strip()
            ]
            if b.get("주의사항"):
                parts.append(f"주의: {_clean_bag_text(b['주의사항'])}")
            if b.get("보관"):
                parts.append(f"보관: {_clean_bag_text(b['보관'])}")
            references[mid] = "약국 안내(약봉투): " + " / ".join(parts)

    # ---------- 진료 근거: 가이드 하단 "이번 가이드 생성 근거"에 그대로 보여 준다 (LLM에는 보내지 않음)
    mismatches = sum(1 for x in issues if x["level"] == "warn" and x["target"] != "문서")
    documents = [{"type": "처방전", "date": rx.get("교부일"), "place": (rx.get("의료기관") or {}).get("명칭")}]
    if bag is not None:
        documents.append(
            {
                "type": "약봉투",
                "date": (bag.get("복약안내") or {}).get("조제일자"),
                "place": (bag.get("영수증") or {}).get("상호"),
            }
        )
    record = {
        "documents": documents,
        "diagnosis_codes": list(rx.get("질병분류기호") or []),
        "cross_check": {
            "done": bag is not None,
            "mismatch_count": mismatches,
            "summary": (
                "처방전만 사용했어요 (약봉투로 교차 확인하지 않음)"
                if bag is None
                else "처방전과 약봉투의 약·용량·횟수·일수가 서로 맞아요"
                if mismatches == 0
                else f"처방전과 약봉투에서 확인이 필요한 항목 {mismatches}개 → 해당 약에 약사 확인을 켰어요"
            ),
        },
    }
    return {
        "ok": not any(x["level"] == "error" for x in issues),
        "medications": medications,
        "rule_flags": rule_flags,
        "issues": issues,
        "references": references,
        "record": record,
    }
