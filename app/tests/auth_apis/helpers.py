from datetime import date

from dateutil.relativedelta import relativedelta
from httpx import ASGITransport, AsyncClient, Response

from app.main import app

BASE_URL = "http://test"


def signup_payload(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "email": "parent@example.com",
        "password": "pilly1234!",
        "name": "김보호",
        "birth_date": "1990-05-14",
    }
    data.update(overrides)
    return data


def birth_date_years_ago(years: int, days: int = 0) -> str:
    return (date.today() - relativedelta(years=years) + relativedelta(days=days)).isoformat()


async def post(path: str, json: object | None = None, headers: dict[str, str] | None = None) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
        return await client.post(f"/api/v1{path}", json=json, headers=headers)


async def get(path: str, headers: dict[str, str] | None = None) -> Response:
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL) as client:
        return await client.get(f"/api/v1{path}", headers=headers)
