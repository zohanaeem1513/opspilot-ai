# OpsPilot AI — Database

## Platform

[Supabase](https://supabase.com) hosts the project's single PostgreSQL database (free plan). The backend talks to it directly through SQLAlchemy's async engine (`asyncpg` driver) — it does **not** use the Supabase Python client. A real Supabase project is connected (`apps/api/.env`, `apps/web/.env.local`, both git-ignored). Supabase Auth is wired up (Phase 3B, see below); Supabase Storage remains a candidate for a later phase.

`DATABASE_URL` is a standard Postgres connection string (`postgresql+asyncpg://...`) and is **server-side only**. It is read by `apps/api` from the environment and is never sent to `apps/web` or exposed to browser JavaScript.

## Stack

- **SQLAlchemy 2.x** (async ORM) — models under `apps/api/app/db/models/`
- **asyncpg** — the Postgres driver SQLAlchemy's async engine uses
- **Alembic** — schema migrations, configured for SQLAlchemy's async engine

## Schema (Phase 3A)

### `profiles`

| column | type | notes |
|---|---|---|
| `id` | UUID | primary key, **no default**, `FOREIGN KEY REFERENCES auth.users(id) ON DELETE CASCADE` (migration `0002`) |

Phase 3A originally kept this table minimal: no default on `id`, no foreign key. Phase 3B (migration `0002`) added the foreign key to Supabase's own `auth.users` table. `id` values come only from the `sub` claim of a verified Supabase Auth access token — the backend never accepts a client-supplied id for a new profile. Rows are created app-level, get-or-create, the first time an authenticated user is seen (`apps/api/app/api/deps.py: get_current_profile`), not via a database trigger.

**`auth.users` stand-in (`apps/api/app/db/models/supabase_auth.py`):** this project doesn't own or migrate `auth.users` — Supabase does — but SQLAlchemy still needs a `Table` object registered in `Base.metadata` to resolve the `profiles.id → auth.users.id` foreign key string reference. That resolution happens during ORM mapper configuration, which runs globally for every mapped class on the *first* ORM query of any kind — so without this stand-in, even a query that never touches `profiles` (e.g. listing workspaces) raised `sqlalchemy.exc.NoReferencedTableError` against the real database. The stand-in declares only an `id` column, is never created via `create_all()` against a real database, and is explicitly excluded from Alembic's autogenerate diffing (`include_object` in `alembic/env.py`) so it can never be mistaken for a table this project should create, alter, or drop.

### `workspaces`

| column | type | notes |
|---|---|---|
| `id` | UUID | primary key |
| `name` | text | not null |
| `created_at` | timestamptz | `server_default now()` |
| `updated_at` | timestamptz | `server_default now()` |

### `workspace_members`

| column | type | notes |
|---|---|---|
| `workspace_id` | UUID | primary key (composite), FK → `workspaces.id`, `ON DELETE CASCADE` |
| `profile_id` | UUID | primary key (composite), FK → `profiles.id`, `ON DELETE CASCADE` |
| `role` | text | not null, default `"member"` |
| `created_at` | timestamptz | `server_default now()` |

`workspace_members.profile_id` has an `ON DELETE CASCADE` foreign key to `profiles.id` — this is required in Phase 3A even though nothing creates profile rows yet, so that Phase 3B's auth wiring doesn't need a schema change to satisfy it.

**Note on `updated_at`:** the SQLAlchemy model sets `onupdate=func.now()` on `workspaces.updated_at`. This is ORM-level behavior — it only fires when a row is updated through SQLAlchemy. It is **not** a Postgres trigger, so a row updated by raw SQL (e.g. directly in the Supabase SQL editor) will not have `updated_at` bumped automatically.

### Workspace ownership (Phase 3C)

`workspaces` has no `owner_id` column. Instead, the member row created alongside a new workspace is written with `role = "owner"` instead of the default `"member"` — `workspace_members.role` already existed for exactly this purpose, so no migration was needed. There's currently no invite flow, so in practice every workspace has exactly one member (its owner); authorization checks membership only, not role — see `docs/PRODUCT_REQUIREMENTS.md`'s explicit MVP non-goal on role-granularity.

### Workspace API (Phase 3C)

`apps/api/app/api/routes/workspaces.py` exposes:

| Method | Path | Notes |
|---|---|---|
| `POST` | `/workspaces` | Creates a workspace; caller becomes its `"owner"`. |
| `GET` | `/workspaces` | Lists the caller's workspaces, newest first. |
| `GET` | `/workspaces/{id}` | 404 if the workspace doesn't exist *or* the caller isn't a member — never 403, so a caller can't distinguish the two cases. |
| `PATCH` | `/workspaces/{id}` | Renames a workspace the caller belongs to. |
| `DELETE` | `/workspaces/{id}` | Deletes a workspace the caller belongs to; `workspace_members` rows cascade via the existing FK. |

All four member-scoped routes share one dependency, `get_workspace_access` (`apps/api/app/api/deps.py`), which does the membership check in a single query.

### `documents` (Phase 4)

| column | type | notes |
|---|---|---|
| `id` | UUID | primary key |
| `workspace_id` | UUID | FK → `workspaces.id`, `ON DELETE CASCADE`, indexed |
| `uploaded_by` | UUID | FK → `profiles.id`, `ON DELETE CASCADE` |
| `filename` | text | not null — sanitized to a bare filename (no path components) before storing |
| `content_type` | text | not null |
| `size_bytes` | bigint | not null |
| `storage_path` | text | not null — key into Supabase Storage, `{workspace_id}/{document_id}/{filename}`; never returned by the API |
| `created_at` | timestamptz | `server_default now()` |

`documents` stores metadata only — the file bytes live in a private Supabase Storage bucket, not Postgres. See "Document storage (Phase 4)" below.

### Document API (Phase 4)

`apps/api/app/api/routes/documents.py` exposes, all nested under a workspace and authorized via the same `get_workspace_access` dependency as the workspace routes (membership-only, 404 never 403):

| Method | Path | Notes |
|---|---|---|
| `POST` | `/workspaces/{workspace_id}/documents` | Multipart upload. Accepts `application/pdf` and `text/plain` only (415 otherwise), rejects empty files (422) and files over 10 MB (413). |
| `GET` | `/workspaces/{workspace_id}/documents` | Lists the workspace's documents, newest first. |
| `GET` | `/workspaces/{workspace_id}/documents/{document_id}` | 404 if the document doesn't exist, belongs to a different workspace, or the caller isn't a member. |
| `DELETE` | `/workspaces/{workspace_id}/documents/{document_id}` | Deletes the file from Storage, then the row. |

There is no download/read-back endpoint yet — Phase 4 only covers getting a file in and tracking its metadata. Reading file content back out is deferred to whichever phase first needs it (chunking/embeddings, Phase 5).

## Document storage (Phase 4)

Uploaded file bytes are stored in a **private** Supabase Storage bucket (default name `documents`, see `SUPABASE_STORAGE_BUCKET`), not in Postgres. `apps/api/app/core/storage.py` calls Supabase's Storage REST API directly via `httpx` — no Storage SDK is added, consistent with the database layer's existing "plain REST/SQL, no Supabase client library" approach.

This project does not configure Storage RLS policies (the same choice already made for the database — see "What's not built yet" below), so bucket writes require Supabase's **service_role** key rather than the anon key. Phase 3B deliberately avoided introducing `SUPABASE_SERVICE_ROLE_KEY` anywhere in the codebase specifically because nothing at the time needed it; Phase 4 revisits that only for Storage access, and only inside `app/core/storage.py` — it is never used for direct Postgres access and never sent to `apps/web`. See `docs/DECISIONS.md` for the full reasoning.

A `DocumentStorage` abstract interface (`app/core/storage.py`) sits between the routes and the Supabase-specific implementation, the same seam pattern as `get_db`/`get_current_user` — `apps/api/tests/test_documents.py` overrides it with an in-memory fake, so `pytest` needs no real Supabase Storage credentials or bucket.

**Manual setup step (not automatable from this codebase):** a private bucket matching `SUPABASE_STORAGE_BUCKET` must be created in the Supabase dashboard before uploads will work against a real project. This has not yet been done or verified against the real, connected Supabase project — unlike the database migrations, which have been applied and confirmed working end-to-end, Storage access is implemented and unit-tested only (fake storage backend), not yet exercised against real Supabase Storage.

## Readiness endpoint

`GET /ready` (`apps/api/app/api/routes/ready.py`) reports whether the backend can reach the database:

- **200** — `SELECT 1` succeeded against the configured database.
- **503** — `DATABASE_URL` is missing, the engine fails to initialize, the connection fails, or `SELECT 1` fails.

The error response never includes the connection string or the underlying driver exception — the client only ever sees `{"detail": "database unavailable"}`.

This is separate from `GET /health`, which reports only that the process is running and does not touch the database.

## Migrations

Migrations live in `apps/api/alembic/`, configured for SQLAlchemy's async engine. `alembic/env.py` reads the connection string from `DATABASE_URL` via `app.core.config.settings` — the connection string is never written into `alembic.ini`.

The initial migration (`alembic/versions/0001_initial_schema.py`) and the Phase 3B migration (`alembic/versions/0002_profiles_auth_fk.py`, adding `profiles.id → auth.users.id`) were both **hand-written**, not autogenerated, because `alembic revision --autogenerate` needs a live database connection to diff against, and neither was written with one. Both have since been applied to the real Supabase project (`alembic upgrade head`) — the schema above now exists there as described. No schema change was needed for Phase 3C (workspace management); it reuses this schema as-is.

To apply migrations against a real database:

```powershell
cd apps/api
$env:DATABASE_URL = "postgresql+asyncpg://..."
.\.venv\Scripts\python.exe -m alembic upgrade head
```

To create a new migration once real schema changes are needed against a real database, use `alembic revision --autogenerate -m "..."` and review the generated file before applying it — autogenerate is a starting point, not something to trust blindly (it doesn't reliably detect things like column renames).

## What's not built yet

- Row-Level Security (RLS) policies are not configured, for either the database or Storage; access control is enforced in the FastAPI layer (`get_workspace_access`) instead, since the backend connects with a direct Postgres connection rather than through Supabase's client libraries.
- No workspace invite/membership-management endpoints — a workspace currently gets members only via `POST /workspaces` (the creator, as `"owner"`); there's no way to add a second member yet.
- No per-role permission differences (e.g. only the owner may delete) — deliberately out of scope for MVP, see `docs/PRODUCT_REQUIREMENTS.md`.
- No document download/content-read endpoint yet (Phase 4 covers upload/list/delete only) — see "Document storage" above.
- Document upload has not yet been verified against a real, connected Supabase Storage bucket — only against the in-memory fake used by `pytest`.
