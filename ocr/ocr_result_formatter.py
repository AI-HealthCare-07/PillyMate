"""파서 결과(한글 키)를 API 명세 7절 run_ocr() 반환 형식(snake_case)으로 바꾼다.

반환 형식:
{
  "prescription_date", "hospital_name", "diagnosis_extracted",
  "medications": [{ "name", "insurance_code", "dose_per_time", "unit", "daily_count", "total_days",
                    "max_daily_count", "as_needed", "usage", "route", "dosage_form", "confidence" }]
}
모르는 값은 None이다. 환자 성명·주민등록번호 같은 식별정보는 이 형식에 들어가지 않는다.
OCR 원문(마스킹본 포함)도 돌려주지 않는다 (11/24 멘토링 4절: 필요한 데이터만 구조화해 저장).

값 규칙은 API 명세 11절 결정 사항을 따른다.
- unit: mL · 포 · 정 · 캡슐 · g · 방울 · 개 (그 밖의 단위는 None)
- route: ORAL · EXTERNAL
- dosage_form: SYRUP · DRY_SYRUP · POWDER · TABLET · CAPSULE · OINTMENT · CREAM · EYE_DROP · SUPPOSITORY · ETC
- as_needed가 True이면 daily_count는 None (복용 횟수 대신 max_daily_count로 안내)
"""

import re

ALLOWED_UNITS = ("mL", "포", "정", "캡슐", "g", "방울", "개")
UNIT_ALIASES = {"ml": "mL", "mℓ": "mL", "cc": "mL", "캅셀": "캡슐"}

ORAL = "ORAL"
EXTERNAL = "EXTERNAL"
ORAL_FORMS = ("SYRUP", "DRY_SYRUP", "POWDER", "TABLET", "CAPSULE")
EXTERNAL_FORMS = ("OINTMENT", "CREAM", "EYE_DROP", "SUPPOSITORY")

# 위에서부터 먼저 맞는 제형을 고른다. '건조시럽'이 '시럽'보다, '점안액'이 '액'보다 먼저 와야 한다.
# '시럼'은 OCR이 '시럽'을 자주 잘못 읽는 글자다.
DOSAGE_FORM_PATTERNS = (
    ("EYE_DROP", re.compile(r"점안")),
    ("SUPPOSITORY", re.compile(r"좌약|좌제")),
    ("OINTMENT", re.compile(r"연고")),
    ("CREAM", re.compile(r"크림")),
    # '건조사립'은 OCR이 '건조시럽'을 잘못 읽은 글자다.
    ("DRY_SYRUP", re.compile(r"건조\s*[시사][럽럼립]|드라이\s*시[럽럼]")),
    ("CAPSULE", re.compile(r"캡슐")),
    ("SYRUP", re.compile(r"시[럽럼]|현탁|내용액")),
    ("POWDER", re.compile(r"\d산$|산$|세립|과립|가루|산제")),
    ("TABLET", re.compile(r"정(?:제|\d|$)")),
)
# 위 제형에 없지만 몸에 바르거나 뿌리거나 들이마시는 약 → dosage_form ETC, route EXTERNAL.
EXTERNAL_ETC_PATTERN = re.compile(
    r"스프레이|분무|흡입|흠입|네뷸|할러|레스[풀플]|점이|이용액|귀약|외용|패치|로션|겔|가글"
)

AS_NEEDED_PATTERN = re.compile(r"필요\s*시|열\s*이?\s*날\s*때|아플\s*때|prn", re.IGNORECASE)
MAX_DAILY_COUNT_PATTERN = re.compile(r"(?:1\s*일|하루)\s*최대\s*\(?\s*(\d+)\s*\)?\s*(?:회|번)")
# 처방전 약 이름의 포장 단위 표기: '/1포', '/1정', '/100(1)mL/병', '0.5mg/2mL(…)/1관'.
# 마지막 표기가 1회 투약량의 단위다. 관·회·병처럼 허용 목록에 없는 단위가 마지막이면 None이 된다.
PACKAGE_UNIT_PATTERN = re.compile(r"/\s*\d+(?:\.\d+)?\s*(?:\(\s*\d+\s*\))?\s*(mL|ml|포|정|캡슐|g|개|관|회|병|방울)")
EAR_DROP_PATTERN = re.compile(r"점이|이용액|귀약")
# 가루약은 한 번 먹을 양을 1포씩 나눠 싸 주고, 좌약은 한 번에 1개를 넣는다.
DEFAULT_UNIT_BY_FORM = {
    "SYRUP": "mL",
    "DRY_SYRUP": "mL",
    "POWDER": "포",
    "TABLET": "정",
    "CAPSULE": "캡슐",
    "EYE_DROP": "방울",
    "SUPPOSITORY": "개",
}


def main_drug_name(name):
    """'세파클러건조시럽(내복)/60(1)mL/병' → '세파클러건조시럽'. 괄호나 '/'가 처음 나오기 전까지만 남긴다."""
    return re.split(r"[(/（／]", name or "", maxsplit=1)[0].strip()


def display_drug_name(name):
    """보호자에게 보여 줄 약 이름. '맥시부펜시럽(덱시부프로펜)/100(1)mL/병' → '맥시부펜시럽'.

    성분·포장 표기는 단위·제형을 짐작하는 데만 쓰고(그래서 원래 이름으로 먼저 판단한다) 출력에서는 뗀다.
    '(급여)타이레놀'처럼 괄호로 시작해 남는 글자가 없으면 원래 이름을 그대로 둔다.
    """
    return main_drug_name(name) or name


def match_dosage_form(text):
    for form, pattern in DOSAGE_FORM_PATTERNS:
        if pattern.search(text):
            return form
    return None


def infer_dosage_form(name, *hints):
    """약 이름을 먼저 보고, 모르겠으면 분류·성상 같은 보조 글자를 본다. 알 수 없으면 None.

    보조 글자는 '흰색 비강 분무 현탁액'처럼 뿌리는 약에도 '현탁액'이 들어가므로,
    뿌리기·흡입 같은 표현을 제형 낱말보다 먼저 본다.
    """
    main_name = main_drug_name(name)
    if main_name:
        form = match_dosage_form(main_name)
        if form:
            return form
        if EXTERNAL_ETC_PATTERN.search(main_name):
            return "ETC"
    for hint in hints:
        if not hint:
            continue
        if EXTERNAL_ETC_PATTERN.search(hint):
            return "ETC"
        form = match_dosage_form(hint)
        if form:
            return form
    return None


def infer_route(dosage_form, *texts):
    """제형으로 복용 경로를 정한다. ETC는 글자로 판단하고, 알 수 없으면 None."""
    if dosage_form in ORAL_FORMS:
        return ORAL
    if dosage_form in EXTERNAL_FORMS:
        return EXTERNAL
    if dosage_form == "ETC":
        if any(text and EXTERNAL_ETC_PATTERN.search(text) for text in texts):
            return EXTERNAL
        if any(text and "내복" in text for text in texts):
            return ORAL
    return None


def normalize_unit(unit):
    if not unit:
        return None
    unit = UNIT_ALIASES.get(unit.strip().lower(), unit.strip())
    return unit if unit in ALLOWED_UNITS else None


def infer_prescription_unit(name, dosage_form):
    """처방전에는 단위 칸이 없어서 약 이름의 포장 표기나 제형으로 짐작한다.

    안약·귀약은 '/5mL/병'처럼 병 용량이 적혀 있어도 1회 투약량은 방울 수다.
    """
    if dosage_form == "EYE_DROP" or EAR_DROP_PATTERN.search(name or ""):
        return "방울"
    found = PACKAGE_UNIT_PATTERN.findall(name or "")
    if found:
        return normalize_unit(found[-1])
    if re.search(r"ml", name or "", re.IGNORECASE):
        return "mL"
    return DEFAULT_UNIT_BY_FORM.get(dosage_form)


def bag_unit(raw_unit, name, dosage_form):
    """약봉투의 단위. 읽은 단위가 허용 목록에 없으면(앰플·흡입 등) 짐작하지 않고 None.

    짐작(약 이름의 포장 표기·제형)은 약봉투에 단위가 아예 없을 때만 한다.
    예: '1앰플씩'을 이름의 '/2mL'로 바꾸면 1앰플(2mL)이 1mL로 보여 양이 달라진다.
    """
    if raw_unit and str(raw_unit).strip():
        return normalize_unit(raw_unit)
    return infer_prescription_unit(name, dosage_form)


def clean_usage(text):
    """'->식후 30분' 같은 화살표·기호를 떼어 낸다."""
    if not text:
        return None
    cleaned = re.sub(r"^[\s\-–>→·:]+", "", text).strip()
    return cleaned or None


def to_float(value):
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


def to_int(value):
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return int(value) if float(value).is_integer() else None


def find_max_daily_count(*texts):
    for text in texts:
        found = MAX_DAILY_COUNT_PATTERN.search(text or "")
        if found:
            return int(found.group(1))
    return None


def build_medication(
    *,
    name,
    insurance_code,
    dose_per_time,
    unit,
    daily_count,
    total_days,
    as_needed,
    usage,
    dosage_form,
    route,
    confidence,
    max_daily_count,
):
    return {
        "name": display_drug_name(name),
        "insurance_code": insurance_code,
        "dose_per_time": to_float(dose_per_time),
        "unit": unit,
        # 명세 규칙: 필요시 복용약은 하루 횟수 대신 max_daily_count로 안내한다.
        "daily_count": None if as_needed else to_int(daily_count),
        "total_days": to_int(total_days),
        "max_daily_count": max_daily_count,
        "as_needed": as_needed,
        "usage": usage,
        "route": route,
        "dosage_form": dosage_form,
        "confidence": confidence,
    }


def format_prescription_medication(drug):
    name = drug.get("명칭") or None
    usage = clean_usage(drug.get("용법"))
    dosage_form = infer_dosage_form(name)
    return build_medication(
        name=name,
        insurance_code=drug.get("코드"),
        dose_per_time=drug.get("1회투약량"),
        unit=infer_prescription_unit(name, dosage_form),
        daily_count=drug.get("1일투여횟수"),
        total_days=drug.get("총투약일수"),
        as_needed=bool(AS_NEEDED_PATTERN.search(usage or "")),
        usage=usage,
        dosage_form=dosage_form,
        route=infer_route(dosage_form, name, usage),
        confidence=drug.get("신뢰도"),
        max_daily_count=find_max_daily_count(usage),
    )


def format_prescription_result(parsed):
    """prescription_parser.parse() 결과 → 명세 형식."""
    codes = parsed.get("질병분류기호") or []
    return {
        "prescription_date": parsed.get("교부일"),
        "hospital_name": (parsed.get("의료기관") or {}).get("명칭"),
        # 질병분류기호가 여러 개면 쉼표로 잇는다 (참고용 표시 값).
        "diagnosis_extracted": ",".join(codes) or None,
        "medications": [format_prescription_medication(drug) for drug in parsed.get("처방의약품") or []],
    }


def format_bag_guide_medication(drug, taking_time):
    """약봉투 오른쪽 '복약안내' 표의 약 한 줄."""
    name = drug.get("명칭")
    category, looks = drug.get("분류"), drug.get("성상")
    dosage_form = infer_dosage_form(name, category, looks)
    route = infer_route(dosage_form, name, category, looks)
    amount = drug.get("1회용량")
    as_needed = bool(drug.get("필요시"))

    usage_parts = []
    if amount == "적당량":
        usage_parts.append("적당량")
    if as_needed:
        usage_parts.append("필요시")
    elif route == ORAL and taking_time:
        # 약봉투 아래 '□식전 30분 □식후 30분' 체크 표시는 봉투 안의 먹는 약 전체에 해당한다.
        usage_parts.append(taking_time)

    return build_medication(
        name=name,
        insurance_code=None,
        dose_per_time=amount,
        # 약봉투 표에 단위가 없거나 흐릿하면 처방전처럼 약 이름·제형으로 짐작한다.
        unit=bag_unit(drug.get("단위"), name, dosage_form),
        daily_count=drug.get("1일횟수"),
        total_days=drug.get("일수"),
        as_needed=as_needed,
        usage=" ".join(usage_parts) or None,
        dosage_form=dosage_form,
        route=route,
        confidence=drug.get("신뢰도"),
        max_daily_count=find_max_daily_count(drug.get("복용법"), drug.get("주의사항")),
    )


def format_bag_receipt_medication(drug):
    """복약안내 표를 못 읽었을 때 쓰는 왼쪽 영수증의 '약품명 투약량 횟수 일수' 표의 약 한 줄."""
    name = drug.get("명칭")
    dosage_form = infer_dosage_form(name)
    return build_medication(
        name=name,
        insurance_code=None,
        dose_per_time=drug.get("투약량"),
        unit=DEFAULT_UNIT_BY_FORM.get(dosage_form),
        daily_count=drug.get("횟수"),
        total_days=drug.get("일수"),
        as_needed=False,
        usage=None,
        dosage_form=dosage_form,
        route=infer_route(dosage_form, name),
        confidence=drug.get("신뢰도"),
        max_daily_count=None,
    )


def format_medicine_bag_result(parsed):
    """medicine_bag_parser.parse() 결과 → 명세 형식.

    약봉투에는 처방일·질병분류기호가 없다. 대신 약 받은 날(조제일자)을 prescription_date로 돌려준다
    (11/26 결정: 앱은 약봉투의 날짜를 '약 받은 날'로 보여 주고 복약 일정을 이 날부터 시작한다).
    조제일자는 복약안내 쪽 값을 먼저 쓰고, 못 읽었으면 영수증 쪽 값을 쓴다. 질병분류기호는 None이다.
    """
    guide = parsed.get("복약안내") or {}
    receipt = parsed.get("영수증") or {}
    taking_time = (parsed.get("복용표시") or {}).get("복용시점")
    guide_drugs = parsed.get("약품") or []
    if guide_drugs:
        medications = [format_bag_guide_medication(drug, taking_time) for drug in guide_drugs]
    else:
        receipt_drugs = receipt.get("약품내역") or []
        medications = [format_bag_receipt_medication(drug) for drug in receipt_drugs]
    return {
        "prescription_date": guide.get("조제일자") or receipt.get("조제일자"),
        "hospital_name": guide.get("병원"),
        "diagnosis_extracted": None,
        "medications": medications,
    }
