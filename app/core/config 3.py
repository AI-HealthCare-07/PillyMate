import os
import uuid
import zoneinfo
from dataclasses import field
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(StrEnum):
    LOCAL = "local"
    DEV = "dev"
    PROD = "prod"


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

    ENV: Env = Env.LOCAL
    SECRET_KEY: str = f"default-secret-key{uuid.uuid4().hex}"
    TIMEZONE: zoneinfo.ZoneInfo = field(default_factory=lambda: zoneinfo.ZoneInfo("Asia/Seoul"))
    TEMPLATE_DIR: str = os.path.join(Path(__file__).resolve().parent.parent, "templates")

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "pw1234"
    DB_NAME: str = "ai_health"
    DB_CONNECT_TIMEOUT: int = 5
    DB_CONNECTION_POOL_MAXSIZE: int = 10

    COOKIE_DOMAIN: str = "localhost"

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 14 * 24 * 60
    JWT_LEEWAY: int = 5

    # CORS: 허용할 프론트 주소를 쉼표로 구분 (예: "http://localhost:5173,https://pillymate.example.com")
    # 비워 두면 CORS 미들웨어를 붙이지 않음 (FE·BE가 같은 도메인이고 nginx가 /api/로 나누는 경우)
    CORS_ORIGINS: str = ""

    # 이미지 저장소: "local"이면 S3 없이 로컬 폴더에 저장 (개발용), "s3"면 AWS S3 사용
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    LOCAL_STORAGE_DIR: str = os.path.join(Path(__file__).resolve().parent.parent.parent, ".local_storage")
    AWS_REGION: str = "ap-northeast-2"
    S3_BUCKET: str = ""
    S3_PRESIGNED_URL_EXPIRE_SECONDS: int = 600  # 명세 6번: presigned URL 10분 유효

    # 외부 API 키: 코드에 넣지 않고 환경변수 또는 Secrets Manager로만 주입
    CLOVA_OCR_URL: str = ""
    CLOVA_OCR_SECRET: str = ""
    ANTHROPIC_API_KEY: str = ""

    # 데모 로그인(A1): 배포 환경에서 false로 끄면 404
    DEMO_LOGIN_ENABLED: bool = False

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
