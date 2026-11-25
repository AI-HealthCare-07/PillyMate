import io
import json
from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

from ocr import clova_ocr_client
from ocr.clova_ocr_client import ClovaCredentials, request_clova_ocr
from ocr.ocr_exceptions import OcrConfigurationError, OcrRecognitionError, OcrRequestError

CREDENTIALS = ClovaCredentials(invoke_url="https://clova.example.test/general", secret_key="test-secret")


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def fake_urlopen(body=None, error=None, captured=None):
    def _urlopen(request, timeout):
        if captured is not None:
            captured.update(request=request, timeout=timeout)
        if error:
            raise error
        return FakeResponse(body if isinstance(body, bytes) else json.dumps(body).encode())

    return _urlopen


def success_body(fields):
    return {"images": [{"inferResult": "SUCCESS", "fields": fields}]}


def test_sends_image_with_secret_header_and_timeout(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        clova_ocr_client, "urlopen", fake_urlopen(success_body([{"inferText": "처방전"}]), captured=captured)
    )

    fields = request_clova_ocr(b"\x89PNG...", "png", CREDENTIALS, timeout_seconds=7)

    assert fields == [{"inferText": "처방전"}]
    request = captured["request"]
    assert request.full_url == CREDENTIALS.invoke_url
    assert request.get_header("X-ocr-secret") == "test-secret"
    assert captured["timeout"] == 7
    payload = json.loads(request.data)
    assert payload["version"] == "V2"
    assert payload["images"][0]["format"] == "png"


@pytest.mark.parametrize(
    ("error", "message_part"),
    [
        (HTTPError("https://clova.example.test", 401, "Unauthorized", Message(), io.BytesIO()), "HTTP 401"),
        (TimeoutError(), "초 안에 응답하지 않았어요"),
        (URLError(TimeoutError()), "초 안에 응답하지 않았어요"),
        (URLError("dns failure"), "연결하지 못했어요"),
    ],
)
def test_network_failures_become_ocr_request_error(monkeypatch, error, message_part):
    monkeypatch.setattr(clova_ocr_client, "urlopen", fake_urlopen(error=error))

    with pytest.raises(OcrRequestError, match=message_part):
        request_clova_ocr(b"img", "jpg", CREDENTIALS)


@pytest.mark.parametrize(
    "body",
    [b"not json", {"images": []}, {"images": [{"inferResult": "FAILURE", "message": "bad image"}]}],
)
def test_unexpected_responses_become_ocr_recognition_error(monkeypatch, body):
    monkeypatch.setattr(clova_ocr_client, "urlopen", fake_urlopen(body))

    with pytest.raises(OcrRecognitionError):
        request_clova_ocr(b"img", "jpg", CREDENTIALS)


def test_credentials_from_environment(monkeypatch):
    monkeypatch.setenv("CLOVA_OCR_URL", " https://clova.example.test/general ")
    monkeypatch.setenv("CLOVA_OCR_SECRET", "test-secret")

    assert ClovaCredentials.from_environment() == CREDENTIALS


def test_missing_credentials_raise_configuration_error(monkeypatch):
    monkeypatch.delenv("CLOVA_OCR_URL", raising=False)
    monkeypatch.delenv("CLOVA_OCR_SECRET", raising=False)

    with pytest.raises(OcrConfigurationError):
        ClovaCredentials.from_environment()


def test_secret_key_is_hidden_in_repr():
    assert "test-secret" not in repr(CREDENTIALS)
