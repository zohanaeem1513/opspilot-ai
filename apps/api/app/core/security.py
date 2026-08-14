from __future__ import annotations

from typing import Any

import jwt
from jwt import PyJWKClient

from app.core.config import settings

SUPABASE_AUDIENCE = "authenticated"


class TokenVerificationError(Exception):
    """Raised when a bearer token fails verification, for any reason.

    Never carries the underlying cause (bad signature, expired, wrong
    audience, ...) so callers can surface a generic 401 without leaking
    verification internals to the client.
    """


class AuthNotConfiguredError(TokenVerificationError):
    """Raised when neither SUPABASE_JWT_SECRET nor SUPABASE_URL is set."""


_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        assert settings.supabase_url is not None
        jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url)
    return _jwks_client


def verify_access_token(token: str) -> dict[str, Any]:
    """Verify a Supabase Auth access token and return its claims.

    Picks the verification path that matches the Supabase project's actual
    signing configuration: a shared secret (HS256) if SUPABASE_JWT_SECRET is
    set, or the project's public JWKS (RS256/ES256) if SUPABASE_URL is set
    instead. Exactly one is expected to be configured, matching whichever
    algorithm the project uses.

    The "iss" claim is always validated against SUPABASE_JWT_ISSUER — this is
    required configuration, not optional. If it isn't set, verification
    refuses to proceed rather than silently skipping issuer validation.
    Passing `issuer=` to jwt.decode() also makes the "iss" claim itself
    required on the token: a token with no "iss" claim at all fails
    verification too.
    """
    if not settings.supabase_jwt_issuer:
        raise AuthNotConfiguredError("SUPABASE_JWT_ISSUER is not configured")

    try:
        if settings.supabase_jwt_secret:
            return jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience=SUPABASE_AUDIENCE,
                issuer=settings.supabase_jwt_issuer,
            )
        if settings.supabase_url:
            signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
            return jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=SUPABASE_AUDIENCE,
                issuer=settings.supabase_jwt_issuer,
            )
    except jwt.PyJWTError as exc:
        raise TokenVerificationError("token verification failed") from exc

    raise AuthNotConfiguredError("Neither SUPABASE_JWT_SECRET nor SUPABASE_URL is configured")
