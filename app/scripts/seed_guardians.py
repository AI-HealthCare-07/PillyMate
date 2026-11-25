"""개발·시연용 데모 보호자를 만들어요 (DATA-SAMPLE-004, A1 데모 로그인용).

실행 (docker compose로 띄운 상태에서):
    docker exec fastapi uv run python -m app.scripts.seed_guardians

- 이메일은 DEMO_GUARDIAN_EMAIL(기본 demo@pillymate.com)을 써요.
- 이미 있으면 비밀번호·이름·생년월일만 다시 맞춰요(여러 번 실행해도 안전).
- 비밀번호는 SEED_DEMO_PASSWORD 환경변수로 바꿀 수 있어요. 데모 로그인은 비밀번호 없이 들어가요.
- 시연을 운영 서버에서 해야 하면 ENV=prod에서도 실행돼요. 그때는 DEMO_LOGIN_ENABLED로 켜고 꺼요.
- 데모 자녀·처방 예시 데이터는 BE-2가 따로 넣어요.
"""

import asyncio
import os
from datetime import date

from tortoise import Tortoise

from app.core import config
from app.core.db.databases import TORTOISE_ORM
from app.core.utils.security import hash_password
from app.models.guardians import Guardian

DEMO_GUARDIAN = {
    "email": config.DEMO_GUARDIAN_EMAIL.lower(),
    "password": os.getenv("SEED_DEMO_PASSWORD", "pilly1234!"),
    "name": "김보호",
    "birth_date": date(1990, 5, 14),
    "gender": "FEMALE",
    "phone_number": "01012345678",
}


async def seed() -> None:
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        data = dict(DEMO_GUARDIAN)
        password_hash = hash_password(str(data.pop("password")))
        guardian, created = await Guardian.update_or_create(
            email=data.pop("email"),
            defaults={**data, "password_hash": password_hash},
        )
        print(f"{'created' if created else 'updated'}: {guardian.email} (guardian_id={guardian.id})")
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(seed())
