"""Password hashing and JWT credentials. Secrets come from the environment."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlalchemy import select
from sqlalchemy.orm import Session

from utility_asset_registry.config import get_settings
from utility_asset_registry.models import User

ALGORITHM = "HS256"
ROLES = frozenset({"admin", "surveyor"})

_hasher = BcryptHasher()


class AuthError(Exception):
    def __init__(self, status_code: int, content: dict) -> None:
        self.status_code = status_code
        self.content = content


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _hasher.verify(password, password_hash)


def create_token(username: str, role: str) -> tuple[str, int]:
    settings = get_settings()
    expires_in = settings.jwt_expire_minutes * 60
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)
    return token, expires_in


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise AuthError(
            401,
            {"outcome": "unauthenticated", "message": "The sign-in credential is missing, expired or invalid"},
        ) from exc


def get_user_by_username(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == username))


def authenticate(session: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(session, username)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def bootstrap_admin(session: Session) -> None:
    """Create the first administrator from the environment if none exists yet."""
    settings = get_settings()
    username = settings.bootstrap_admin_username.strip()
    password = settings.bootstrap_admin_password
    if not username or not password:
        return
    if get_user_by_username(session, username) is not None:
        return
    session.add(
        User(username=username, password_hash=hash_password(password), role="admin")
    )
    session.commit()
