from dataclasses import dataclass

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from homelab_monitor.auth.passwords import hash_password
from homelab_monitor.models import User


@dataclass(frozen=True)
class DefaultUser:
    username: str
    password: str
    full_name: str
    role: str


DEFAULT_USERS = (
    DefaultUser("admin", "admin123", "Administrator", "admin"),
    DefaultUser("operator", "operator123", "Operator", "operator"),
    DefaultUser("viewer", "viewer123", "Viewer", "viewer"),
)


def ensure_default_users(db: Session) -> None:
    bind = db.get_bind()
    if bind is None or "users" not in inspect(bind).get_table_names():
        return

    existing = set(db.scalars(select(User.username)).all())
    created = False
    for user in DEFAULT_USERS:
        if user.username in existing:
            continue
        db.add(
            User(
                username=user.username,
                password_hash=hash_password(user.password),
                full_name=user.full_name,
                role=user.role,
                is_active=True,
            )
        )
        created = True
    if created:
        db.commit()
