"""Simple env-var-backed admin/admin provider.

Good enough for solo usage and local development. For production use, swap to
an OAuth/OIDC provider — see `oauth_provider.py`.
"""

from __future__ import annotations

import hmac

from app.auth.provider import AuthenticatedUser, AuthProvider
from app.config import Settings


class SimpleAuthProvider(AuthProvider):
    name = "simple"

    def __init__(self, settings: Settings) -> None:
        self._username = settings.auth_username
        self._password = settings.auth_password

    async def authenticate(
        self, username: str, password: str
    ) -> AuthenticatedUser | None:
        if hmac.compare_digest(username, self._username) and hmac.compare_digest(
            password, self._password
        ):
            return AuthenticatedUser(
                username=username,
                provider=self.name,
                is_admin=True,
            )
        return None
