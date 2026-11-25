"""가이드 템플릿(DATA-REF-006·007)의 출처를 공식 원문으로 바꾸는 스크립트.

규칙
- 출처 주소는 질병관리청·식약처·정부 정책브리핑·약학정보원(허가자료) 같은 공식 도메인만 허용한다.
  기사·블로그·업체 정리 글 주소는 모두 뺀다.
- 문장마다 공식 원문과 대조한 결과(status)를 붙인다.
    verified  원문과 내용이 맞음
    revised   원문에 맞게 문장을 고침
    check     공식 출처는 달았지만 이번에 원문을 다시 열어 대조하지 못함 → 사람이 확인
    internal  PillyMate 자체 안전 원칙
    removed   공식 출처를 찾지 못함 → 가이드에 나오지 않게 함
- removed 처리: 생활 안내(sections[].items)는 disabled로 끄고,
  위험 신호·나이별 주의·약 팁·관리 포인트는 목록에서 빼서 _removed_unverified에 보관한다.

실행 (저장소 루트에서)
    uv run python -m app.scripts.fix_guide_sources            # 바뀔 내용만 보기
    uv run python -m app.scripts.fix_guide_sources --write    # 파일에 반영
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REVIEW_DATE = "2026-11-24"
DEFAULT_DIR = Path(__file__).resolve().parents[1] / "resources" / "guide" / "templates"

OFFICIAL_HOSTS = {
    "health.kdca.go.kr",
    "kdca.go.kr",
    "www.kdca.go.kr",
    "nedrug.mfds.go.kr",
    "mfds.go.kr",
    "www.mfds.go.kr",
    "korea.kr",
    "www.korea.kr",
    "common.health.kr",
}

_PORTAL = (
    "https://health.kdca.go.kr/healthinfo/biz/health/gnrlzHealthInfo/gnrlzHealthInfo/gnrlzHealthInfoView.do?cntnts_sn="
)

# 출처 목록. url이 None이면 주소가 없는 공식 문서(정보집 등)이거나 내부 원칙이다.
SOURCES: dict[str, dict[str, Any]] = {
    "KDCA_FEVER": {"title": "질병관리청 국가건강정보포털 「소아 발열 대처법」", "url": _PORTAL + "6951"},
    "KDCA_COLD": {"title": "질병관리청 국가건강정보포털 「감기」", "url": _PORTAL + "5423"},
    "KDCA_OM": {"title": "질병관리청 국가건강정보포털 「중이염」", "url": _PORTAL + "3568"},
    "KDCA_GE": {"title": "질병관리청 국가건강정보포털 「급성 바이러스 위장관염」", "url": _PORTAL + "6756"},
    "KDCA_STOOL": {"title": "질병관리청 국가건강정보포털 「대변 이상」", "url": _PORTAL + "5722"},
    "KDCA_AD": {
        "title": "질병관리청 국가건강정보포털 이달의 건강정보 「알레르기 예방관리수칙」 중 아토피피부염 예방관리수칙",
        "url": "https://health.kdca.go.kr/healthinfo/biz/health/ntcnInfo/healthSourc/thtimtCntnts/thtimtCntntsView.do?thtimt_cntnts_sn=25",
    },
    "KDCA_AD_INFO": {"title": "질병관리청 국가건강정보포털 「아토피피부염」", "url": _PORTAL + "6582"},
    "KDCA_EYE": {"title": "질병관리청 국가건강정보포털 「유행각결막염」", "url": _PORTAL + "5270"},
    "KDCA_ABX": {"title": "질병관리청 국가건강정보포털 「항생제」", "url": _PORTAL + "6475"},
    "KDCA_ABX_FAQ": {
        "title": "질병관리청 「항생제에 흔히 묻는 질문」",
        "url": "https://kdca.go.kr/gallery.es?act=view&bid=0002&list_no=144960&mid=a20108070000",
    },
    "MFDS_MANUAL_25": {
        "title": "식약처 의약품 안전사용 매뉴얼 ㉕ 「환절기, 어린이 감기약 올바르게 먹이세요!」",
        "url": "https://nedrug.mfds.go.kr/eBook/catImage/182/25.pdf",
    },
    "MFDS_SYRUP_BRIEF": {
        "title": "식약청 「어린이 감기약, 꼭 확인하고 먹이세요」 (정책브리핑 부처 브리핑)",
        "url": "https://www.korea.kr/briefing/policyBriefingView.do?newsId=148709458",
    },
    "MFDS_FEVER": {
        "title": "식약처 컨슈머 뉴스레터 Issue.2 「어린이 해열제 복용 방법은?」 (2026.1.9)",
        "url": "https://www.mfds.go.kr/brd/m_61/view.do?seq=54388",
    },
    "LBL_RACE": {
        "title": "의약품안전나라 하이드라섹산10mg(라세카도트릴) 허가정보 (품목기준코드 201405412)",
        "url": "https://nedrug.mfds.go.kr/pbp/CCBBB01/getItemDetail?itemSeq=201405412",
    },
    "MFDS_GUIDE_186": {
        "title": "식약처 「소아·청소년에 대한 의약품 적정사용 정보집」(2022.12 개정) 186. Cetirizine (546~547쪽)",
        "url": "https://www.mfds.go.kr/brd/m_218/view.do?seq=33514",
    },
    "MFDS_GUIDE_9": {
        "title": "식약처 「소아·청소년에 대한 의약품 적정사용 정보집」(2022.12 개정) 9. Desonide (46~47쪽)",
        "url": "https://www.mfds.go.kr/brd/m_218/view.do?seq=33514",
    },
    "KPHA_2026": {"title": "대한소아청소년병원협회 해열제 교차복용 권고 (주제선정서 참고문헌 18)", "url": None},
    "PILLYMATE_RULE": {"title": "PillyMate 안전 원칙 (모르는 건 약사 확인)", "url": None},
    "TODO_SOURCE": {"title": "출처 확보 필요 - 출처를 찾기 전에는 가이드에 넣지 않음", "url": None},
}

V, R, C, INT, X = "verified", "revised", "check", "internal", "removed"

# 문장(item) 단위 결정. text가 있으면 문장을 바꾸고, 그 밖의 키(min_months 등)는 그대로 덮어쓴다.
ITEM_FIXES: dict[str, dict[str, Any]] = {
    # --- common: 위험 신호·나이별 주의 (소아 발열 대처법 원문과 대조)
    "er.under3m_fever": {"status": V, "source": "KDCA_FEVER"},
    "er.lethargy": {"status": V, "source": "KDCA_FEVER"},
    "er.breathing": {"status": V, "source": "KDCA_FEVER"},
    "er.cyanosis": {"status": V, "source": "KDCA_FEVER"},
    "er.rash": {"status": V, "source": "KDCA_FEVER"},
    "er.seizure": {"status": V, "source": "KDCA_FEVER"},
    "doc.fever5d": {"status": V, "source": "KDCA_FEVER"},
    "doc.3to6m_39": {"status": V, "source": "KDCA_FEVER"},
    "doc.diaper6h": {"status": V, "source": "KDCA_FEVER"},
    "age.under3m": {
        "status": R,
        "source": "KDCA_FEVER",
        "text": "생후 3개월 미만 아기가 38℃ 이상 열이 나면 컨디션과 상관없이 바로 응급실 진료를 받으세요.",
    },
    "age.3to6m": {"status": R, "source": "KDCA_FEVER", "text": "생후 3~6개월 아기가 39℃ 이상이면 진료를 받으세요."},
    "age.under12m_honey": {"status": X},
    "age.measure_by_weight": {
        "status": R,
        "source": "KDCA_FEVER",
        "text": "해열제 양은 나이보다 몸무게를 기준으로 정해요. 몸무게가 바뀌면 약사에게 다시 확인하세요.",
    },
    # --- 감기·기관지염
    "cold.course.peak": {"status": V, "source": "KDCA_COLD"},
    "cold.water.often": {"status": R, "source": "KDCA_COLD", "min_months": 6},
    "cold.water.fever": {
        "status": R,
        "source": "KDCA_FEVER",
        "min_months": 6,
        "text": "열이 날 때는 평소보다 더 자주 수분을 챙겨 주세요.",
    },
    "cold.eat.small": {"status": R, "source": "KDCA_COLD", "text": "회복하려면 충분한 영양 섭취가 필요해요."},
    "cold.rest": {"status": V, "source": "KDCA_COLD"},
    "cold.clothes": {"status": V, "source": "KDCA_FEVER"},
    "cold.humidity": {"status": V, "source": "KDCA_COLD"},
    "cold.no_alcohol_rub": {"status": V, "source": "KDCA_FEVER"},
    "cold.handwash": {
        "status": R,
        "source": "KDCA_COLD",
        "text": "외출 뒤에는 손을 씻고, 손으로 코나 눈을 만지지 않게 해 주세요.",
    },
    "cold.daycare": {
        "status": R,
        "source": "KDCA_FEVER",
        "text": "열이 나는 동안에는 어린이집·학교를 쉬고 충분히 쉬게 해 주세요.",
        "disabled": False,
        "needs_review": False,
    },
    # --- 결막염 (유행각결막염 원문)
    "conj.course.contagious": {"status": V, "source": "KDCA_EYE"},
    "conj.handwash": {"status": R, "source": "KDCA_EYE", "text": "눈을 만졌다면 꼭 손을 깨끗이 씻게 해 주세요."},
    "conj.no_rub": {"status": V, "source": "KDCA_EYE"},
    "conj.towel": {"status": R, "source": "KDCA_EYE", "text": "수건, 세면도구, 침구는 따로 쓰게 해 주세요."},
    "conj.eyedrop_own": {"status": X},
    "conj.no_patch": {"status": R, "source": "KDCA_EYE", "text": "안대는 하지 않는 게 좋아요."},
    "conj.daycare": {
        "status": R,
        "source": "KDCA_EYE",
        "text": "증상이 시작된 뒤 약 2주 동안은 사람이 많이 모이는 곳을 피해 주세요. "
        "어린이집·학교에 다시 가는 시기는 진료 때 확인하세요.",
    },
    "conj.vision": {"status": X},
    # --- 피부염 (아토피피부염 예방관리수칙)
    "derm.course.long": {"status": V, "source": "KDCA_AD_INFO"},
    "derm.course.moisturize_basic": {"status": R, "source": "KDCA_AD", "text": "보습과 피부 관리를 꾸준히 해 주세요."},
    "derm.bath.warm": {"status": V, "source": "KDCA_AD"},
    "derm.bath.pat": {"status": X},
    "derm.moist.3min": {"status": R, "source": "KDCA_AD", "text": "목욕 직후에 보습제를 발라 주세요."},
    "derm.moist.twice": {"status": V, "source": "KDCA_AD"},
    "derm.order": {"status": INT, "source": "PILLYMATE_RULE"},
    "derm.room": {"status": R, "source": "KDCA_AD", "text": "실내 온도와 습도가 너무 높거나 낮지 않게 유지해 주세요."},
    "derm.clothes": {"status": R, "source": "KDCA_AD", "text": "거친 옷감보다 부드러운 옷감의 옷을 입혀 주세요."},
    "derm.scratch": {
        "status": R,
        "source": "KDCA_AD",
        "text": "긁으면 피부가 더 상하고 가려움이 심해져요. 손톱을 짧게 깎아 주세요.",
    },
    "derm.ooze": {"status": X},
    # --- 장염 (급성 바이러스 위장관염·대변 이상)
    "ent.course.goal": {"status": R, "source": "KDCA_GE", "text": "장염 치료의 핵심은 탈수를 막고 바로잡는 거예요."},
    "ent.ors": {"status": R, "source": "KDCA_GE", "text": "처방받은 경구수액이 있으면 먹여서 잃은 수분을 채워 주세요."},
    "ent.no_sports_drink": {"status": V, "source": "KDCA_STOOL"},
    "ent.breastfeed": {"status": V, "source": "KDCA_GE"},
    "ent.no_fasting": {"status": V, "source": "KDCA_STOOL"},
    "ent.avoid": {"status": R, "source": "KDCA_GE", "text": "기름지거나 매우 자극적인 음식은 피해 주세요."},
    "ent.handwash": {
        "status": R,
        "source": "KDCA_GE",
        "text": "화장실에 다녀온 뒤와 기저귀를 간 뒤에는 흐르는 물에 비누로 30초 이상 손을 씻으세요.",
    },
    "ent.severe_dehyd": {
        "status": R,
        "source": "KDCA_STOOL",
        "needs_review": False,
        "text": "잘 먹지 못하고 처지거나, 소변 양이 줄거나, 피나 점액이 섞인 변을 보면 진료를 받으세요.",
    },
    # --- 중이염
    "om.course.followup": {"status": V, "source": "KDCA_OM"},
    "om.course.abx": {"status": V, "source": "KDCA_ABX_FAQ"},
    "om.bottle.position": {"status": V, "source": "KDCA_OM"},
    "om.bottle.sleep": {"status": X},
    "om.smoke": {"status": V, "source": "KDCA_OM"},
    "om.handwash": {"status": V, "source": "KDCA_OM"},
    "om.vaccine": {"status": V, "source": "KDCA_OM"},
    "om.ear_discharge": {
        "status": R,
        "source": "KDCA_OM",
        "text": "귀에서 고름이나 분비물이 흘러나올 때",
        "disabled": False,
        "needs_review": False,
    },
    # --- 약 계열 팁 (DATA-REF-007)
    "form.liquid.measure": {
        "status": R,
        "source": "MFDS_MANUAL_25",
        "text": "밥숟가락 대신 약물용 계량컵이나 계량스푼으로 재세요. 쓴 뒤에는 물로 씻어 충분히 말려 두세요.",
    },
    "form.liquid.separate": {"status": V, "source": "MFDS_MANUAL_25"},
    "form.liquid.month": {"status": V, "source": "MFDS_SYRUP_BRIEF"},
    "common.missed": {
        "status": R,
        "source": "MFDS_SYRUP_BRIEF",
        "text": "먹이는 걸 잊었는데 다음 먹일 시간이 이미 됐다면 그때 한 번 양만 먹이세요.",
    },
    "common.storage": {"status": V, "source": "MFDS_MANUAL_25"},
    "abx.finish": {"status": V, "source": "KDCA_ABX_FAQ"},
    "abx.no_share": {"status": R, "source": "KDCA_ABX", "text": "남은 항생제를 두었다가 나중에 임의로 먹이지 마세요."},
    "abx.fridge": {"status": V, "source": "MFDS_MANUAL_25"},
    "apap.interval": {"status": V, "source": "KDCA_FEVER"},
    "apap.dup": {
        "status": R,
        "source": "MFDS_FEVER",
        "text": "감기로 병원에서 처방받은 약에 해열제 성분이 들어 있는지 확인하세요.",
    },
    "ibu.interval": {"status": V, "source": "KDCA_FEVER"},
    "ibu.same_family": {
        "status": R,
        "source": "MFDS_FEVER",
        "text": "이부프로펜과 덱시부프로펜은 같은 계열이에요. 번갈아 먹이지 마세요.",
    },
    "pro.with_abx": {"status": X},
    "diar.fluids": {
        "status": R,
        "source": "LBL_RACE",
        "text": "이 약은 수분 보충을 돕는 약이에요. 설사할 때는 경구수액으로 수분을 채우는 게 꼭 필요해요.",
    },
    "diar.7days": {
        "status": R,
        "source": "LBL_RACE",
        "text": "이 약은 7일을 넘겨 먹이지 않아요. 증상이 5일 이상 계속되면 꼭 진료를 받으세요.",
    },
    "ah.sleepy": {
        "status": R,
        "source": "MFDS_GUIDE_186",
        "text": "졸리거나 어지러울 수 있어요. 주의나 집중이 필요한 활동은 조심하게 해 주세요.",
    },
    "cough.water": {
        "status": R,
        "source": "KDCA_COLD",
        "text": "가래가 잘 나오려면 물을 충분히 마시는 게 도움이 돼요.",
    },
    "ts.thin": {
        "status": R,
        "source": "MFDS_GUIDE_9",
        "text": "환부에 얇게 바르고, 붕대 등으로 덮어 밀봉하지 마세요. 피부가 접힌 부위가 밀봉되지 않게 주의하세요.",
    },
    "ts.wash": {"status": X},
    "eye.no_touch": {"status": X},
    "eye.own": {"status": R, "source": "KDCA_EYE", "text": "수건과 세면도구는 아이 혼자 쓰게 해 주세요."},
    # --- 오늘의 관리 포인트 (focus)
    "cold.focus.water": {
        "status": R,
        "source": "KDCA_COLD",
        "min_months": 6,
        "why": "수분이 부족하면 가래가 잘 안 나와요.",
        "actions": ["물을 평소보다 자주 챙겨 주세요.", "열이 날 때는 더 자주 챙겨 주세요."],
        "needs_review": False,
    },
    "cold.focus.rest": {"status": V, "source": "KDCA_COLD"},
    "cold.focus.air": {"status": V, "source": "KDCA_COLD", "needs_review": False},
    "om.focus.followup": {"status": V, "source": "KDCA_OM"},
    "om.focus.bottle": {
        "status": R,
        "source": "KDCA_OM",
        "why": "눕혀서 먹이면 중이염이 더 잘 생긴다고 안내돼요.",
        "actions": ["아기 머리를 배보다 높게 하고 먹이세요.", "눕혀서 먹이지 마세요."],
    },
    "om.focus.smoke": {"status": V, "source": "KDCA_OM"},
    "om.focus.hand": {"status": V, "source": "KDCA_OM"},
    "ent.focus.fluid": {
        "status": R,
        "source": "KDCA_GE",
        "actions": [
            "처방받은 경구수액이 있으면 먹여서 잃은 수분을 채워 주세요.",
            "이온음료나 과일주스는 탈수를 고치는 데 맞지 않아요.",
        ],
    },
    "ent.focus.eat": {
        "status": R,
        "source": "KDCA_STOOL",
        "why": "굶는다고 빨리 낫지 않아요. 적절히 먹는 게 회복에 도움이 돼요.",
        "actions": ["탈수가 나아지면 평소처럼 먹여 주세요.", "기름지거나 매우 자극적인 음식은 피해 주세요."],
    },
    "ent.focus.hand": {
        "status": R,
        "source": "KDCA_GE",
        "why": "손 씻기가 장염이 퍼지는 걸 막는 기본 수칙이에요.",
        "actions": ["화장실에 다녀온 뒤와 기저귀를 간 뒤에는 흐르는 물에 비누로 30초 이상 손을 씻으세요."],
    },
    "derm.focus.moist": {
        "status": R,
        "source": "KDCA_AD",
        "why": "보습과 피부 관리가 아토피피부염 예방관리수칙의 첫 번째예요.",
        "actions": ["목욕 직후에 보습제를 발라 주세요.", "보습제는 하루에 적어도 두 번 이상 발라 주세요."],
        "needs_review": False,
    },
    "derm.focus.bath": {
        "status": R,
        "source": "KDCA_AD",
        "why": "관리 수칙에서 미지근한 물로 10분 정도 목욕하라고 안내해요.",
        "actions": ["미지근한 물로 10분 정도 씻겨 주세요.", "때를 밀지 마세요."],
        "needs_review": False,
    },
    "derm.focus.env": {
        "status": R,
        "source": "KDCA_AD",
        "actions": [
            "거친 옷감보다 부드러운 옷감의 옷을 입혀 주세요.",
            "실내 온도와 습도가 너무 높거나 낮지 않게 해 주세요.",
        ],
    },
    "conj.focus.hand": {
        "status": R,
        "source": "KDCA_EYE",
        "why": "유행성 눈병은 눈 분비물이나 손을 통해 쉽게 옮아요.",
        "actions": ["눈을 만졌다면 꼭 손을 깨끗이 씻게 해 주세요.", "가려워도 눈을 비비지 않게 해 주세요."],
    },
    "conj.focus.separate": {
        "status": R,
        "source": "KDCA_EYE",
        "why": "수건이나 세면도구를 같이 쓰면 가족에게 옮을 수 있어요.",
        "actions": ["수건, 세면도구, 침구는 따로 쓰게 해 주세요."],
    },
    "common.focus.observe": {"status": V, "source": "KDCA_FEVER"},
    "cold.water.under6m": {"status": V, "source": "KDCA_FEVER"},
}

# 새로 넣는 문장: (파일, 섹션 key, 넣을 위치의 앞 문장 id, 문장)
NEW_ITEMS: list[tuple[str, str, str, dict[str, Any]]] = [
    (
        "DATA-REF-006_cold_bronchitis.json",
        "hydration",
        "cold.water.fever",
        {
            "id": "cold.water.under6m",
            "text": "생후 6개월 미만 아기는 의료진이 따로 말하지 않았다면 물을 더 먹이지 말고, "
            "모유나 분유를 조금씩 자주 먹이세요.",
            "source": "KDCA_FEVER",
            "needs_review": False,
            "max_months": 5,
            "source_check": V,
        },
    ),
]

# 위험 신호 안에서 옮길 문장: id → (원래 목록, 옮길 목록)
MOVES: dict[str, tuple[str, str]] = {"ent.severe_dehyd": ("go_to_er", "see_doctor")}


def host_ok(url: str | None) -> bool:
    return url is None or (urlparse(url).hostname or "") in OFFICIAL_HOSTS


def apply_fix(item: dict[str, Any], log: list[dict[str, Any]], fname: str) -> bool:
    """문장 하나에 결정을 적용한다. 남겨 두면 True, 목록에서 뺄 것이면 False."""
    fix = ITEM_FIXES.get(item["id"])
    old_source = item.get("source")
    if fix is None:
        # 결정이 없는 문장: 출처가 공식이면 check, 아니면 제거
        src = SOURCES.get(old_source or "")
        fix = {"status": C} if src and src["url"] is not None and host_ok(src["url"]) else {"status": X}
    status = fix["status"]
    entry = {"file": fname, "id": item["id"], "status": status, "old_source": old_source}
    if status == X:
        item["source"] = "TODO_SOURCE"
        item["source_check"] = X
        entry["new_source"] = "TODO_SOURCE"
        log.append(entry)
        return False
    before = item.get("text") or item.get("why")
    for key, value in fix.items():
        if key != "status":
            item[key] = value
    item["source_check"] = status
    entry["new_source"] = item.get("source")
    if "text" in fix and fix["text"] != before:
        entry["old_text"], entry["new_text"] = before, fix["text"]
    log.append(entry)
    return True


def walk(
    node: Any, fname: str, log: list[dict[str, Any]], removed: list[dict[str, Any]], in_items: bool = False
) -> Any:
    if isinstance(node, dict):
        return {k: walk(v, fname, log, removed, in_items=(k == "items")) for k, v in node.items()}
    if isinstance(node, list) and node and all(isinstance(x, dict) and "id" in x and "source" in x for x in node):
        kept = []
        for item in node:
            item = dict(item)
            if apply_fix(item, log, fname):
                kept.append(item)
            elif in_items:  # 생활 안내 문장은 남겨 두되 꺼서 가이드에 안 나오게
                item["disabled"] = True
                kept.append(item)
            else:
                removed.append(item)
        return kept
    if isinstance(node, list):
        return [walk(x, fname, log, removed) for x in node]
    return node


def used_sources(node: Any, acc: set[str]) -> set[str]:
    if isinstance(node, dict):
        if isinstance(node.get("source"), str) and "id" in node:
            acc.add(node["source"])
        for k, v in node.items():
            if k not in ("sources", "_removed_unverified"):
                used_sources(v, acc)
    elif isinstance(node, list):
        for x in node:
            used_sources(x, acc)
    return acc


def bad_urls(node: Any, acc: list[str]) -> list[str]:
    if isinstance(node, dict):
        for v in node.values():
            bad_urls(v, acc)
    elif isinstance(node, list):
        for x in node:
            bad_urls(x, acc)
    elif isinstance(node, str) and node.startswith("http") and not host_ok(node):
        acc.append(node)
    return acc


def process(path: Path, log: list[dict[str, Any]]) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    for fname, sec_key, after_id, new in NEW_ITEMS:
        if fname == path.name:
            for sec in data.get("sections", []):
                ids = [x["id"] for x in sec["items"]]
                if sec["key"] == sec_key and new["id"] not in ids:
                    sec["items"].insert(ids.index(after_id) + 1 if after_id in ids else len(ids), dict(new))
                    log.append(
                        {
                            "file": fname,
                            "id": new["id"],
                            "status": "added",
                            "new_source": new["source"],
                            "new_text": new["text"],
                        }
                    )
    for block in ("warning_signs", "extra_warning_signs"):
        signs = data.get(block)
        if isinstance(signs, dict):
            for item_id, (src, dst) in MOVES.items():
                hit = [x for x in signs.get(src, []) if x.get("id") == item_id]
                if hit:
                    signs[src] = [x for x in signs[src] if x.get("id") != item_id]
                    signs.setdefault(dst, []).extend(hit)
    removed: list[dict[str, Any]] = list(data.pop("_removed_unverified", []))  # 다시 돌려도 중복되지 않게
    data = walk(data, path.name, log, removed)
    if removed:
        data["_removed_unverified"] = removed
    keys = sorted(used_sources(data, set()))
    data["sources"] = {k: {"title": SOURCES[k]["title"], "url": SOURCES[k]["url"]} for k in keys}
    data["source_review"] = {
        "date": REVIEW_DATE,
        "rule": "공식 원문(질병관리청·식약처 등)만 출처로 씀. 원문과 대조 결과는 각 문장의 source_check에 표시. "
        "removed는 출처를 찾을 때까지 가이드에 나오지 않음.",
    }
    return data


def main() -> int:  # noqa: C901
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", type=Path, default=DEFAULT_DIR, help="템플릿 폴더")
    ap.add_argument("--write", action="store_true", help="파일에 반영 (없으면 미리보기만)")
    ap.add_argument("--report", type=Path, help="결과 표를 마크다운으로 저장할 경로")
    args = ap.parse_args()

    bad_registry = [k for k, s in SOURCES.items() if not host_ok(s["url"])]
    if bad_registry:
        print(f"공식 도메인이 아닌 출처가 목록에 있어요: {bad_registry}", file=sys.stderr)
        return 1

    log: list[dict[str, Any]] = []
    results: dict[Path, dict[str, Any]] = {}
    for path in sorted(args.dir.glob("DATA-REF-00[67]_*.json")):
        results[path] = process(path, log)

    problems = []
    for path, data in results.items():
        for url in bad_urls(data, []):
            problems.append(f"{path.name}: 공식이 아닌 주소가 남아 있어요 {url}")
        for key in used_sources(data, set()):
            if key not in SOURCES:
                problems.append(f"{path.name}: 목록에 없는 출처 키 {key}")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1

    counts: dict[str, int] = {}
    for e in log:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    lines = [
        f"# 가이드 템플릿 출처 점검 결과 ({REVIEW_DATE})",
        "",
        "상태: " + ", ".join(f"{k} {v}개" for k, v in sorted(counts.items())),
        "",
        "| 파일 | 문장 id | 상태 | 이전 출처 → 새 출처 | 바뀐 문장 |",
        "| --- | --- | --- | --- | --- |",
    ]
    order = {"removed": 0, "check": 1, "revised": 2, "added": 3, "internal": 4, "verified": 5}
    for e in sorted(log, key=lambda e: (order.get(e["status"], 9), e["file"], e["id"])):
        change = e.get("new_text", "") if e.get("old_text") != e.get("new_text") else ""
        lines.append(
            f"| {e['file'].removesuffix('.json')} | {e['id']} | {e['status']} | "
            f"{e.get('old_source') or '-'} → {e.get('new_source') or '-'} | {change} |"
        )
    report = "\n".join(lines)
    print(report)
    if args.report:
        args.report.write_text(report + "\n", encoding="utf-8")

    if args.write:
        for path, data in results.items():
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n{len(results)}개 파일에 반영했어요: {args.dir}")
    else:
        print("\n미리보기만 했어요. 반영하려면 --write를 붙여 다시 실행하세요.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
