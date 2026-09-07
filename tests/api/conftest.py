import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DATABASE_PATH = Path("/tmp/homelab-monitor-tests.db")
os.environ["HOMELAB_REGISTRATION_KEY"] = "test-registration-key-at-least-24-chars"
os.environ["HOMELAB_DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH}"
os.environ["HOMELAB_LOG_LEVEL"] = "WARNING"

from homelab_monitor.database import Base, get_engine  # noqa: E402
from homelab_monitor.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def database_schema() -> None:
    TEST_DATABASE_PATH.unlink(missing_ok=True)
    Base.metadata.create_all(bind=get_engine())
    yield
    Base.metadata.drop_all(bind=get_engine())
    TEST_DATABASE_PATH.unlink(missing_ok=True)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
