import re

from starlette import status
from tortoise.contrib.test import TestCase

from app.tests.auth_apis.helpers import get, post, signup_payload

LOGIN_REQUIRED = {"detail": "로그인이 필요해요."}


class TestMeAPI(TestCase):
    async def test_get_me_success(self) -> None:
        signup = await post("/auth/signup", json=signup_payload(email="me@example.com"))
        login = await post("/auth/login", json={"email": "me@example.com", "password": "pilly1234!"})
        token = login.json()["access_token"]

        response = await get("/me", headers={"Authorization": f"Bearer {token}"})

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["guardian_id"] == signup.json()["guardian_id"]
        assert body["email"] == "me@example.com"
        assert body["name"] == "김보호"
        assert body["birth_date"] == "1990-05-14"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00", body["created_at"])

    async def test_get_me_without_token_returns_401(self) -> None:
        response = await get("/me")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == LOGIN_REQUIRED

    async def test_get_me_with_invalid_token_returns_401(self) -> None:
        response = await get("/me", headers={"Authorization": "Bearer invalid"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json() == LOGIN_REQUIRED

    async def test_old_users_me_path_is_gone(self) -> None:
        response = await get("/users/me")
        assert response.status_code == status.HTTP_404_NOT_FOUND
