"""Sign-in and administrator user creation."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from utility_asset_registry.api.deps import get_db, require_admin
from utility_asset_registry.api.errors import created, invalid_payload, unauthenticated
from utility_asset_registry.auth import ROLES, authenticate, create_token, get_user_by_username, hash_password
from utility_asset_registry.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    role: str


@router.post("/login")
def login(payload: LoginIn, session: Session = Depends(get_db)):
    user = authenticate(session, payload.username, payload.password)
    if user is None:
        return unauthenticated("Username or password is wrong")
    token, expires_in = create_token(user.username, user.role)
    return {
        "token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "role": user.role,
        "username": user.username,
    }


@router.post("/users", status_code=201)
def create_user(payload: UserIn, session: Session = Depends(get_db), _: User = Depends(require_admin)):
    role = payload.role.strip().lower()
    if role not in ROLES:
        return invalid_payload({"role": "role must be surveyor or admin"})
    if get_user_by_username(session, payload.username) is not None:
        return invalid_payload(
            {"username": f"username '{payload.username}' is already in use"},
            message="A user with this name already exists; stored data was not changed",
        )
    user = User(
        username=payload.username.strip(),
        password_hash=hash_password(payload.password),
        role=role,
    )
    session.add(user)
    session.flush()
    return created({"user": {"username": user.username, "role": user.role}})
