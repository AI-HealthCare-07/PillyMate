"""챗봇 답변 로직(bot.py) 테스트는 DB를 쓰지 않는다. 가이드 테스트와 같은 방법으로 DB 접속을 건너뛴다."""

from collections.abc import Generator

import pytest


@pytest.fixture(scope="session", autouse=True)
def initialize() -> Generator[None, None]:
    yield
