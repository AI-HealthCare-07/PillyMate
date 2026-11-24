from httpx import ASGITransport, AsyncClient
from starlette import status

from app.core import config
from app.main import app


class TestAppSetup:
    async def test_health(self) -> None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok"}

    async def test_cors_allows_configured_origin_once(self) -> None:
        origin = config.cors_origins[0]
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.options(
                "/api/v1/auth/login",
                headers={"Origin": origin, "Access-Control-Request-Method": "POST"},
            )
        assert response.status_code == status.HTTP_200_OK
        assert response.headers.get_list("access-control-allow-origin") == [origin]

    def test_cors_origins_are_parsed_from_comma_string(self) -> None:
        assert isinstance(config.CORS_ORIGINS, str)
        assert config.cors_origins == [o.strip() for o in config.CORS_ORIGINS.split(",") if o.strip()]
