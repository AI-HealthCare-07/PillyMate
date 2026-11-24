"""저장해 둔 실제 CLOVA 응답(tests/clova_responses)으로 파서 결과를 정답 파일과 비교한다.

응답 파일은 save_clova_responses 도구로 만든다. 파일이 없으면 이 테스트는 건너뛴다.
정확도를 퍼센트로 보고 싶으면 `python -m ocr.tools.check_parser_accuracy`를 쓴다.

약 이름은 CLOVA가 글자 한두 개를 잘못 읽는 경우가 있다(예: 밀리그램 → 밀리그림).
이건 파서가 아니라 인식 단계의 오류라서, 이름은 거의 같으면 통과시키고 나머지 항목은 정확히 비교한다.
이름이 칸 경계를 잘못 잡아 크게 달라지면(다른 칸 글자가 섞이는 등) 실패한다.
"""

import json
from difflib import SequenceMatcher
from pathlib import Path

import pytest

from ocr.ocr_pipeline import build_result_from_fields
from ocr.personal_info_masking import DUMMY_RESIDENT_NUMBER, RESIDENT_NUMBER
from ocr.tools.check_parser_accuracy import compare_result

TESTS_DIR = Path(__file__).resolve().parent
RESPONSE_PATHS = sorted((TESTS_DIR / "clova_responses").glob("*.json"))
NAME_SIMILARITY_THRESHOLD = 0.85


def is_close_name(actual, expected):
    return bool(actual and expected) and SequenceMatcher(None, actual, expected).ratio() >= NAME_SIMILARITY_THRESHOLD


@pytest.mark.skipif(
    not RESPONSE_PATHS, reason="저장된 CLOVA 응답이 없어요 (ocr.tools.save_clova_responses로 만들 수 있어요)."
)
@pytest.mark.parametrize("response_path", RESPONSE_PATHS, ids=lambda path: path.stem)
def test_saved_response_matches_expected_result(response_path):
    expected_path = TESTS_DIR / "expected_results" / response_path.name
    if not expected_path.exists():
        pytest.skip("정답 파일이 없어요.")
    saved = json.loads(response_path.read_text(encoding="utf-8"))
    expected = json.loads(expected_path.read_text(encoding="utf-8"))

    actual = build_result_from_fields(saved["fields"], saved["source_type"])

    wrong = [
        f"{field}: {a!r} != {e!r}"
        for field, ok, a, e in compare_result(actual, expected)
        if not ok and not (field == "medications.name" and is_close_name(a, e))
    ]
    assert not wrong, "\n".join(wrong)


@pytest.mark.parametrize("response_path", RESPONSE_PATHS, ids=lambda path: path.stem)
def test_saved_response_has_only_dummy_resident_numbers(response_path):
    text = response_path.read_text(encoding="utf-8")

    assert set(RESIDENT_NUMBER.findall(text)) <= {DUMMY_RESIDENT_NUMBER}
