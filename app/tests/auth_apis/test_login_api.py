from starlette import status
from tortoise.contrib.test import TestCase

from app.core import config
from app.services.jwt import JwtService
from app.tests.auth_apis.helpers import post, signup_payload

LOGIN_FAILED = {"detail": "이메일 또는 비밀번호가 맞지 않아요."}


class TestLoginAPI(TestCase):
    async def test_login_success_response_shape(self) -> None:
        signup = await post("/auth/signup", json=signup_payload(email="login@example.com"))
        guardian_id = signup.json()["guardian_id"]

        response = await post("/auth/login", json={"email": "login@example.com", "password": "pilly1234!"})

        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["expires_in"] == 43200
        assert body["guardian"] == {"guardian_id": guardian_id, "name": "김보호", "child_count": 0}
        assert JwtService().verify_access_token(body["access_token"]).payload["guardian_id"] == guardian_id
        assert "set-cookie" not in response.headers  # 리프레시 토큰 없음

    async def test_login_email_is_case_insensitive(self) -> None:
        await post("/auth/signup", json=signup_payload(email="case@example.com"))
        response = await post("/auth/login", json={"email": "CASE@Example.com", "password": "pilly1234!"})
        assert response.status_code == status.HTTP_200_OK

    async def test_wrong_password_and_unknown_email_return_same_401(self) -> None:
        await post("/auth/signup", json=signup_payload(email="wrong@example.com"))
        wrong_password = await post("/auth/login", json={"email": "wrong@example.com", "password": "nope12345"})
        unknown_email = await post("/auth/login", json={"email": "nobody@example.com", "password": "pilly1234!"})
        assert wrong_password.status_code == unknown_email.status_code == status.HTTP_401_UNAUTHORIZED
        assert wrong_password.json() == unknown_email.json() == LOGIN_FAILED

    async def test_missing_password_returns_400(self) -> None:
        response = await post("/auth/login", json={"email": "a@example.com"})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "필수 항목을 입력해 주세요: password"}


class TestDemoLoginAPI(TestCase):
    async def test_demo_login_disabled_returns_404(self) -> None:
        original = config.DEMO_LOGIN_ENABLED
        config.DEMO_LOGIN_ENABLED = False
        try:
            response = await post("/auth/demo-login")
        finally:
            config.DEMO_LOGIN_ENABLED = original
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.json() == {"detail": "데모 로그인을 사용할 수 없어요."}

    async def test_demo_login_without_seed_returns_404(self) -> None:
        original = config.DEMO_LOGIN_ENABLED
        config.DEMO_LOGIN_ENABLED = True
        try:
            response = await post("/auth/demo-login")
        finally:
            config.DEMO_LOGIN_ENABLED = original
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_demo_login_enabled_logs_in_demo_guardian(self) -> None:
        await post("/auth/signup", json=signup_payload(email=config.DEMO_GUARDIAN_EMAIL, name="데모"))
        original = config.DEMO_LOGIN_ENABLED
        config.DEMO_LOGIN_ENABLED = True
        try:
            response = await post("/auth/demo-login")
        finally:
            config.DEMO_LOGIN_ENABLED = original
        assert response.status_code == status.HTTP_200_OK
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["guardian"]["name"] == "데모"
