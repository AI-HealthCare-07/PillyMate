import re
from datetime import date, datetime

from dateutil.relativedelta import relativedelta

from app.core import config

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 64
GUARDIAN_MIN_AGE = 19  # NFR-SEC-005: 보호자는 만 19세 이상


def is_valid_password_length(password: str) -> bool:
    return PASSWORD_MIN_LENGTH <= len(password) <= PASSWORD_MAX_LENGTH


def international_age(birth_date: date, today: date | None = None) -> int:
    """만 나이."""
    today = today or datetime.now(tz=config.TIMEZONE).date()
    return relativedelta(today, birth_date).years


def is_adult_guardian(birth_date: date, today: date | None = None) -> bool:
    return international_age(birth_date, today) >= GUARDIAN_MIN_AGE


# 프론트 가입 화면과 같은 형식: 010-1234-5678 / 01012345678 / +821012345678
_PHONE_PATTERN = re.compile(r"^(010-\d{4}-\d{4}|010\d{8}|\+8210\d{8})$")


def normalize_phone_number(value: str) -> str | None:
    """휴대전화 번호를 숫자만 있는 국내 형식(01012345678)으로 맞춘다. 형식이 틀리면 None."""
    value = value.strip()
    if not _PHONE_PATTERN.match(value):
        return None
    digits = re.sub(r"\D", "", value)
    if digits.startswith("82"):
        digits = "0" + digits[2:]
    return digits
