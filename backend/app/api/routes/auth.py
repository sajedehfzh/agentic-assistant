"""Auth routes — login + current user lookup."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.jwt_handler import create_access_token
from app.auth.middleware import get_current_user
from app.auth.provider import AuthenticatedUser, AuthProvider, get_auth_provider
from app.config import Settings, get_settings

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    provider: str
    username: str


class UserResponse(BaseModel):
    username: str
    provider: str
    is_admin: bool
    email: str | None = None
    full_name: str | None = None


class AuthProvidersResponse(BaseModel):
    active: str
    providers: list[dict[str, object]]


@router.get("/providers", response_model=AuthProvidersResponse)
async def list_providers(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthProvidersResponse:
    """Tell the frontend which auth methods are available.

    The frontend uses this to decide whether to show the password form, the
    OAuth buttons, etc. Adding a new provider in the backend automatically
    surfaces it here.
    """
    return AuthProvidersResponse(
        active=settings.auth_provider,
        providers=[
            {
                "name": "simple",
                "label": "Username & password",
                "supports_password_login": True,
                "enabled": settings.auth_provider == "simple",
            },
            {
                "name": "google",
                "label": "Sign in with Google",
                "supports_password_login": False,
                "enabled": bool(settings.oauth_google_client_id),
            },
            {
                "name": "github",
                "label": "Sign in with GitHub",
                "supports_password_login": False,
                "enabled": bool(settings.oauth_github_client_id),
            },
        ],
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[AuthProvider, Depends(get_auth_provider)],
) -> TokenResponse:
    user = await provider.authenticate(payload.username, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token(
        subject=user.username,
        settings=settings,
        extra_claims={
            "provider": user.provider,
            "is_admin": user.is_admin,
            "email": user.email,
            "full_name": user.full_name,
        },
    )
    return TokenResponse(
        access_token=token,
        expires_in_minutes=settings.jwt_access_token_expire_minutes,
        provider=user.provider,
        username=user.username,
    )


@router.get("/me", response_model=UserResponse)
async def me(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UserResponse:
    return UserResponse(
        username=user.username,
        provider=user.provider,
        is_admin=user.is_admin,
        email=user.email,
        full_name=user.full_name,
    )
