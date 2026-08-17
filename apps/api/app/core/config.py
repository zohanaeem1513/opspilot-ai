from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "opspilot-api"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    database_url: str | None = None

    # Supabase Auth JWT verification — exactly one of these is expected to be
    # set, depending on the Supabase project's configured signing algorithm
    # (Settings -> API -> JWT Settings). supabase_jwt_secret is used for the
    # legacy shared-secret (HS256) setup; supabase_url is used to fetch the
    # project's public JWKS for asymmetric (RS256/ES256) verification.
    supabase_jwt_secret: str | None = None
    supabase_url: str | None = None

    # Expected "iss" claim on Supabase-issued access tokens, e.g.
    # https://<project-ref>.supabase.co/auth/v1 for a real project. Read from
    # the environment, never hard-coded — required for token verification to
    # proceed at all (see app/core/security.py).
    supabase_jwt_issuer: str | None = None

    # Supabase Storage — introduced in Phase 4. Document files live in a
    # private Storage bucket; the backend calls Supabase's Storage REST API
    # directly via httpx (no Storage SDK). A private bucket has no RLS
    # policies configured (this project doesn't use Storage RLS, matching
    # the FastAPI-layer-only authorization already used for the database —
    # see docs/DATABASE.md), so writes require Supabase's service_role key,
    # not the anon key. This is the same powerful key Phase 3B deliberately
    # avoided for direct database access; here its use is narrowly scoped to
    # app/core/storage.py only, never used for Postgres access, and never
    # sent to apps/web. supabase_url (above) doubles as the Storage API's
    # host, so no separate storage URL setting is needed.
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = "documents"


settings = Settings()
