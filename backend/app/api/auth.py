"""Authentication routes."""

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.user import ProfileUpdate
from app.services.auth import update_profile
from app.schemas.auth import (
    LoginRequest,
    LogoutResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services.auth import (
    logout,
    get_current_user,
    login,
    refresh,
    signup,
    user_to_response,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


async def get_current_user_id(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Extract user from Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token = authorization[7:]
    user = await get_current_user(db, token)
    return user_to_response(user)


@router.post(
    "/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
async def signup_endpoint(
    data: SignupRequest, db: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    """Register a new user and return access/refresh tokens."""
    return await signup(db, data)


@router.post("/login", response_model=TokenResponse)
async def login_endpoint(
    data: LoginRequest, db: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    """Authenticate user and return access/refresh tokens."""
    return await login(db, data)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_endpoint(
    data: RefreshRequest, db: AsyncSession = Depends(get_db_session)
) -> TokenResponse:
    """Refresh access token using refresh token."""
    return await refresh(db, data)


@router.post("/logout", response_model=LogoutResponse)
async def logout_endpoint(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db_session),
) -> LogoutResponse:
    """Invalidate all active access and refresh tokens for this account."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header",
        )

    token = authorization[7:]
    await logout(db, token)

    return LogoutResponse()


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserResponse = Depends(get_current_user_id),
) -> UserResponse:
    """Get current authenticated user."""
    return current_user


@router.patch('/me', response_model=UserResponse)
async def patch_me(
    data: ProfileUpdate,
    current_user: UserResponse = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    return await update_profile(db, current_user.id, data)
