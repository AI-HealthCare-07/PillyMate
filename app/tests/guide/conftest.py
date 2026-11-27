"""가이드 모듈 테스트는 DB를 쓰지 않는다.

app/tests/conftest.py의 initialize(자동 실행)는 MySQL에 접속하므로, DB를 안 띄운 컴퓨터에서는
가이드 테스트까지 모두 setup 에러가 난다. 이 폴더에서만 같은 이름의 fixture로 덮어써서 DB 접속을 건너뛴다.
다른 폴더(auth_apis, user_apis)의 테스트에는 영향이 없다.
"""

from collections.abc import Generator

import pytest


@pytest.fixture(scope="session", autouse=True)
def initialize() -> Generator[None, None]:
    yield


@pytest.fixture(autouse=True)
def no_real_mfds_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    """config가 .env를 읽어 MFDS_API_KEY가 있어도, 테스트에서는 식약처 API를 부르지 않는다."""
    from app.services.guide import unreviewed_drug_reference

    monkeypatch.setattr(unreviewed_drug_reference, "lookup_enabled", lambda: False)
