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
