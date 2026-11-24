from fastapi import FastAPI, status
from httpx import ASGITransport, AsyncClient

from app.dependencies.security import LOGIN_REQUIRED_MESSAGE, CurrentGuardian


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.get("/protected")
    async def protected(guardian: CurrentGuardian) -> dict[str, int]:
        return {"id": guardian.id}

    return app


class TestGetRequestUser:
    async def test_no_token_returns_401_korean(self) -> None:
        async with AsyncClient(transport=ASGITransport(app=_make_app()), base_url="http://test") as client:
            response = await client.get("/protected")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": LOGIN_REQUIRED_MESSAGE}

    async def test_invalid_token_returns_401_korean(self) -> None:
        async with AsyncClient(transport=ASGITransport(app=_make_app()), base_url="http://test") as client:
            response = await client.get("/protected", headers={"Authorization": "Bearer not-a-jwt"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == {"detail": LOGIN_REQUIRED_MESSAGE}
