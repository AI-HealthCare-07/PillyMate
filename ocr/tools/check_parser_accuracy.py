"""저장해 둔 CLOVA 응답을 파서로 정리해서 정답 파일과 비교하고, 항목별 정확도를 출력한다.

인터넷 연결이나 CLOVA 키 없이 돌아가므로 파서를 고칠 때마다 반복해서 실행한다.

    uv run python -m ocr.tools.check_parser_accuracy            # 전체 요약
    uv run python -m ocr.tools.check_parser_accuracy --details  # 틀린 값까지 출력

- CLOVA 응답: ocr/tests/clova_responses/<사진 이름>.json (save_clova_responses로 만든다)
- 정답:       ocr/tests/expected_results/<사진 이름>.json (API 명세 형식, raw_text_masked 제외)
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from ocr import OcrError
from ocr.ocr_pipeline import build_result_from_fields

TESTS_DIR = Path(__file__).resolve().parent.parent / "tests"
DEFAULT_RESPONSES_DIR = TESTS_DIR / "clova_responses"
DEFAULT_EXPECTED_DIR = TESTS_DIR / "expected_results"

DOCUMENT_FIELDS = ("prescription_date", "hospital_name", "diagnosis_extracted")
MEDICATION_FIELDS = (
    "name",
    "insurance_code",
    "dose_per_time",
    "unit",
    "daily_count",
    "total_days",
    "max_daily_count",
    "as_needed",
    "usage",
    "route",
    "dosage_form",
)


def compare_result(actual, expected):
    """(항목 이름, 맞았는지, 실제 값, 정답) 목록. 약은 순서대로 짝지어 비교한다."""
    checks = [
        (field, actual.get(field) == expected.get(field), actual.get(field), expected.get(field))
        for field in DOCUMENT_FIELDS
    ]
    actual_meds, expected_meds = actual.get("medications", []), expected.get("medications", [])
    checks.append(("medications.count", len(actual_meds) == len(expected_meds), len(actual_meds), len(expected_meds)))
    for i, expected_med in enumerate(expected_meds):
        actual_med = actual_meds[i] if i < len(actual_meds) else {}
        for field in MEDICATION_FIELDS:
            checks.append(
                (
                    f"medications.{field}",
                    actual_med.get(field) == expected_med.get(field),
                    actual_med.get(field),
                    expected_med.get(field),
                )
            )
    return checks


def check_one_response(response_path, expected_path, totals, show_details):
    """사진 한 장의 결과를 정답과 비교해 totals에 더한다."""
    saved = json.loads(response_path.read_text(encoding="utf-8"))
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    source_type = saved["source_type"]
    success = totals[(source_type, "정리 성공")]
    success[1] += 1
    try:
        actual = build_result_from_fields(saved["fields"], source_type)
    except OcrError as error:
        print(f"{response_path.stem}: 실패 ({type(error).__name__})")
        return
    success[0] += 1

    wrong = []
    for field, ok, actual_value, expected_value in compare_result(actual, expected):
        totals[(source_type, field)][0] += ok
        totals[(source_type, field)][1] += 1
        if not ok:
            wrong.append(f"    {field}: {actual_value!r} (정답 {expected_value!r})")
    if show_details and wrong:
        print(f"{response_path.stem}:")
        print("\n".join(wrong))


def print_summary(totals):
    print()
    for source_type in sorted({key[0] for key in totals}):
        print(f"[{source_type}]")
        for (kind, field), (correct, count) in totals.items():
            if kind == source_type:
                print(f"  {field:28} {correct:4}/{count:<4} {correct / count:6.1%}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="저장한 CLOVA 응답으로 파서 정확도를 확인해요.")
    parser.add_argument("--responses-dir", type=Path, default=DEFAULT_RESPONSES_DIR)
    parser.add_argument("--expected-dir", type=Path, default=DEFAULT_EXPECTED_DIR)
    parser.add_argument("--details", action="store_true", help="틀린 값을 사진별로 출력")
    args = parser.parse_args(argv)

    response_paths = sorted(args.responses_dir.glob("*.json"))
    if not response_paths:
        print(f"{args.responses_dir}에 저장된 CLOVA 응답이 없어요. save_clova_responses를 먼저 실행해 주세요.")
        return 1

    totals = defaultdict(lambda: [0, 0])  # (source_type, 항목) → [맞은 수, 전체 수]
    for response_path in response_paths:
        expected_path = args.expected_dir / response_path.name
        if expected_path.exists():
            check_one_response(response_path, expected_path, totals, args.details)
        else:
            print(f"{response_path.stem}: 정답 파일이 없어 건너뜀")
    print_summary(totals)
    return 0


if __name__ == "__main__":
    sys.exit(main())
