from datetime import date

from app.models.guardians import Guardian


class GuardianRepository:
    def __init__(self) -> None:
        self._model = Guardian

    async def get_guardian(self, guardian_id: int) -> Guardian | None:
        return await self._model.get_or_none(id=guardian_id)

    async def get_by_email(self, email: str) -> Guardian | None:
        return await self._model.get_or_none(email=email)

    async def exists_by_email(self, email: str) -> bool:
        return await self._model.filter(email=email).exists()

    async def create_guardian(
        self,
        email: str,
        password_hash: str,
        name: str,
        birth_date: date,
        gender: str | None = None,
        phone_number: str | None = None,
    ) -> Guardian:
        return await self._model.create(
            email=email,
            password_hash=password_hash,
            name=name,
            birth_date=birth_date,
            gender=gender,
            phone_number=phone_number,
        )

    async def count_children(self, guardian_id: int) -> int:
        """로그인 응답의 child_count. 자녀 모델(BE-2)이 머지되기 전에는 0을 돌려준다."""
        try:
            from app.models.children import Child  # type: ignore[import-not-found]
        except ImportError:
            return 0
        count: int = await Child.filter(guardian_id=guardian_id).count()
        return count
