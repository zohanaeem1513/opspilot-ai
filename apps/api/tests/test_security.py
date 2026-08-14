import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

import app.core.security as security
from app.core.security import AuthNotConfiguredError, TokenVerificationError, verify_access_token

TEST_ISSUER = "https://test-project.supabase.co/auth/v1"


def _make_token(secret: str, **overrides) -> str:
    now = int(time.time())
    payload = {
        "sub": str(uuid.uuid4()),
        "email": "user@example.com",
        "aud": "authenticated",
        "iss": TEST_ISSUER,
        "iat": now,
        "exp": now + 3600,
    }
    payload.update(overrides)
    return jwt.encode(payload, secret, algorithm="HS256")


def test_hs256_valid_token_returns_claims(monkeypatch):
    monkeypatch.setattr(security.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(security.settings, "supabase_url", None)
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", TEST_ISSUER)
    token = _make_token("test-secret")

    claims = verify_access_token(token)

    assert claims["aud"] == "authenticated"
    assert claims["iss"] == TEST_ISSUER


def test_hs256_wrong_secret_raises(monkeypatch):
    monkeypatch.setattr(security.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(security.settings, "supabase_url", None)
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", TEST_ISSUER)
    token = _make_token("wrong-secret")

    with pytest.raises(TokenVerificationError):
        verify_access_token(token)


def test_hs256_expired_token_raises(monkeypatch):
    monkeypatch.setattr(security.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(security.settings, "supabase_url", None)
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", TEST_ISSUER)
    token = _make_token("test-secret", exp=int(time.time()) - 60)

    with pytest.raises(TokenVerificationError):
        verify_access_token(token)


def test_hs256_wrong_audience_raises(monkeypatch):
    monkeypatch.setattr(security.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(security.settings, "supabase_url", None)
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", TEST_ISSUER)
    token = _make_token("test-secret", aud="something-else")

    with pytest.raises(TokenVerificationError):
        verify_access_token(token)


def test_hs256_correct_issuer_succeeds(monkeypatch):
    monkeypatch.setattr(security.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(security.settings, "supabase_url", None)
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", TEST_ISSUER)
    token = _make_token("test-secret", iss=TEST_ISSUER)

    claims = verify_access_token(token)

    assert claims["iss"] == TEST_ISSUER


def test_hs256_wrong_issuer_raises(monkeypatch):
    monkeypatch.setattr(security.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(security.settings, "supabase_url", None)
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", TEST_ISSUER)
    token = _make_token("test-secret", iss="https://attacker-project.supabase.co/auth/v1")

    with pytest.raises(TokenVerificationError):
        verify_access_token(token)


def test_hs256_missing_issuer_claim_raises(monkeypatch):
    """Passing issuer= to jwt.decode() makes the 'iss' claim itself
    required, not just checked when present — a token with no 'iss' claim
    must fail, not be silently accepted."""
    monkeypatch.setattr(security.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(security.settings, "supabase_url", None)
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", TEST_ISSUER)

    now = int(time.time())
    payload = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "iat": now,
        "exp": now + 3600,
        # no "iss" claim at all
    }
    token = jwt.encode(payload, "test-secret", algorithm="HS256")

    with pytest.raises(TokenVerificationError):
        verify_access_token(token)


def test_missing_issuer_config_raises_auth_not_configured(monkeypatch):
    """Issuer validation must never be silently skipped: if
    SUPABASE_JWT_ISSUER isn't configured, verification refuses to proceed
    at all, even though a signing secret is configured."""
    monkeypatch.setattr(security.settings, "supabase_jwt_secret", "test-secret")
    monkeypatch.setattr(security.settings, "supabase_url", None)
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", None)
    token = _make_token("test-secret")

    with pytest.raises(AuthNotConfiguredError):
        verify_access_token(token)


def test_no_config_raises_auth_not_configured(monkeypatch):
    monkeypatch.setattr(security.settings, "supabase_jwt_secret", None)
    monkeypatch.setattr(security.settings, "supabase_url", None)
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", None)
    token = _make_token("irrelevant-secret")

    with pytest.raises(AuthNotConfiguredError):
        verify_access_token(token)


def _make_rs256_token(private_key, **overrides) -> str:
    now = int(time.time())
    payload = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "iss": TEST_ISSUER,
        "iat": now,
        "exp": now + 3600,
    }
    payload.update(overrides)
    return jwt.encode(payload, private_key, algorithm="RS256")


def test_jwks_valid_token_returns_claims(monkeypatch):
    """Exercises the asymmetric (RS256/JWKS) verification path without any
    real network call — the JWKS client lookup is stubbed to return a
    locally generated test key pair's public key."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _make_rs256_token(private_key)

    monkeypatch.setattr(security.settings, "supabase_jwt_secret", None)
    monkeypatch.setattr(security.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", TEST_ISSUER)

    class FakeSigningKey:
        key = private_key.public_key()

    class FakeJWKSClient:
        def get_signing_key_from_jwt(self, token: str) -> FakeSigningKey:
            return FakeSigningKey()

    monkeypatch.setattr(security, "_get_jwks_client", lambda: FakeJWKSClient())

    claims = verify_access_token(token)

    assert claims["aud"] == "authenticated"
    assert claims["iss"] == TEST_ISSUER


def test_jwks_wrong_key_raises(monkeypatch):
    signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _make_rs256_token(signing_key)

    monkeypatch.setattr(security.settings, "supabase_jwt_secret", None)
    monkeypatch.setattr(security.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", TEST_ISSUER)

    class FakeSigningKey:
        key = other_key.public_key()

    class FakeJWKSClient:
        def get_signing_key_from_jwt(self, token: str) -> FakeSigningKey:
            return FakeSigningKey()

    monkeypatch.setattr(security, "_get_jwks_client", lambda: FakeJWKSClient())

    with pytest.raises(TokenVerificationError):
        verify_access_token(token)


def test_jwks_wrong_issuer_raises(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = _make_rs256_token(private_key, iss="https://attacker-project.supabase.co/auth/v1")

    monkeypatch.setattr(security.settings, "supabase_jwt_secret", None)
    monkeypatch.setattr(security.settings, "supabase_url", "https://example.supabase.co")
    monkeypatch.setattr(security.settings, "supabase_jwt_issuer", TEST_ISSUER)

    class FakeSigningKey:
        key = private_key.public_key()

    class FakeJWKSClient:
        def get_signing_key_from_jwt(self, token: str) -> FakeSigningKey:
            return FakeSigningKey()

    monkeypatch.setattr(security, "_get_jwks_client", lambda: FakeJWKSClient())

    with pytest.raises(TokenVerificationError):
        verify_access_token(token)
