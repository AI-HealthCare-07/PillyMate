"""샘플 사진들을 CLOVA OCR에 한 번씩 보내고, 받은 글자 상자(fields)를 JSON 파일로 저장한다.

CLOVA는 부를 때마다 요금이 나가므로 사진마다 한 번만 보내고, 이후 파서 개선은 저장한 파일로 반복한다.
이미 저장된 사진은 건너뛴다 (--overwrite로 다시 받을 수 있다).

    uv run --env-file ~/ocr/.env python -m ocr.tools.save_clova_responses \\
        --source-type PRESCRIPTION ~/ocr/"PillyMate Image"/처방전/*

저장할 때 파서가 찾은 환자 이름과 주민등록번호 형태의 글자는 [이름], [주민번호]로 바꾼다 (좌표는 그대로).
그래도 주소·연락처 같은 글자는 남으므로, 실제 환자 사진의 응답은 저장소에 커밋하지 않는다.
"""

import argparse
import json
import sys
from pathlib import Path

from ocr import SOURCE_TYPES, ClovaCredentials, OcrError
from ocr.clova_ocr_client import request_clova_ocr
from ocr.ocr_pipeline import PARSER_ERRORS, detect_image_format, parse_document
from ocr.personal_info_masking import mask_personal_info_in_fields

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "tests" / "clova_responses"


def remove_patient_info(fields, source_type):
    """파서로 환자 이름을 찾아 글자 상자에서 이름과 주민등록번호를 가린다."""
    try:
        _, patient_names = parse_document(fields, source_type)
    except PARSER_ERRORS:
        patient_names = []
    return mask_personal_info_in_fields(fields, patient_names)


def save_response(image_path, source_type, output_dir, credentials, overwrite):
    output_path = output_dir / f"{image_path.stem}.json"
    if output_path.exists() and not overwrite:
        return "건너뜀 (이미 있음)"
    image_bytes = image_path.read_bytes()
    fields = request_clova_ocr(image_bytes, detect_image_format(image_bytes), credentials)
    fields = remove_patient_info(fields, source_type)
    output_path.write_text(
        json.dumps({"source_type": source_type, "image_name": image_path.name, "fields": fields}, ensure_ascii=False),
        encoding="utf-8",
    )
    return f"저장 ({len(fields)}개 글자 상자)"


def main(argv=None):
    parser = argparse.ArgumentParser(description="샘플 사진의 CLOVA OCR 응답을 저장해요.")
    parser.add_argument("images", nargs="+", type=Path, help="jpg·png 사진 경로들")
    parser.add_argument("--source-type", required=True, choices=SOURCE_TYPES)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--overwrite", action="store_true", help="이미 저장한 사진도 다시 보내기")
    args = parser.parse_args(argv)

    try:
        credentials = ClovaCredentials.from_environment()
    except OcrError as error:
        print(error, file=sys.stderr)
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)

    failed = 0
    for image_path in sorted(path.expanduser() for path in args.images):
        if image_path.suffix.lower() not in (".jpg", ".jpeg", ".png"):
            continue
        try:
            status = save_response(image_path, args.source_type, args.output_dir, credentials, args.overwrite)
        except (OSError, OcrError) as error:
            failed += 1
            status = f"실패 ({type(error).__name__}: {error})"
        print(f"{image_path.name}: {status}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
