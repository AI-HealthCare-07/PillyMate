"""챗봇 API 테스트 (테스트용 MySQL DB). LLM은 가짜 함수로 바꿔 비용 없이 돈다."""

from typing import Any
from unittest.mock import patch

from httpx import ASGITransport, AsyncClient
from starlette import status

from app.main import app
from app.scripts.seed_prescription import confirm_body_example
from app.services.chat.bot import EMERGENCY_REPLY, SAFETY_NOTES
from app.services.guide.llm_client import LLMCallError
from app.tests.prescription_apis.test_prescription_guide_apis import PrescriptionApiBase, offline_generate_guide


def fake_llm(system: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    question = messages[0]["content"].rsplit("보호자 질문: ", 1)[1]
    if "늘려" in question:
        return {"answer": "처방은 1회 5mL예요.", "category": "dose_change"}
    return {"answer": "세토펜은 열이 날 때만 먹여요.", "category": "medication_use"}


def failing_llm(system: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    raise LLMCallError("LLM 호출 실패: APITimeoutError")


@patch("app.services.prescriptions.generate_guide", offline_generate_guide)
@patch("app.services.chat.bot.default_call_llm", fake_llm)
class TestChatApi(PrescriptionApiBase):
    async def make_guide(self, client: AsyncClient) -> tuple[dict[str, str], str]:
        headers, p, meds = await self.prepare(client)
        base = f"/api/v1/prescriptions/{p.id}"
        await client.put(f"{base}/confirm", json=confirm_body_example(meds), headers=headers)
        await client.post(f"{base}/guide", headers=headers)
        return headers, base

    async def test_chat_answer(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, base = await self.make_guide(client)
            body = {
                "message": "해열제는 언제 먹여요?",
                "history": [{"role": "assistant", "text": "궁금한 걸 물어보세요."}],
            }
            res = await client.post(f"{base}/chat", json=body, headers=headers)
        assert res.status_code == status.HTTP_200_OK, res.text
        assert res.json() == {
            "reply": "세토펜은 열이 날 때만 먹여요.",
            "category": "medication_use",
            "needs_professional": False,
        }

    async def test_chat_safety(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, base = await self.make_guide(client)
            dose = await client.post(f"{base}/chat", json={"message": "두 배로 늘려도 돼요?"}, headers=headers)
            er = await client.post(f"{base}/chat", json={"message": "아이가 경련을 해요"}, headers=headers)
        assert dose.json()["reply"].endswith(SAFETY_NOTES["dose_change"])
        assert dose.json()["needs_professional"] is True
        assert er.json()["reply"] == EMERGENCY_REPLY

    async def test_chat_before_guide_409(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, p, _ = await self.prepare(client)
            res = await client.post(
                f"/api/v1/prescriptions/{p.id}/chat", json={"message": "보관은요?"}, headers=headers
            )
        assert res.status_code == status.HTTP_409_CONFLICT
        assert res.json()["detail"] == "가이드를 먼저 만들어 주세요."

    async def test_chat_errors(self):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            headers, base = await self.make_guide(client)
            other = await self.login(client, "chat-other@example.com")
            res_other = await client.post(f"{base}/chat", json={"message": "보관은요?"}, headers=other)
            res_anon = await client.post(f"{base}/chat", json={"message": "보관은요?"})
            with patch("app.services.chat.bot.default_call_llm", failing_llm):
                res_fail = await client.post(f"{base}/chat", json={"message": "보관은요?"}, headers=headers)
        assert res_other.status_code == status.HTTP_404_NOT_FOUND
        assert res_anon.status_code == status.HTTP_401_UNAUTHORIZED
        assert res_fail.status_code == status.HTTP_502_BAD_GATEWAY
        assert res_fail.json()["detail"] == "답변을 만들지 못했어요. 잠시 후 다시 물어봐 주세요."
