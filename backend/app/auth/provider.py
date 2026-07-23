"""Pluggable authentication provider abstraction.

The application talks only to `AuthProvider`. Concrete implementations live in
sibling modules (`simple_provider.py`, `oauth_provider.py`, ...). To plug in a
new provider:

1. Create a new class implementing `AuthProvider`.
2. Add the relevant config to `app/config.py` and `.env`.
3. Register it inside `get_auth_provider` below.
4. (Optional) Surface a corresponding button on the frontend Login page.

No other code should need to change.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Depends

from app.config import Settings, get_settings


@dataclass
class AuthenticatedUser:
    username: str
    provider: str
    is_admin: bool = True
    email: Optional[str] = None
    full_name: Optional[str] = None


class AuthProvider(ABC):
    """Abstract authentication provider."""

    name: str = "base"

    @abstractmethod
    async def authenticate(
        self, username: str, password: str
    ) -> Optional[AuthenticatedUser]:
        """Validate credentials. Return an `AuthenticatedUser` on success, `None` otherwise."""

    @property
    def supports_password_login(self) -> bool:
        """Whether this provider accepts a username + password pair."""
        return True


def get_auth_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthProvider:
    """Factory used everywhere we need an auth provider.

    Switching providers is just a matter of changing the `AUTH_PROVIDER` env
    variable and (for non-simple providers) filling in the relevant secrets.
    """
    from app.auth.simple_provider import SimpleAuthProvider

    if settings.auth_provider == "simple":
        return SimpleAuthProvider(settings)

    if settings.auth_provider == "oauth":
        from app.auth.oauth_provider import OAuthProvider

        return OAuthProvider(settings)

    raise ValueError(f"Unknown AUTH_PROVIDER: {settings.auth_provider!r}")
