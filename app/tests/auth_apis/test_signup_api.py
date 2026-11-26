from starlette import status
from tortoise.contrib.test import TestCase

from app.models.guardians import Guardian
from app.tests.auth_apis.helpers import birth_date_years_ago, post, signup_payload


class TestSignupAPI(TestCase):
    async def test_signup_success(self) -> None:
        response = await post("/auth/signup", json=signup_payload())

        assert response.status_code == status.HTTP_201_CREATED
        body = response.json()
        assert set(body) == {"guardian_id", "email", "name", "birth_date", "gender", "phone_number"}
        assert body["email"] == "parent@example.com"
        assert body["name"] == "김보호"
        assert body["birth_date"] == "1990-05-14"
        assert body["gender"] == "FEMALE"
        assert body["phone_number"] == "01012345678"  # 숫자만 저장

        guardian = await Guardian.get(id=body["guardian_id"])
        assert guardian.password_hash != "pilly1234!"  # 해시로 저장

    async def test_email_is_saved_in_lowercase(self) -> None:
        response = await post("/auth/signup", json=signup_payload(email="Mom@Example.COM"))
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["email"] == "mom@example.com"

    async def test_duplicate_email_ignoring_case_returns_409(self) -> None:
        await post("/auth/signup", json=signup_payload(email="dup@example.com"))
        response = await post("/auth/signup", json=signup_payload(email="DUP@example.com"))
        assert response.status_code == status.HTTP_409_CONFLICT
        assert response.json() == {"detail": "이미 가입된 이메일이에요."}

    async def test_missing_field_returns_400(self) -> None:
        payload = signup_payload()
        del payload["birth_date"]
        response = await post("/auth/signup", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "필수 항목을 입력해 주세요: birth_date"}

    async def test_password_length_rule(self) -> None:
        for password in ("short7!", "a" * 65):
            response = await post(
                "/auth/signup", json=signup_payload(email=f"{len(password)}@ex.com", password=password)
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
            assert response.json() == {"detail": "비밀번호는 8~64자로 입력해 주세요."}

        ok = await post("/auth/signup", json=signup_payload(email="len64@ex.com", password="a" * 64))
        assert ok.status_code == status.HTTP_201_CREATED

    async def test_guardian_must_be_19_or_older(self) -> None:
        under = await post(
            "/auth/signup", json=signup_payload(email="u@ex.com", birth_date=birth_date_years_ago(19, 1))
        )
        assert under.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert under.json() == {"detail": "만 19세 이상만 가입할 수 있어요."}

        exactly = await post("/auth/signup", json=signup_payload(email="e@ex.com", birth_date=birth_date_years_ago(19)))
        assert exactly.status_code == status.HTTP_201_CREATED

    async def test_invalid_email_format_returns_422(self) -> None:
        response = await post("/auth/signup", json=signup_payload(email="invalid-email"))
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        assert isinstance(response.json()["detail"], list)

    async def test_phone_number_formats_are_normalized(self) -> None:
        for index, raw in enumerate(["010-9876-5432", "01098765432", "+821098765432"]):
            response = await post(
                "/auth/signup", json=signup_payload(email=f"phone{index}@example.com", phone_number=raw)
            )
            assert response.status_code == status.HTTP_201_CREATED
            assert response.json()["phone_number"] == "01098765432"

    async def test_invalid_phone_number_returns_422(self) -> None:
        for raw in ["02-123-4567", "010-123-4567", "abc", ""]:
            response = await post("/auth/signup", json=signup_payload(phone_number=raw))
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT, raw

    async def test_invalid_gender_returns_422(self) -> None:
        response = await post("/auth/signup", json=signup_payload(gender="OTHER"))
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    async def test_missing_gender_or_phone_returns_400(self) -> None:
        for field in ("gender", "phone_number"):
            payload = signup_payload()
            del payload[field]
            response = await post("/auth/signup", json=payload)
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert response.json() == {"detail": f"필수 항목을 입력해 주세요: {field}"}
