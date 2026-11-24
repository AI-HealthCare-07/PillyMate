from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app


class TestLoginAPI(TestCase):
    async def test_login_success(self):
        # 먼저 사용자 등록
        signup_data = {
            "email": "login_test@example.com",
            "password": "Password123!",
            "name": "로그인테스터",
            "gender": "FEMALE",
            "birth_date": "1995-05-05",
            "phone_number": "01011112222",
        }
        login_data = {"email": "login_test@example.com", "password": "Password123!"}

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/auth/signup", json=signup_data)

            # 로그인 시도
            response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.json()
        # 쿠키 검증 대신 응답 헤더 확인
        assert any("refresh_token" in header for header in response.headers.get_list("set-cookie"))

    async def test_login_refresh_cookie_expires_with_refresh_token(self):
        # 리프레시 쿠키 만료는 access token(60분)이 아닌 refresh token(14일) 기준이어야 함
        signup_data = {
            "email": "cookie_exp@example.com",
            "password": "Password123!",
            "name": "쿠키테스터",
            "gender": "MALE",
            "birth_date": "1994-04-04",
            "phone_number": "01022223333",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await client.post("/api/v1/auth/signup", json=signup_data)
            response = await client.post(
                "/api/v1/auth/login", json={"email": "cookie_exp@example.com", "password": "Password123!"}
            )
        cookie = next(h for h in response.headers.get_list("set-cookie") if h.startswith("refresh_token="))
        expires_attr = next(p.split("=", 1)[1] for p in cookie.split("; ") if p.lower().startswith("expires="))
        remaining = parsedate_to_datetime(expires_attr) - datetime.now(UTC)
        assert timedelta(days=13) < remaining <= timedelta(days=14, minutes=1)

    async def test_signup_without_email_returns_422(self):
        signup_data = {
            "password": "Password123!",
            "name": "이메일없음",
            "gender": "MALE",
            "birth_date": "1994-04-04",
            "phone_number": "01099990000",
        }
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/signup", json=signup_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_login_invalid_credentials(self):
        login_data = {"email": "nonexistent@example.com", "password": "WrongPassword123!"}
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/auth/login", json=login_data)

        # AuthService.authenticate 에서 실패 시 HTTP_400_BAD_REQUEST 발생
        assert response.status_code == status.HTTP_400_BAD_REQUEST
