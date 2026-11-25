import re

from starlette import status
from tortoise.contrib.test import TestCase

from app.models.children import Child
from app.tests.auth_apis.helpers import birth_date_years_ago, get, post, signup_payload


async def login(email: str) -> dict[str, str]:
    await post("/auth/signup", json=signup_payload(email=email))
    response = await post("/auth/login", json={"email": email, "password": "pilly1234!"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def child_payload(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "name": "민준",
        "birth_date": "2021-03-02",
        "consent_agreed": True,
        "weight_kg": 18.5,
        "allergies": "계란",
        "notes": "열성 경련 이력 있음",
    }
    data.update(overrides)
    return data


class TestChildAPI(TestCase):
    async def test_register_child_and_list_only_mine(self) -> None:
        mine = await login("mom@example.com")
        other = await login("other@example.com")

        created = await post("/children", json=child_payload(), headers=mine)
        await post("/children", json=child_payload(name="서아", weight_kg=None, allergies="", notes=None), headers=mine)
        await post("/children", json=child_payload(name="남의아이"), headers=other)

        assert created.status_code == status.HTTP_201_CREATED
        body = created.json()
        assert body["name"] == "민준"
        assert body["birth_date"] == "2021-03-02"
        assert body["weight_kg"] == 18.5
        assert body["allergies"] == "계란"
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+09:00", body["created_at"])
        stored = await Child.get(id=body["child_id"])
        assert stored.consent_agreed_at is not None

        listed = await get("/children", headers=mine)
        assert listed.status_code == status.HTTP_200_OK
        assert [c["name"] for c in listed.json()] == ["민준", "서아"]
        assert listed.json()[1]["weight_kg"] is None
        assert listed.json()[1]["allergies"] is None

    async def test_empty_list(self) -> None:
        headers = await login("empty@example.com")
        response = await get("/children", headers=headers)
        assert response.json() == []

    async def test_requires_login(self) -> None:
        assert (await get("/children")).status_code == status.HTTP_401_UNAUTHORIZED
        assert (await post("/children", json=child_payload())).status_code == status.HTTP_401_UNAUTHORIZED

    async def test_rules_use_spec_messages(self) -> None:
        headers = await login("rules@example.com")
        cases = [
            (child_payload(consent_agreed=False), 422, "보호자 동의 3가지에 모두 동의해 주세요."),
            (child_payload(birth_date=birth_date_years_ago(18)), 422, "만 18세 미만 자녀만 등록할 수 있어요."),
            (child_payload(birth_date=birth_date_years_ago(0, days=3)), 422, "생년월일을 다시 확인해 주세요."),
            (child_payload(weight_kg=0.4), 422, "체중은 0.5~150kg 사이로 입력해 주세요."),
            (child_payload(weight_kg=150.1), 422, "체중은 0.5~150kg 사이로 입력해 주세요."),
            (child_payload(name="  "), 400, "필수 항목을 입력해 주세요: name"),
        ]
        for payload, code, message in cases:
            response = await post("/children", json=payload, headers=headers)
            assert (response.status_code, response.json()) == (code, {"detail": message}), payload

        assert await Child.filter(guardian__email="rules@example.com").count() == 0

    async def test_age_just_under_limit_is_allowed(self) -> None:
        headers = await login("edge@example.com")
        response = await post(
            "/children", json=child_payload(birth_date=birth_date_years_ago(18, days=1)), headers=headers
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_missing_consent_field_is_400(self) -> None:
        headers = await login("missing@example.com")
        payload = child_payload()
        del payload["consent_agreed"]
        response = await post("/children", json=payload, headers=headers)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json() == {"detail": "필수 항목을 입력해 주세요: consent_agreed"}
