"""run_ocr(): 사진 → CLOVA OCR → 처방전·약봉투 파서 → 개인정보 마스킹 → API 명세 형식.

API 명세 7절의 AI-1 내부 모듈. BE-2가 `POST /prescriptions`(def, 동기) 안에서 함수로 호출한다.
"""

from ocr import medicine_bag_parser, prescription_parser
from ocr.clova_ocr_client import DEFAULT_TIMEOUT_SECONDS, ClovaCredentials, request_clova_ocr
from ocr.ocr_exceptions import OcrInputError, OcrParseError, OcrRecognitionError
from ocr.ocr_result_formatter import format_medicine_bag_result, format_prescription_result
from ocr.personal_info_masking import mask_personal_info
from ocr.text_layout_utils import fields_to_plain_text

PRESCRIPTION = "PRESCRIPTION"
PILL_BAG = "PILL_BAG"
SOURCE_TYPES = (PRESCRIPTION, PILL_BAG)

# 파서가 예상하지 못한 배치를 만났을 때 날 수 있는 오류들.
PARSER_ERRORS = (KeyError, TypeError, ValueError, IndexError, ZeroDivisionError, StopIteration, AttributeError)


def detect_image_format(image_bytes):
    """파일 앞부분(매직 넘버)으로 CLOVA에 알려 줄 형식을 정한다. jpg·png만 받는다."""
    if not image_bytes:
        raise OcrInputError("이미지 파일이 비어 있어요.")
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "jpg"
    raise OcrInputError("JPG 또는 PNG 이미지만 인식할 수 있어요.")


def validate_source_type(source_type):
    if source_type not in SOURCE_TYPES:
        raise OcrInputError(f"source_type은 {' 또는 '.join(SOURCE_TYPES)}만 쓸 수 있어요.")


def parse_document(fields, source_type):
    """문서 종류에 맞는 파서로 정리하고, 마스킹에 쓸 환자 이름들과 함께 돌려준다."""
    if source_type == PRESCRIPTION:
        parsed = prescription_parser.parse(fields)
        return parsed, [parsed["환자"]["성명"]]
    parsed = medicine_bag_parser.parse(fields)
    return parsed, [parsed["복약안내"]["환자"]["성명"], parsed["영수증"]["환자성명"]]


def build_result_from_fields(fields, source_type):
    """CLOVA fields → 명세 형식. 네트워크 없이 저장해 둔 CLOVA 응답으로 테스트할 때도 쓴다."""
    validate_source_type(source_type)
    if not fields:
        raise OcrRecognitionError("이미지에서 글자를 찾지 못했어요.")

    try:
        parsed, patient_names = parse_document(fields, source_type)
        raw_text_masked = mask_personal_info(fields_to_plain_text(fields), patient_names)
        if source_type == PRESCRIPTION:
            return format_prescription_result(parsed, raw_text_masked)
        return format_medicine_bag_result(parsed, raw_text_masked)
    except PARSER_ERRORS as error:
        # 원래 예외 메시지에는 읽은 글자가 들어 있을 수 있어서 종류만 남긴다.
        raise OcrParseError(f"인식 결과를 항목으로 정리하지 못했어요 ({type(error).__name__}).") from None


def run_ocr(image_bytes, source_type, *, credentials=None, timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
    """처방전·약봉투 사진을 읽어 API 명세 7절 형식의 dict를 돌려준다. 동기 함수다.

    image_bytes: jpg 또는 png 파일 내용
    source_type: "PRESCRIPTION"(처방전) 또는 "PILL_BAG"(약봉투)
    credentials: ClovaCredentials. 생략하면 환경변수 CLOVA_OCR_URL, CLOVA_OCR_SECRET을 읽는다.
    timeout_seconds: CLOVA 응답을 기다릴 최대 시간(초)

    실패하면 OcrError의 하위 예외를 던진다 (ocr_exceptions 참고).
    """
    validate_source_type(source_type)
    image_format = detect_image_format(image_bytes)
    credentials = credentials or ClovaCredentials.from_environment()
    fields = request_clova_ocr(image_bytes, image_format, credentials, timeout_seconds)
    return build_result_from_fields(fields, source_type)
