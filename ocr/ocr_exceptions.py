"""run_ocr()이 던지는 예외 모음.

BE-2는 OcrError 하나만 잡아도 되고, 상태코드를 나눌 때는 아래처럼 구분한다.
- OcrInputError        → 422 (지원하지 않는 문서 종류·이미지 형식, 빈 파일)
- 그 밖의 OcrError     → 502 (CLOVA 설정 누락, 요청 실패·시간 초과, 인식 실패, 결과 정리 실패)

예외 메시지에는 OCR로 읽은 글자(환자 정보 등)를 절대 넣지 않는다. 로그에 그대로 남을 수 있기 때문이다.
"""


class OcrError(Exception):
    """OCR 모듈의 모든 예외의 부모."""


class OcrInputError(OcrError, ValueError):
    """호출하는 쪽이 잘못된 값을 넘겼다 (문서 종류, 이미지 형식, 빈 파일)."""


class OcrConfigurationError(OcrError):
    """CLOVA OCR 주소나 Secret Key가 설정되지 않았다."""


class OcrRequestError(OcrError):
    """CLOVA OCR 요청이 실패했거나 시간 안에 응답하지 않았다."""


class OcrRecognitionError(OcrError):
    """CLOVA가 응답은 했지만 글자를 인식하지 못했거나 응답 형식이 예상과 다르다."""


class OcrParseError(OcrError):
    """인식한 글자를 처방전·약봉투 항목으로 정리하다가 실패했다."""
