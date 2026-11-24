"""공통 예외 처리기 (명세서 1절 "입력 오류 코드", 8절 에러 메시지).

- 필수값 누락: 400 + {"detail": "필수 항목을 입력해 주세요: email, name"}
- 그 밖의 자동 검증 오류: 422 (FastAPI 기본 형식, detail이 목록)
- 처리하지 못한 예외: 500 + {"detail": "서버에서 알 수 없는 오류가 발생했어요."}
"""

import logging
from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

MISSING_FIELDS_MESSAGE = "필수 항목을 입력해 주세요"
INTERNAL_ERROR_MESSAGE = "서버에서 알 수 없는 오류가 발생했어요."

# loc의 첫 칸은 값의 위치("body", "query", "path", "header", "cookie")라서 필드 이름에서 뺀다.
_LOCATION_PREFIXES = {"body", "query", "path", "header", "cookie"}


def _field_name(loc: Sequence[Any]) -> str:
    parts = list(loc)
    if parts and parts[0] in _LOCATION_PREFIXES:
        parts = parts[1:]
    return ".".join(str(part) for part in parts)


def missing_field_names(errors: Sequence[dict[str, Any]]) -> list[str]:
    """검증 오류 중 필수값 누락(type == "missing")인 필드 이름을 순서대로, 중복 없이 돌려준다."""
    names: list[str] = []
    for error in errors:
        if error.get("type") != "missing":
            continue
        name = _field_name(error.get("loc", ()))
        if name not in names:
            names.append(name)
    return names


async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    has_missing = any(error.get("type") == "missing" for error in errors)
    if has_missing:
        names = [name for name in missing_field_names(errors) if name]
        detail = f"{MISSING_FIELDS_MESSAGE}: {', '.join(names)}" if names else f"{MISSING_FIELDS_MESSAGE}."
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": detail})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={"detail": jsonable_encoder(errors)},
    )


async def internal_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": INTERNAL_ERROR_MESSAGE},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, internal_exception_handler)
