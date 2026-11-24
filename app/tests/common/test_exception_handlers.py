from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel, Field

from app.core.exception_handlers import (
    INTERNAL_ERROR_MESSAGE,
    register_exception_handlers,
)


class _Payload(BaseModel):
    email: str
    name: str
    age: int = Field(ge=0)


def _make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/echo")
    async def echo(payload: _Payload) -> dict[str, str]:
        return {"email": payload.email}

    @app.get("/boom")
    async def boom() -> None:
        raise RuntimeError("unexpected")

    return app


async def _post(json: object) -> tuple[int, dict]:
    async with AsyncClient(transport=ASGITransport(app=_make_app()), base_url="http://test") as client:
        response = await client.post("/echo", json=json)
    return response.status_code, response.json()


class TestValidationHandler:
    async def test_missing_fields_return_400_with_field_names(self) -> None:
        code, body = await _post({"age": 3})
        assert code == status.HTTP_400_BAD_REQUEST
        assert body == {"detail": "필수 항목을 입력해 주세요: email, name"}

    async def test_missing_and_invalid_together_return_400(self) -> None:
        code, body = await _post({"name": "a", "age": -1})
        assert code == status.HTTP_400_BAD_REQUEST
        assert body["detail"] == "필수 항목을 입력해 주세요: email"

    async def test_format_error_returns_422_list(self) -> None:
        code, body = await _post({"email": "a@b.com", "name": "a", "age": "not-a-number"})
        assert code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert isinstance(body["detail"], list)

    async def test_empty_body_returns_400(self) -> None:
        async with AsyncClient(transport=ASGITransport(app=_make_app()), base_url="http://test") as client:
            response = await client.post("/echo")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"].startswith("필수 항목을 입력해 주세요")


class TestInternalErrorHandler:
    async def test_unhandled_error_returns_500_korean_message(self) -> None:
        transport = ASGITransport(app=_make_app(), raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/boom")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.json() == {"detail": INTERNAL_ERROR_MESSAGE}
