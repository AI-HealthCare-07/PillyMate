"""CLOVA OCR(General, V2)에 이미지를 보내고 글자 상자 목록(fields)을 받아오는 동기 클라이언트.

API 명세에서 OCR API를 `def`(동기)로 작성하기로 했으므로 이 클라이언트도 동기로 동작한다.
`async def` 안에서 바로 부르면 서버 전체가 멈추니, 그럴 때는 run_in_threadpool로 감싸서 부른다.
외부 패키지 없이 파이썬 기본 urllib만 써서 app·ai_worker 어느 컨테이너에서도 그대로 import된다.
"""

import base64
import json
import os
import time
import uuid
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ocr.ocr_exceptions import OcrConfigurationError, OcrRecognitionError, OcrRequestError

# API 명세: OCR은 요청 하나 안에서 30초 안에 끝나야 한다. 이미지 저장 등 앞뒤 작업 시간을 남겨 둔다.
DEFAULT_TIMEOUT_SECONDS = 25

URL_ENV_NAME = "CLOVA_OCR_URL"
SECRET_ENV_NAME = "CLOVA_OCR_SECRET"


@dataclass(frozen=True)
class ClovaCredentials:
    """CLOVA OCR 도메인의 APIGW Invoke URL과 Secret Key."""

    invoke_url: str
    secret_key: str

    def __repr__(self):
        # Secret Key가 로그나 오류 화면에 찍히지 않도록 가린다.
        return f"ClovaCredentials(invoke_url={self.invoke_url!r}, secret_key='***')"

    @classmethod
    def from_environment(cls):
        """환경변수 CLOVA_OCR_URL, CLOVA_OCR_SECRET에서 읽는다."""
        invoke_url = os.environ.get(URL_ENV_NAME, "").strip()
        secret_key = os.environ.get(SECRET_ENV_NAME, "").strip()
        if not invoke_url or not secret_key:
            raise OcrConfigurationError(f"환경변수 {URL_ENV_NAME}, {SECRET_ENV_NAME}를 설정해 주세요.")
        return cls(invoke_url=invoke_url, secret_key=secret_key)


def build_request_payload(image_bytes, image_format):
    return {
        "version": "V2",
        "requestId": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
        "images": [
            {
                "format": image_format,
                "name": "upload",
                "data": base64.b64encode(image_bytes).decode("ascii"),
            }
        ],
    }


def request_clova_ocr(image_bytes, image_format, credentials, timeout_seconds=DEFAULT_TIMEOUT_SECONDS):
    """이미지 한 장을 CLOVA OCR로 인식하고 글자 상자 목록(fields)을 돌려준다.

    image_format: "jpg" 또는 "png"
    반환값의 각 상자: {"inferText", "inferConfidence", "boundingPoly": {"vertices": [...]}, "lineBreak"}
    """
    request = Request(
        credentials.invoke_url,
        data=json.dumps(build_request_payload(image_bytes, image_format)).encode(),
        headers={"Content-Type": "application/json", "X-OCR-SECRET": credentials.secret_key},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = json.load(response)
    except HTTPError as error:
        status = error.code
        error.close()
        raise OcrRequestError(f"CLOVA OCR 요청이 실패했어요 (HTTP {status}).") from None
    except TimeoutError:
        raise OcrRequestError(f"CLOVA OCR이 {timeout_seconds}초 안에 응답하지 않았어요.") from None
    except URLError as error:
        if isinstance(error.reason, TimeoutError):
            raise OcrRequestError(f"CLOVA OCR이 {timeout_seconds}초 안에 응답하지 않았어요.") from None
        raise OcrRequestError("CLOVA OCR 서버에 연결하지 못했어요.") from None
    except OSError:
        raise OcrRequestError("CLOVA OCR 응답을 받는 중 연결이 끊어졌어요.") from None
    except ValueError:
        raise OcrRecognitionError("CLOVA OCR 응답이 JSON 형식이 아니에요.") from None

    return extract_fields(body)


def extract_fields(response_body):
    """CLOVA 응답 JSON에서 첫 번째 이미지의 fields를 꺼낸다."""
    try:
        image_result = response_body["images"][0]
        infer_result = image_result["inferResult"]
    except (KeyError, IndexError, TypeError):
        raise OcrRecognitionError("CLOVA OCR 응답 형식이 예상과 달라요.") from None
    if infer_result != "SUCCESS":
        raise OcrRecognitionError(f"CLOVA OCR이 이미지를 인식하지 못했어요 ({infer_result}).")
    return image_result.get("fields") or []
