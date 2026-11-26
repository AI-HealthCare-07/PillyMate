from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, EmailStr, Field

from app.core.validators import normalize_phone_number


def _lower(value: str) -> str:
    return value.strip().lower()


def _phone(value: str) -> str:
    normalized = normalize_phone_number(value)
    if normalized is None:
        raise ValueError("휴대전화 번호 형식이 맞지 않아요.")
    return normalized


class SignUpRequest(BaseModel):
    email: Annotated[EmailStr, AfterValidator(_lower)]
    # 길이(8~64자)는 명세 문구로 응답하기 위해 서비스에서 확인한다.
    password: str
    name: Annotated[str, Field(min_length=1, max_length=50)]
    birth_date: date
    gender: Literal["MALE", "FEMALE"]
    phone_number: Annotated[str, AfterValidator(_phone)]


class SignUpResponse(BaseModel):
    guardian_id: int
    email: str
    name: str
    birth_date: date
    gender: str | None = None
    phone_number: str | None = None


class LoginRequest(BaseModel):
    # 로그인에서는 형식이 틀린 이메일도 422가 아니라 401로 응답한다 (어느 쪽이 틀렸는지 알려 주지 않음).
    email: Annotated[str, AfterValidator(_lower)]
    password: str


class GuardianSummary(BaseModel):
    guardian_id: int
    name: str
    child_count: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    guardian: GuardianSummary
