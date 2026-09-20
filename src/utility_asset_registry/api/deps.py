"""FastAPI session and authentication dependencies."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from utility_asset_registry.auth import AuthError, decode_token, get_user_by_username
from utility_asset_registry.models import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_db(request: Request) -> Generator[Session, None, None]:
    factory = request.app.state.session_factory
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthError(
            401,
            {"outcome": "unauthenticated", "message": "Sign in is required"},
        )
    payload = decode_token(credentials.credentials)
    username = payload.get("sub")
    if not username:
        raise AuthError(
            401,
            {"outcome": "unauthenticated", "message": "The sign-in credential is missing, expired or invalid"},
        )
    user = get_user_by_username(session, username)
    if user is None:
        raise AuthError(
            401,
            {"outcome": "unauthenticated", "message": "The sign-in credential is missing, expired or invalid"},
        )
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AuthError(
            403,
            {
                "outcome": "not_permitted",
                "message": "Only an administrator may do that",
            },
        )
    return user
