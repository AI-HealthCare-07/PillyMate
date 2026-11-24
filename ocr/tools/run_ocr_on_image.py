"""사진 한 장을 run_ocr()로 읽고 API 명세 형식의 결과를 출력한다. CLOVA를 실제로 호출한다.

    uv run --env-file ~/ocr/.env python -m ocr.tools.run_ocr_on_image 사진.png --source-type PRESCRIPTION

CLOVA 키는 환경변수 CLOVA_OCR_URL, CLOVA_OCR_SECRET에서 읽는다 (--env-file로 넘기면 된다).
"""

import argparse
import json
import sys
from pathlib import Path

from ocr import SOURCE_TYPES, OcrError, run_ocr


def main(argv=None):
    parser = argparse.ArgumentParser(description="사진 한 장을 OCR해서 API 명세 형식으로 출력해요.")
    parser.add_argument("image", type=Path, help="jpg 또는 png 사진 경로")
    parser.add_argument("--source-type", required=True, choices=SOURCE_TYPES, help="처방전 또는 약봉투")
    parser.add_argument("--hide-raw-text", action="store_true", help="마스킹한 원문(raw_text_masked)은 빼고 출력")
    args = parser.parse_args(argv)

    try:
        result = run_ocr(args.image.expanduser().read_bytes(), args.source_type)
    except OSError as error:
        print(f"사진을 열지 못했어요: {error}", file=sys.stderr)
        return 1
    except OcrError as error:
        print(f"OCR 실패 ({type(error).__name__}): {error}", file=sys.stderr)
        return 1

    if args.hide_raw_text:
        result.pop("raw_text_masked", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
