"""Authentication package.

Provides a pluggable auth provider abstraction. The default implementation is
a simple username/password (admin/admin) stored in env vars. To add OAuth or
SSO, implement `AuthProvider` and register it in `get_auth_provider`.
"""

from app.auth.middleware import get_current_user
from app.auth.provider import AuthenticatedUser, AuthProvider, get_auth_provider

__all__ = ["AuthProvider", "AuthenticatedUser", "get_auth_provider", "get_current_user"]
