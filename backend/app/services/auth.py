"""Argon2 authentication and database-backed JWT revocation."""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

import anyio
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.exceptions import ConflictError, UnauthorizedError, ValidationError
from app.models.entities import User, UserRole
from app.schemas.user import ProfileUpdate
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)

# Password hashes use Argon2.
pwd_context = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
)
settings = get_settings()
PASSWORD_LIMITER = anyio.CapacityLimiter(2)


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.

    Validates password requirements:
    - Minimum 8 characters
    - Maximum 72 characters (current API contract)
    """
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if len(password) > 72:
        raise ValidationError("Password too long (max 72 characters)")
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: UUID, role: UserRole, *, auth_version: int) -> str:
    """Create a JWT access token."""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    to_encode = {
        "sub": str(user_id),
        "role": role.value,
        "ver": auth_version,
        "jti": uuid4().hex,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def create_refresh_token(user_id: UUID, *, auth_version: int) -> str:
    """Create a JWT refresh token."""
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    to_encode = {
        "sub": str(user_id),
        "type": "refresh",
        "ver": auth_version,
        "jti": uuid4().hex,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm],
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
        UUID(payload["sub"])
        if type(payload.get("ver")) is not int or payload["ver"] < 0:
            raise ValueError("Missing or invalid token version")
        return payload
    except (JWTError, ValueError, TypeError, KeyError) as e:
        raise UnauthorizedError("Invalid or expired token") from e


def create_token_response(user: User) -> TokenResponse:
    """Create a token response for a user."""
    access_token = create_access_token(user.id, user.role, auth_version=user.auth_version)
    refresh_token = create_refresh_token(user.id, auth_version=user.auth_version)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def signup(db: AsyncSession, data: SignupRequest) -> TokenResponse:
    """Register a new user."""
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise ConflictError("Email already registered")

    password_hash = await anyio.to_thread.run_sync(
        hash_password, data.password, limiter=PASSWORD_LIMITER
    )
    user = User(
        email=data.email,
        display_name=data.display_name,
        password_hash=password_hash,
        role=UserRole.user,
    )
    db.add(user)
    await db.flush()
    return create_token_response(user)


async def login(db: AsyncSession, data: LoginRequest) -> TokenResponse:
    """Authenticate a user and return tokens."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not user.password_hash:
        raise UnauthorizedError("Invalid credentials")

    password_valid = await anyio.to_thread.run_sync(
        verify_password, data.password, user.password_hash, limiter=PASSWORD_LIMITER
    )
    if not password_valid:
        raise UnauthorizedError("Invalid credentials")

    if not user.is_active:
        raise UnauthorizedError("Account is deactivated")

    return create_token_response(user)


async def refresh(db: AsyncSession, data: RefreshRequest) -> TokenResponse:
    """Consume the current refresh version exactly once across all workers."""
    payload = decode_token(data.refresh_token)

    if payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid token type")

    user = await _rotate_version(db, payload)
    return create_token_response(user)


async def _rotate_version(db: AsyncSession, payload: dict[str, Any]) -> User:
    result = await db.execute(
        update(User).where(
            User.id == UUID(payload["sub"]), User.is_active.is_(True),
            User.auth_version == payload["ver"],
        ).values(auth_version=User.auth_version + 1).returning(User)
        .execution_options(synchronize_session=False, populate_existing=True)
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError("Invalid, revoked, or inactive session")
    # Commit revocation before returning new credentials or logout success.
    await db.commit()
    return user


async def logout(db: AsyncSession, token: str) -> None:
    """Revoke all of the user's tokens using a currently valid access token."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")
    await _rotate_version(db, payload)


async def get_current_user(db: AsyncSession, token: str) -> User:
    """Get current user from access token."""
    payload = decode_token(token)

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    user_id = UUID(payload["sub"])
    result = await db.execute(
        select(User).where(User.id == user_id).execution_options(populate_existing=True)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active or payload.get("ver") != user.auth_version:
        raise UnauthorizedError("User not found or inactive")

    return user


def user_to_response(user: User) -> UserResponse:
    """Convert User entity to UserResponse schema."""
    return UserResponse.model_validate(user)


async def update_profile(db: AsyncSession, user_id: UUID, data: ProfileUpdate) -> UserResponse:
    """Update only explicitly supplied profile fields for the authenticated owner."""
    values = data.model_dump(exclude_unset=True)
    if values:
        await db.execute(update(User).where(User.id == user_id, User.is_active.is_(True)).values(**values))
        await db.commit()
    user = await db.get(User, user_id, populate_existing=True)
    if user is None or not user.is_active:
        raise UnauthorizedError('Account unavailable')
    return user_to_response(user)
