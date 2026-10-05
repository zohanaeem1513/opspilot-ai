# OpsPilot AI — Database

## Platform

[Supabase](https://supabase.com) hosts the project's single PostgreSQL database (free plan). The backend talks to it directly through SQLAlchemy's async engine (`asyncpg` driver) — it does **not** use the Supabase Python client. A real Supabase project is connected (`apps/api/.env`, `apps/web/.env.local`, both git-ignored). Supabase Auth is wired up (Phase 3B), and Supabase Storage is now also implemented and verified for document file storage.

`DATABASE_URL` is a standard Postgres connection string (`postgresql+asyncpg://...`) and is **server-side only**. It is read by `apps/api` from the environment and is never sent to `apps/web` or exposed to browser JavaScript.

## Stack

- **SQLAlchemy 2.x** (async ORM) — models under `apps/api/app/db/models/`
- **asyncpg** — the Postgres driver SQLAlchemy's async engine uses
- **Alembic** — schema migrations, configured for SQLAlchemy's async engine
- **pgvector** — stores document chunk embeddings directly in PostgreSQL
- **Supabase Storage** — stores uploaded document file bytes outside PostgreSQL

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

### `documents` (Phases 4–5)

| column | type | notes |
|---|---|---|
| `id` | UUID | primary key |
| `workspace_id` | UUID | FK → `workspaces.id`, `ON DELETE CASCADE`, indexed |
| `uploaded_by` | UUID | FK → `profiles.id`, `ON DELETE CASCADE` |
| `filename` | text | not null — sanitized to a bare filename (no path components) before storing |
| `content_type` | text | not null |
| `size_bytes` | bigint | not null |
| `storage_path` | text | not null — key into Supabase Storage, `{workspace_id}/{document_id}/{filename}`; never returned by the API |
| `status` | varchar | not null, default `"uploaded"`; processing state: `uploaded`, `processing`, `processed`, or `failed` |
| `processing_error` | varchar, nullable | safe user-facing reason when document processing fails |
| `created_at` | timestamptz | `server_default now()` |

`documents` stores metadata and processing state only — the original file bytes live in a private Supabase Storage bucket, not Postgres.

Phase 5 added `status` and `processing_error` through migration `0004_document_processing.py`.

### `document_chunks` (Phase 5)

`document_chunks` is created by migration `0004_document_processing.py` and stores the extracted text pieces used for semantic retrieval.

| column | type | notes |
|---|---|---|
| `id` | UUID | primary key |
| `document_id` | UUID | FK → `documents.id`, `ON DELETE CASCADE`, indexed |
| `workspace_id` | UUID | FK → `workspaces.id`, `ON DELETE CASCADE`, indexed |
| `chunk_index` | integer | zero-based position of the chunk within the source document |
| `content` | text | extracted and normalized document text for this chunk |
| `embedding` | vector(384) | normalized local Sentence Transformers embedding |
| `created_at` | timestamptz | `server_default now()` |

The pair:

```text
(document_id, chunk_index)