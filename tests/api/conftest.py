import os
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

TEST_DATABASE_PATH = Path("/tmp/homelab-monitor-tests.db")
os.environ["HOMELAB_REGISTRATION_KEY"] = "test-registration-key-at-least-24-chars"
os.environ["HOMELAB_DATABASE_URL"] = f"sqlite:///{TEST_DATABASE_PATH}"
os.environ["HOMELAB_LOG_LEVEL"] = "WARNING"
os.environ["HOMELAB_JWT_SECRET"] = "test-jwt-secret-key-at-least-32-chars"

from homelab_monitor.auth.passwords import hash_password  # noqa: E402
from homelab_monitor.database import Base, get_engine  # noqa: E402
from homelab_monitor.main import app  # noqa: E402
from homelab_monitor.models import User  # noqa: E402


def seed_users() -> None:
    with Session(get_engine()) as db:
        db.add_all(
            [
                User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    full_name="Administrator",
                    role="admin",
                    is_active=True,
                ),
                User(
                    username="operator",
                    password_hash=hash_password("operator123"),
                    full_name="Operator",
                    role="operator",
                    is_active=True,
                ),
                User(
                    username="viewer",
                    password_hash=hash_password("viewer123"),
                    full_name="Viewer",
                    role="viewer",
                    is_active=True,
                ),
                User(
                    username="disabled",
                    password_hash=hash_password("disabled123"),
                    full_name="Disabled User",
                    role="viewer",
                    is_active=False,
                ),
            ]
        )
        db.commit()


@pytest.fixture(scope="session", autouse=True)
def database_schema() -> Iterator[None]:
    TEST_DATABASE_PATH.unlink(missing_ok=True)
    Base.metadata.create_all(bind=get_engine())
    seed_users()
    yield
    Base.metadata.drop_all(bind=get_engine())
    TEST_DATABASE_PATH.unlink(missing_ok=True)


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def login(client: TestClient) -> Callable[..., str]:
    def _login(username: str = "admin", password: str = "admin123") -> str:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200
        return response.json()["access_token"]

    return _login


@pytest.fixture
def auth_header(login: Callable[..., str]) -> Callable[..., dict[str, str]]:
    def _auth_header(
        username: str = "admin",
        password: str = "admin123",
    ) -> dict[str, str]:
        return {"Authorization": f"Bearer {login(username, password)}"}

    return _auth_header
