"""사진을 올려 run_ocr() 결과를 브라우저에서 바로 확인하는 개발용 서버 (AI-1 테스트용).

API 서버(app)와 상관없이 혼자 돌아간다. 사진을 올릴 때마다 CLOVA를 한 번 호출한다.

    uv run --env-file ~/ocr/.env python -m ocr.tools.ocr_preview_server     # → http://127.0.0.1:8010

- GET  /                          테스트 페이지 (ocr_preview_page.html)
- POST /api/ocr?source_type=...   본문에 사진 파일 그대로 → {"result": run_ocr 결과, "elapsed_ms": 걸린 시간}
  실패하면 422(OcrInputError) 또는 502(그 밖의 OcrError)와 {"error_type", "message"}

로컬(127.0.0.1)에서만 열리며, 요청 본문이나 OCR 결과는 서버 로그에 남기지 않는다.
"""

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from ocr import OcrError, OcrInputError, run_ocr

PAGE_PATH = Path(__file__).with_name("ocr_preview_page.html")
DEFAULT_PORT = 8010
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # API 명세 5번: 10MB 이하


class OcrPreviewHandler(BaseHTTPRequestHandler):
    def send_body(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, status, data):
        self.send_body(status, json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self):
        if urlsplit(self.path).path == "/":
            self.send_body(200, PAGE_PATH.read_bytes(), "text/html; charset=utf-8")
        else:
            self.send_error(404)

    def do_HEAD(self):
        # 실행기·상태 확인용. 본문 없이 페이지가 있는지만 알려 준다.
        self.send_response(200 if urlsplit(self.path).path == "/" else 404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_POST(self):
        url = urlsplit(self.path)
        if url.path != "/api/ocr":
            self.send_error(404)
            return
        source_type = parse_qs(url.query).get("source_type", [""])[0]
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length > MAX_IMAGE_BYTES:
            self.send_json(422, {"error_type": "OcrInputError", "message": "10MB 이하 사진만 올릴 수 있어요."})
            return

        image_bytes = self.rfile.read(length) if length > 0 else b""
        started = time.perf_counter()
        try:
            result = run_ocr(image_bytes, source_type)
        except OcrInputError as error:
            self.send_json(422, {"error_type": type(error).__name__, "message": str(error)})
            return
        except OcrError as error:
            self.send_json(502, {"error_type": type(error).__name__, "message": str(error)})
            return
        elapsed_ms = round((time.perf_counter() - started) * 1000)
        self.send_json(200, {"result": result, "elapsed_ms": elapsed_ms})

    def log_message(self, format, *args):
        # 기본 로그(요청 줄·상태코드)만 남긴다. 본문과 결과는 출력하지 않는다.
        sys.stderr.write(f"{self.address_string()} {format % args}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="run_ocr() 결과를 브라우저에서 확인하는 개발용 서버예요.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args(argv)

    with ThreadingHTTPServer(("127.0.0.1", args.port), OcrPreviewHandler) as server:
        print(f"OCR 미리보기: http://127.0.0.1:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
