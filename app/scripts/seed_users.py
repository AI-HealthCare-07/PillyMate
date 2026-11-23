"""개발용 시드 계정을 만들어요.

실행 (docker compose로 띄운 상태에서):
    docker exec fastapi uv run python -m app.scripts.seed_users

- 이미 같은 이메일 계정이 있으면 비밀번호와 관리자 권한만 다시 맞춰요(여러 번 실행해도 안전).
- ENV=prod 에서는 실행되지 않아요.
- 비밀번호는 SEED_MASTER_PASSWORD 환경변수로 바꿀 수 있어요.
"""

import asyncio
import os
from datetime import date

from tortoise import Tortoise

from app.core import config
from app.core.config import Env
from app.core.db.databases import TORTOISE_ORM
from app.core.utils.security import hash_password
from app.models.users import Gender, User
from app.repositories.user_repository import UserRepository

SEED_USERS = [
    {
        "email": "master@pillymate.com",
        "password": os.getenv("SEED_MASTER_PASSWORD", "Master1234!"),
        "name": "마스터",
        "phone_number": "01000000000",
        "gender": Gender.FEMALE,
        "birthday": date(1990, 1, 1),
        "is_admin": True,
    },
]


async def seed() -> None:
    if config.ENV == Env.PROD:
        raise SystemExit("ENV=prod 에서는 시드 계정을 만들지 않아요.")

    await Tortoise.init(config=TORTOISE_ORM)
    try:
        repo = UserRepository()
        for spec in SEED_USERS:
            data = dict(spec)
            password = data.pop("password")
            is_admin = data.pop("is_admin")
            user = await repo.get_user_by_email(data["email"])
            if user:
                user.hashed_password = hash_password(password)
                user.is_admin = is_admin
                user.is_active = True
                await user.save(update_fields=["hashed_password", "is_admin", "is_active"])
                print(f"updated: {user.email} (id={user.id}, admin={user.is_admin})")
            else:
                user = await repo.create_user(hashed_password=hash_password(password), is_admin=is_admin, **data)
                print(f"created: {user.email} (id={user.id}, admin={user.is_admin})")
        print(f"total users: {await User.all().count()}")
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(seed())
