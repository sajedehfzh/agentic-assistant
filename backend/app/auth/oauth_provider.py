"""OAuth provider — placeholder.

This is a scaffold for plugging Google / GitHub / generic OIDC providers in
later. To activate it:

1. Set `AUTH_PROVIDER=oauth` in `.env`.
2. Provide the relevant client id/secret env vars (see `app/config.py`).
3. Replace the body of `authenticate()` with real token exchange / userinfo
   calls (e.g. using `httpx` against the provider's `/userinfo` endpoint).
4. Add an `/api/auth/oauth/callback` route to handle the redirect.
5. Wire the corresponding button on the frontend `LoginPage`.
"""

from __future__ import annotations

from app.auth.provider import AuthenticatedUser, AuthProvider
from app.config import Settings


class OAuthProvider(AuthProvider):
    name = "oauth"
    supports_password_login = False

    def __init__(self, settings: Settings) -> None:
        self._google_client_id = settings.oauth_google_client_id
        self._google_client_secret = settings.oauth_google_client_secret
        self._github_client_id = settings.oauth_github_client_id
        self._github_client_secret = settings.oauth_github_client_secret

    async def authenticate(
        self, username: str, password: str
    ) -> AuthenticatedUser | None:
        raise NotImplementedError(
            "OAuth login is not yet implemented. Implement token exchange in "
            "OAuthProvider.authenticate or add a dedicated OAuth callback route."
        )
