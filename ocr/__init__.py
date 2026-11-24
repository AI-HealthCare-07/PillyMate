"""PillyMate OCR 모듈 (AI-1).

사용법은 ocr/README.md를 참고한다. 밖에서는 아래 이름만 import해서 쓴다.

    from ocr import run_ocr, OcrError, OcrInputError

이 패키지는 app·ai_worker 코드를 import하지 않는다. 파이썬 기본 라이브러리만 쓴다.
"""

from ocr.clova_ocr_client import DEFAULT_TIMEOUT_SECONDS, ClovaCredentials
from ocr.ocr_exceptions import (
    OcrConfigurationError,
    OcrError,
    OcrInputError,
    OcrParseError,
    OcrRecognitionError,
    OcrRequestError,
)
from ocr.ocr_pipeline import PILL_BAG, PRESCRIPTION, SOURCE_TYPES, run_ocr

__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "PILL_BAG",
    "PRESCRIPTION",
    "SOURCE_TYPES",
    "ClovaCredentials",
    "OcrConfigurationError",
    "OcrError",
    "OcrInputError",
    "OcrParseError",
    "OcrRecognitionError",
    "OcrRequestError",
    "run_ocr",
]
