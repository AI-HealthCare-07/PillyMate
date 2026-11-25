"""run_ocr()이 API 명세 7절 형식을 지키는지 확인한다. CLOVA 호출은 가짜로 바꾼다."""

import json

import pytest

from ocr import (
    ClovaCredentials,
    OcrInputError,
    OcrParseError,
    OcrRecognitionError,
    OcrRequestError,
    ocr_pipeline,
    run_ocr,
)
from ocr.tests.fake_clova_fields import fake_medicine_bag_fields, fake_prescription_fields

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 32
JPG_BYTES = b"\xff\xd8\xff\xe0" + b"0" * 32
CREDENTIALS = ClovaCredentials(invoke_url="https://clova.example.test/general", secret_key="test-secret")

SPEC_DOCUMENT_KEYS = {"prescription_date", "hospital_name", "diagnosis_extracted", "medications"}
SPEC_MEDICATION_KEYS = {
    "name", "insurance_code", "dose_per_time", "unit", "daily_count", "total_days",
    "max_daily_count", "as_needed", "usage", "route", "dosage_form", "confidence",
}  # fmt: skip
ALLOWED_UNITS = {"mL", "포", "정", "캡슐", "g", "방울", "개", None}
ALLOWED_ROUTES = {"ORAL", "EXTERNAL", None}
ALLOWED_FORMS = {
    "SYRUP", "DRY_SYRUP", "POWDER", "TABLET", "CAPSULE", "OINTMENT", "CREAM", "EYE_DROP", "SUPPOSITORY", "ETC", None,
}  # fmt: skip


@pytest.fixture
def fake_clova(monkeypatch):
    """request_clova_ocr를 가짜로 바꾸고, 넘어온 인자를 기록한다."""
    calls = []

    def use(fields):
        def _request(image_bytes, image_format, credentials, timeout_seconds):
            calls.append({"image_format": image_format, "credentials": credentials, "timeout": timeout_seconds})
            return fields

        monkeypatch.setattr(ocr_pipeline, "request_clova_ocr", _request)
        return calls

    return use


def assert_matches_api_spec(result):
    assert set(result) == SPEC_DOCUMENT_KEYS
    for medication in result["medications"]:
        assert set(medication) == SPEC_MEDICATION_KEYS
        assert medication["unit"] in ALLOWED_UNITS
        assert medication["route"] in ALLOWED_ROUTES
        assert medication["dosage_form"] in ALLOWED_FORMS
        assert isinstance(medication["as_needed"], bool)
        if medication["as_needed"]:
            assert medication["daily_count"] is None


def test_prescription_result_matches_api_spec(fake_clova):
    calls = fake_clova(fake_prescription_fields())

    result = run_ocr(PNG_BYTES, "PRESCRIPTION", credentials=CREDENTIALS, timeout_seconds=9)

    assert_matches_api_spec(result)
    assert calls == [{"image_format": "png", "credentials": CREDENTIALS, "timeout": 9}]
    assert result["prescription_date"] == "2026-11-12"
    assert result["hospital_name"] == "해솔소아청소년과의원"
    assert result["diagnosis_extracted"] == "J00,J209"
    first, second = result["medications"]
    assert first == {
        "name": "세파클러건조시럽",
        "insurance_code": "643901230",
        "dose_per_time": 4.2,
        "unit": "mL",
        "daily_count": 3,
        "total_days": 5,
        "max_daily_count": None,
        "as_needed": False,
        "usage": "식후 30분",
        "route": "ORAL",
        "dosage_form": "DRY_SYRUP",
        "confidence": 0.95,
    }
    assert (second["as_needed"], second["daily_count"], second["max_daily_count"]) == (True, None, 4)


def test_pill_bag_result_matches_api_spec(fake_clova):
    fake_clova(fake_medicine_bag_fields())

    result = run_ocr(JPG_BYTES, "PILL_BAG", credentials=CREDENTIALS)

    assert_matches_api_spec(result)
    assert result["prescription_date"] is None
    assert result["diagnosis_extracted"] is None
    assert result["hospital_name"] == "해솔소아청소년과의원"
    assert [(m["name"], m["route"], m["dosage_form"]) for m in result["medications"]] == [
        ("세파클러건조시럽", "ORAL", "DRY_SYRUP"),
        ("세토펜현탁액", "ORAL", "SYRUP"),
        ("후시딘연고", "EXTERNAL", "OINTMENT"),
    ]


@pytest.mark.parametrize(
    ("fields", "source_type"),
    [(fake_prescription_fields(), "PRESCRIPTION"), (fake_medicine_bag_fields(), "PILL_BAG")],
)
def test_patient_name_and_resident_number_never_leave_the_module(fake_clova, fields, source_type):
    fake_clova(fields)

    result = run_ocr(PNG_BYTES, source_type, credentials=CREDENTIALS)

    everything = json.dumps(result, ensure_ascii=False)
    assert "김하윤" not in everything
    assert "230512" not in everything


@pytest.mark.parametrize(
    ("fields", "source_type"),
    [(fake_prescription_fields(), "PRESCRIPTION"), (fake_medicine_bag_fields(), "PILL_BAG")],
)
def test_ocr_raw_text_is_not_returned(fake_clova, fields, source_type):
    """원문은 마스킹본도 돌려주지 않는다. 결과에는 정리된 항목만 있다."""
    fake_clova(fields)

    result = run_ocr(PNG_BYTES, source_type, credentials=CREDENTIALS)

    assert "raw_text_masked" not in result
    assert "[이름]" not in json.dumps(result, ensure_ascii=False)


def test_unknown_source_type_is_input_error():
    with pytest.raises(OcrInputError):
        run_ocr(PNG_BYTES, "RECEIPT", credentials=CREDENTIALS)


@pytest.mark.parametrize("image_bytes", [b"", b"GIF89a....", b"%PDF-1.7"])
def test_only_jpg_and_png_are_accepted(image_bytes):
    with pytest.raises(OcrInputError):
        run_ocr(image_bytes, "PRESCRIPTION", credentials=CREDENTIALS)


def test_image_without_text_is_recognition_error(fake_clova):
    fake_clova([])

    with pytest.raises(OcrRecognitionError):
        run_ocr(PNG_BYTES, "PRESCRIPTION", credentials=CREDENTIALS)


def test_parser_crash_becomes_parse_error_without_ocr_text(fake_clova, monkeypatch):
    fake_clova(fake_prescription_fields())

    def broken_parse(fields):
        raise ValueError("김하윤 230512-4083217")  # 원래 메시지에 환자 정보가 있어도

    monkeypatch.setattr(ocr_pipeline.prescription_parser, "parse", broken_parse)

    with pytest.raises(OcrParseError) as error_info:
        run_ocr(PNG_BYTES, "PRESCRIPTION", credentials=CREDENTIALS)
    assert "김하윤" not in str(error_info.value)
    assert error_info.value.__cause__ is None


def test_clova_failure_propagates_as_ocr_error(monkeypatch):
    def failing_request(*args):
        raise OcrRequestError("CLOVA OCR이 25초 안에 응답하지 않았어요.")

    monkeypatch.setattr(ocr_pipeline, "request_clova_ocr", failing_request)

    with pytest.raises(OcrRequestError):
        run_ocr(PNG_BYTES, "PRESCRIPTION", credentials=CREDENTIALS)


def test_reads_credentials_from_environment_when_not_given(fake_clova, monkeypatch):
    calls = fake_clova(fake_prescription_fields())
    monkeypatch.setenv("CLOVA_OCR_URL", CREDENTIALS.invoke_url)
    monkeypatch.setenv("CLOVA_OCR_SECRET", CREDENTIALS.secret_key)

    run_ocr(PNG_BYTES, "PRESCRIPTION")

    assert calls[0]["credentials"] == CREDENTIALS
