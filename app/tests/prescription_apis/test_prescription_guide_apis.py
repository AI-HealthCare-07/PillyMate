"""처방 확정·가이드 생성·조회 API 테스트 (테스트용 MySQL DB 'test'에서 돈다).

- 처방 업로드·OCR API는 아직 없어서, 시드 스크립트의 create_demo_prescription으로 OCR_DONE 처방을 바로 만든다.
- LLM은 부르지 않는다: generate_guide에 '항상 실패하는 가짜 LLM'을 넣어 fallback 가이드로 만든다. (API 비용 0)
"""

from typing import Any
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from starlette import status
from tortoise.contrib.test import TestCase

from app.main import app
from app.models.guardians import Guardian
from app.models.medications import Medication
from app.models.prescriptions import Prescription, PrescriptionStatus
from app.scripts.seed_prescription import confirm_body_example, create_demo_prescription
from app.services.guide import service as guide_service
from app.tests.auth_apis.helpers import signup_payload

PASSWORD = "pilly1234!"


def offline_generate_guide(child: dict, prescription: dict, medications: list[dict], **_: Any) -> dict:
    def no_llm(system: str, user: str) -> dict:
        raise ValueError("테스트에서는 LLM을 부르지 않아요")

    return guide_service.generate_guide(child, prescription, medications, call_llm=no_llm)


class PrescriptionApiBase(TestCase):
    async def login(self, client: AsyncClient, email: str) -> dict[str, str]:
        signup = signup_payload(email=email, password=PASSWORD)
        joined = await client.post("/api/v1/auth/signup", json=signup)
        res = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
        assert res.status_code == 200, f"가입 {joined.status_code}: {joined.text}\n로그인 {res.status_code}: {res.text}"
        return {"Authorization": f"Bearer {res.json()['access_token']}"}

    async def prepare(self, client: AsyncClient, email: str = "rx@example.com"):
        headers = await self.login(client, email)
        guardian = await Guardian.get(email=email)
        p = await create_demo_prescription(guardian)
        meds = await Medication.filter(prescription_id=p.id).order_by("id")
        return headers, p, meds


class TestConfirmApi(PrescriptionApiBase):
    async def test_confirm_success_and_user_edited_flag(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            body = confirm_body_example(meds)
            body["medications"][1]["dose_per_time"] = 4.0  # 뮤코펙트 양을 보호자가 고침
            res = await client.put(f"/api/v1/prescriptions/{p.id}/confirm", json=body, headers=headers)

        assert res.status_code == status.HTTP_200_OK, res.text
        data = res.json()
        assert data["status"] == "CONFIRMED"
        assert data["diagnosis_user_input"] == "감기, 급성 기관지염"
        assert data["has_guide"] is False
        edited = {m["name"]: m["is_user_edited"] for m in data["medications"]}
        assert edited["뮤코펙트시럽(암브록솔염산염)"] is True
        assert edited["세파클러건조시럽(내복)/60(1)mL/병"] is False  # 4.2 그대로 → 안 고친 것
        assert edited["세토펜현탁액(아세트아미노펜)"] is True  # OCR이 비운 하루 최대 횟수를 채움

    async def test_confirm_add_and_remove_medication(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            body = confirm_body_example(meds)
            removed = body["medications"].pop(2)  # 비오플 삭제
            body["medications"].append(
                {
                    "medication_id": None,
                    "name": "지르텍시럽",
                    "dose_per_time": 2.5,
                    "unit": "mL",
                    "daily_count": 1,
                    "total_days": 5,
                    "as_needed": False,
                    "usage": "1일 1회 자기 전",
                    "route": "ORAL",
                    "dosage_form": "SYRUP",
                }
            )
            res = await client.put(f"/api/v1/prescriptions/{p.id}/confirm", json=body, headers=headers)

        assert res.status_code == status.HTTP_200_OK, res.text
        names = [m["name"] for m in res.json()["medications"]]
        assert "지르텍시럽" in names and removed["name"] not in names
        assert not await Medication.exists(id=removed["medication_id"])

    async def test_confirm_missing_diagnosis_400(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            body = confirm_body_example(meds) | {"diagnosis_user_input": " "}
            res = await client.put(f"/api/v1/prescriptions/{p.id}/confirm", json=body, headers=headers)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.json()["detail"] == "필수 항목을 입력해 주세요: diagnosis_user_input"

    async def test_confirm_as_needed_without_max_is_ok(self):
        """처방전·약봉투에 하루 최대 횟수가 없는 필요시 약도 많아서, 비워도 확정한다."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            body = confirm_body_example(meds)
            body["medications"][3]["max_daily_count"] = None
            res = await client.put(f"/api/v1/prescriptions/{p.id}/confirm", json=body, headers=headers)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json()["medications"][3]["max_daily_count"] is None

    async def test_confirm_as_needed_without_total_days_is_ok(self):
        """필요할 때 먹는 약(해열제 등)은 정해진 복용 기간이 없을 수 있다."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            body = confirm_body_example(meds)
            assert body["medications"][3]["as_needed"] is True
            body["medications"][3]["total_days"] = None
            res = await client.put(f"/api/v1/prescriptions/{p.id}/confirm", json=body, headers=headers)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json()["medications"][3]["total_days"] is None

    async def test_confirm_regular_medication_with_blank_amounts_is_ok(self):
        """OCR이 못 읽은 1회 양·단위·하루 횟수·기간은 보호자가 비워 둔 채로 확정할 수 있다 (명세 7번)."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            body = confirm_body_example(meds)
            assert body["medications"][0]["as_needed"] is False
            blank = {"dose_per_time": None, "unit": None, "daily_count": None, "total_days": None}
            body["medications"][0] |= blank
            res = await client.put(f"/api/v1/prescriptions/{p.id}/confirm", json=body, headers=headers)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert {k: res.json()["medications"][0][k] for k in blank} == blank

    async def test_confirm_saves_free_text_usage(self):
        """용법(usage)은 정해진 값 목록이 아니라 문자열이다. 보호자가 직접 적은 글도 그대로 저장한다."""
        free_text = "1일 3회 식후 즉시, 자기 전에는 빼고"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            body = confirm_body_example(meds)
            body["medications"][0]["usage"] = free_text
            res = await client.put(f"/api/v1/prescriptions/{p.id}/confirm", json=body, headers=headers)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json()["medications"][0]["usage"] == free_text

    async def test_confirm_usage_over_100_chars_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            body = confirm_body_example(meds)
            body["medications"][0]["usage"] = "가" * 101
            res = await client.put(f"/api/v1/prescriptions/{p.id}/confirm", json=body, headers=headers)
        assert res.status_code == 422

    async def test_confirm_medication_without_route_400(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            body = confirm_body_example(meds)
            body["medications"][0]["route"] = None
            res = await client.put(f"/api/v1/prescriptions/{p.id}/confirm", json=body, headers=headers)
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert res.json()["detail"] == "필수 항목을 입력해 주세요: medications[0].route"

    async def test_confirm_rule_errors_422(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            url = f"/api/v1/prescriptions/{p.id}/confirm"

            empty = confirm_body_example(meds) | {"medications": []}
            res_empty = await client.put(url, json=empty, headers=headers)

            prn = confirm_body_example(meds)
            prn["medications"][3]["daily_count"] = 3
            res_prn = await client.put(url, json=prn, headers=headers)

            other = confirm_body_example(meds)
            other["medications"][0]["medication_id"] = 999999
            res_other = await client.put(url, json=other, headers=headers)

        assert (res_empty.status_code, res_empty.json()["detail"]) == (422, "약을 1개 이상 입력해 주세요.")
        assert (res_prn.status_code, res_prn.json()["detail"]) == (
            422,
            "필요할 때 먹는 약은 하루 복용 횟수를 비워 주세요.",
        )
        assert (res_other.status_code, res_other.json()["detail"]) == (422, "이 처방에 없는 약이 포함돼 있어요.")

    async def test_confirm_other_guardian_404_and_no_token_401(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            _, p, meds = await self.prepare(client)
            other_headers = await self.login(client, "other@example.com")
            body = confirm_body_example(meds)
            res_other = await client.put(f"/api/v1/prescriptions/{p.id}/confirm", json=body, headers=other_headers)
            res_anon = await client.put(f"/api/v1/prescriptions/{p.id}/confirm", json=body)
        assert res_other.status_code == status.HTTP_404_NOT_FOUND
        assert res_other.json()["detail"] == "처방전을 찾을 수 없어요."
        assert res_anon.status_code == status.HTTP_401_UNAUTHORIZED
        assert res_anon.json()["detail"] == "로그인이 필요해요."


@patch("app.services.prescriptions.generate_guide", offline_generate_guide)
class TestGuideApi(PrescriptionApiBase):
    async def test_guide_before_confirm_409(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, _ = await self.prepare(client)
            res = await client.post(f"/api/v1/prescriptions/{p.id}/guide", headers=headers)
        assert res.status_code == status.HTTP_409_CONFLICT
        assert res.json()["detail"] == "처방을 먼저 확정해 주세요."

    async def test_get_guide_before_create_404(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, _ = await self.prepare(client)
            res = await client.get(f"/api/v1/prescriptions/{p.id}/guide", headers=headers)
        assert res.status_code == status.HTTP_404_NOT_FOUND
        assert res.json()["detail"] == "아직 만든 가이드가 없어요."

    async def test_full_flow_confirm_create_get(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            base = f"/api/v1/prescriptions/{p.id}"
            await client.put(f"{base}/confirm", json=confirm_body_example(meds), headers=headers)

            created = await client.post(f"{base}/guide", headers=headers)
            again = await client.post(f"{base}/guide", headers=headers)
            fetched = await client.get(f"{base}/guide", headers=headers)
            locked = await client.put(f"{base}/confirm", json=confirm_body_example(meds), headers=headers)

        assert created.status_code == status.HTTP_201_CREATED, created.text
        assert again.status_code == status.HTTP_200_OK  # 두 번째는 새로 만들지 않음
        assert again.json()["guide_id"] == created.json()["guide_id"]
        assert fetched.json() == created.json()

        content = created.json()["guide_content"]
        # 프론트(guide.jsx)가 읽는 키
        for key in ("schedule", "asNeeded", "howTo", "life", "danger", "summary", "disclaimer"):
            assert key in content
        assert [s["slot"] for s in content["schedule"]] == ["아침", "점심", "저녁"]
        assert ["세파클러건조시럽", "4.2mL", "5일"] in content["schedule"][0]["items"]
        assert "세토펜현탁액" in content["asNeeded"] and "하루 4번" in content["asNeeded"]
        assert len(content["howTo"]) == 4
        assert content["danger"]

        p_after = await Prescription.get(id=p.id)
        assert p_after.status == PrescriptionStatus.GUIDE_DONE
        assert locked.status_code == status.HTTP_409_CONFLICT
        assert locked.json()["detail"] == "가이드를 만든 처방은 수정할 수 없어요."

    async def test_guide_with_as_needed_medication_without_total_days(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            base = f"/api/v1/prescriptions/{p.id}"
            body = confirm_body_example(meds)
            body["medications"][3]["total_days"] = None  # 세토펜(필요할 때) 기간·최대 횟수 없음
            body["medications"][3]["max_daily_count"] = None
            await client.put(f"{base}/confirm", json=body, headers=headers)
            created = await client.post(f"{base}/guide", headers=headers)

        assert created.status_code == status.HTTP_201_CREATED, created.text
        content = created.json()["guide_content"]
        assert "세토펜현탁액" in content["asNeeded"]
        assert "번을 넘기지" not in content["asNeeded"]  # 최대 횟수가 없으면 지어내지 않는다
        assert len(content["howTo"]) == 4

    async def test_guide_unexpected_error_502_keeps_confirmed(self):
        def boom(*args: Any, **kwargs: Any) -> dict:
            raise RuntimeError("예상 못 한 오류")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, meds = await self.prepare(client)
            base = f"/api/v1/prescriptions/{p.id}"
            await client.put(f"{base}/confirm", json=confirm_body_example(meds), headers=headers)
            with patch("app.services.prescriptions.generate_guide", boom):
                res = await client.post(f"{base}/guide", headers=headers)

        assert res.status_code == status.HTTP_502_BAD_GATEWAY
        assert res.json()["detail"] == "가이드를 만들지 못했어요. 다시 시도해 주세요."
        assert (await Prescription.get(id=p.id)).status == PrescriptionStatus.CONFIRMED
