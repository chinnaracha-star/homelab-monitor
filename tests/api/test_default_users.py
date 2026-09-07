from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from homelab_monitor.auth.bootstrap import DEFAULT_USERS, ensure_default_users
from homelab_monitor.auth.passwords import hash_password, verify_password
from homelab_monitor.database import Base
from homelab_monitor.models import User


def test_default_users_exist_and_passwords_work(
    client: TestClient,
    auth_header: Callable[..., dict[str, str]],
) -> None:
    response = client.get("/api/v1/users", headers=auth_header("admin", "admin123"))
    assert response.status_code == 200
    users = {user["username"]: user for user in response.json()}
    assert users["admin"]["role"] == "admin"
    assert users["admin"]["is_active"] is True
    assert users["operator"]["role"] == "operator"
    assert users["operator"]["is_active"] is True
    assert users["viewer"]["role"] == "viewer"
    assert users["viewer"]["is_active"] is True


def test_login_succeeds_for_default_admin_operator_and_viewer(client: TestClient) -> None:
    for user in DEFAULT_USERS:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": user.password},
        )
        assert response.status_code == 200, user.username
        body = response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]

        me = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        assert me.status_code == 200
        assert me.json()["username"] == user.username
        assert me.json()["role"] == user.role


def test_ensure_default_users_creates_missing_accounts_without_overwriting(
    tmp_path: Path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'users.db'}")
    Base.metadata.create_all(bind=engine)
    custom_hash = hash_password("keep-existing-admin")

    with Session(engine) as db:
        db.add(
            User(
                username="admin",
                password_hash=custom_hash,
                full_name="Custom Admin",
                role="admin",
                is_active=True,
            )
        )
        db.commit()
        ensure_default_users(db)

    with Session(engine) as db:
        users = {user.username: user for user in db.scalars(select(User)).all()}
        assert set(users) == {"admin", "operator", "viewer"}
        assert users["admin"].full_name == "Custom Admin"
        assert users["admin"].password_hash == custom_hash
        assert verify_password("keep-existing-admin", users["admin"].password_hash)
        assert users["operator"].role == "operator"
        assert users["operator"].is_active is True
        assert verify_password("operator123", users["operator"].password_hash)
        assert users["viewer"].role == "viewer"
        assert users["viewer"].is_active is True
        assert verify_password("viewer123", users["viewer"].password_hash)

        ensure_default_users(db)
        assert {user.username for user in db.scalars(select(User)).all()} == {
            "admin",
            "operator",
            "viewer",
        }
