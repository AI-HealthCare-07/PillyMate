"""OCR 원문에서 식별정보를 가린다 (NFR-SEC-007).

API 명세 7절: 식별정보는 run_ocr() 안에서 [이름], [주민번호]처럼 바꾸고 원문은 밖으로 내보내지 않는다.
명세가 정한 이름·주민번호에 더해, 팀 결정(11/24)으로 나이와 전화번호도 가린다.
- [주민번호] 230512-4083217, 230512-4******
- [전화번호] 031-764-2210, 010-1234-5678, (02)123-4567, 1588-1234 (병원·약국 번호도 함께 가린다)
- [나이]     만 3세, 만 3세 2개월, 생후 8개월, (18개월), (3세)
- [이름]     파서가 찾은 환자 이름, '성명' 라벨 바로 뒤 글자
라벨로 이름을 찾을 때 의료인 성명도 함께 가려질 수 있지만, 덜 가리는 것보다 더 가리는 쪽이 안전하다.
"""

import re

NAME_PLACEHOLDER = "[이름]"
RESIDENT_NUMBER_PLACEHOLDER = "[주민번호]"
PHONE_NUMBER_PLACEHOLDER = "[전화번호]"
AGE_PLACEHOLDER = "[나이]"

# 뒷자리를 일부 가린 형태(230512-4******)도 함께 찾는다.
RESIDENT_NUMBER = re.compile(r"\d{6}\s*-\s*[\d*]{7}")
# 0으로 시작하는 지역·휴대전화 번호와 1588 같은 대표번호. 앞뒤가 다른 숫자에 붙어 있으면 전화번호가 아니다.
# (영수증번호 2026-1112-0042, 사업자등록번호 123-45-67890은 0이나 15~19로 시작하지 않아서 걸리지 않는다.)
PHONE_NUMBER = re.compile(
    r"(?<![\d-])(?:\(\s*0\d{1,2}\s*\)\s*-?\s*|0\d{1,2}\s*-\s*)\d{3,4}\s*-\s*\d{4}(?![\d-])"
    r"|(?<![\d-])1[5-9]\d{2}\s*-\s*\d{4}(?![\d-])"
)
# 괄호 안에 숫자+개월/세만 있는 '(18개월)', '(3세)'도 나이로 본다.
# '개봉 후 1개월'(보관 기간)처럼 괄호 밖의 개월 수는 가리지 않는다.
AGE = re.compile(
    r"만\s*\d{1,3}\s*세(?:\s*\d{1,2}\s*개월)?|생후\s*\d{1,3}\s*개월"
    r"|(?<=\()\s*\d{1,3}\s*(?:개월|세)\s*(?=\))"
)
# '성 명', '환자성명', '환자정보 :' 같은 라벨 바로 뒤의 한글 2~5자.
# 이름 칸이 비어 바로 다음 라벨(주민등록번호 등)이 오는 경우는 가리지 않는다.
NAME_AFTER_LABEL = re.compile(
    r"(환\s*자\s*성\s*명|성\s*명|환\s*자\s*정\s*보)(\s*:?\s*)(?!주민|팩스|전화|면허|생년|나이|성별|주소|서명)([가-힣]{2,5})"
)


# 저장용 CLOVA 응답에는 [이름] 대신 같은 모양의 가짜 값을 넣는다.
# 파서는 '['로 시작하는 글자를 약봉투의 [분류] 칸으로 보기 때문에, [이름]을 넣으면 결과가 달라진다.
DUMMY_PATIENT_NAME = "홍길동"
DUMMY_RESIDENT_NUMBER = "000000-0000000"


def mask_personal_info_in_fields(fields, patient_names=()):
    """CLOVA 글자 상자마다 환자 정보를 가짜 값으로 바꾼 복사본을 돌려준다 (좌표는 그대로).

    테스트용으로 저장하는 CLOVA 응답에 환자 정보가 남지 않게 할 때 쓴다.
    상자 하나에는 라벨과 이름이 따로 들어 있으므로 파서가 찾은 이름과 주민번호 형태만 바꾼다.
    """
    names = sorted({n.strip() for n in patient_names if n and len(n.strip()) >= 2}, key=len, reverse=True)
    masked_fields = []
    for field in fields:
        text = RESIDENT_NUMBER.sub(DUMMY_RESIDENT_NUMBER, field["inferText"])
        for name in names:
            text = text.replace(name, DUMMY_PATIENT_NAME)
        masked_fields.append({**field, "inferText": text})
    return masked_fields


def mask_personal_info(text, patient_names=()):
    """text에서 주민등록번호·전화번호·나이·환자 이름을 가린 글자를 돌려준다.

    patient_names: 파서가 찾은 환자 이름들. None이나 한 글자 값은 무시한다.
    """
    if not text:
        return text
    masked = RESIDENT_NUMBER.sub(RESIDENT_NUMBER_PLACEHOLDER, text)
    masked = PHONE_NUMBER.sub(PHONE_NUMBER_PLACEHOLDER, masked)
    masked = AGE.sub(AGE_PLACEHOLDER, masked)
    for name in sorted({n.strip() for n in patient_names if n and len(n.strip()) >= 2}, key=len, reverse=True):
        masked = masked.replace(name, NAME_PLACEHOLDER)
    return NAME_AFTER_LABEL.sub(lambda m: m.group(1) + m.group(2) + NAME_PLACEHOLDER, masked)
