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

    JWT_ALGORITHM: str = "HS256"
    # 명세서 1절: 토큰 유효시간 12시간, 리프레시 토큰 없음
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 12 * 60
    JWT_LEEWAY: int = 5

    # CORS: 허용할 프론트 주소를 쉼표로 구분 (예: "http://localhost:5173,https://pillymate.example.com")
    # 기본값은 로컬 FE 개발 서버. 빈 값("")이면 CORS 미들웨어를 붙이지 않음 (FE·BE가 같은 도메인인 경우)
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

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

    # 식약처 공공데이터 API (공공데이터포털 일반 인증키 하나로 함께 씀. API마다 활용신청은 따로)
    MFDS_API_KEY: str = ""  # 비밀값: .env 에만 넣는다 (Decoding 키)
    # 허가정보: 보험코드·이름 → 주성분
    MFDS_PERMIT_URL: str = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService08"
    # DUR: 연령금기·효능군중복·병용금기 (2차)
    MFDS_DUR_URL: str = "https://apis.data.go.kr/1471000/DURPrdlstInfoService03"

    # 데모 로그인(A1): 배포 환경에서 false로 끄면 404. 데모 보호자는 app/scripts/seed_guardians.py로 만든다.
    DEMO_LOGIN_ENABLED: bool = False
    DEMO_GUARDIAN_EMAIL: str = "demo@pillymate.com"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
