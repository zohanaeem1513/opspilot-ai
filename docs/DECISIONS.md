# OpsPilot AI — Decisions Log

A running log of significant architecture decisions and the reasoning behind them, so the "why" isn't lost as the project grows. Newest entries at the top.

---

## 2026-10-05 — Phase 5 Document Processing: local Sentence Transformers embeddings stored in pgvector

**Decision:** Uploaded PDF/TXT documents are processed by the FastAPI backend after their file bytes and metadata have been stored. `apps/api/app/core/storage.py` extends the existing `DocumentStorage` abstraction with `download()` so the processing layer can read files back from Supabase Storage without directly depending on Supabase-specific APIs. Processing is split into small services: `app/services/text_extraction.py` extracts UTF-8 text from plain-text files and selectable text from PDFs using `pypdf`; `app/services/chunking.py` normalizes and splits text into overlapping chunks; `app/services/embeddings.py` generates normalized local embeddings with Sentence Transformers using `all-MiniLM-L6-v2`; and `app/services/document_processing.py` coordinates download → extraction → chunking → embedding generation → database persistence.

Migration `0004_document_processing.py` enables the pgvector extension for this processing flow, adds `status` and `processing_error` to `documents`, and creates `document_chunks`. Each chunk stores its `document_id`, `workspace_id`, zero-based `chunk_index`, extracted `content`, and a `vector(384)` embedding. `(document_id, chunk_index)` is unique, and chunk rows cascade when their parent document is deleted. Documents explicitly move through `uploaded`, `processing`, `processed`, or `failed`, rather than requiring the UI to infer processing state.

**Why:** Local Sentence Transformers preserve the project's $0-cost requirement and avoid introducing a paid embeddings API before the RAG layer exists. `all-MiniLM-L6-v2` produces compact 384-dimensional vectors that are sufficient for the MVP's document-retrieval scope. Keeping vectors inside the existing Supabase PostgreSQL database through pgvector avoids introducing a separate vector database and keeps document/workspace relationships enforceable through normal relational foreign keys.

Splitting extraction, chunking, embeddings, and orchestration into separate services keeps each concern small and independently replaceable. For example, the embedding model can later change without rewriting PDF extraction, or the chunking strategy can change without modifying Storage access. Extending the existing `DocumentStorage` interface with `download()` preserves the provider boundary introduced in Phase 4 instead of letting document-processing code call Supabase directly.

A processing failure is treated differently from an upload failure. Once the file and document metadata are stored successfully, an extraction/embedding failure does not make the upload request disappear or delete the file. The document remains visible with `status = "failed"` and a safe `processing_error`, which makes failures inspectable and retryable later.

**Current trade-off:** document processing runs synchronously as part of the upload request. This is intentionally simple for the MVP, but cold Sentence Transformer startup or larger documents can make upload requests slower. The processing logic is isolated enough that it can later be moved behind a background job/worker if throughput or latency becomes a problem.

**Verification:** the complete flow has been exercised against the real connected environment. A TXT document and a text-based PDF both reached `Processed`; a whitespace-only TXT document reached `Failed` with `document contains no extractable text`; and a direct PostgreSQL query confirmed a stored document chunk with `vector_dims(embedding) = 384`. The backend test suite passes 52/52, `ruff check` passes, frontend lint passes, and the Next.js production build succeeds.

---

## 2026-08-17 — Phase 4 Document Upload: Supabase Storage over local disk or Postgres bytea, service_role key scoped to Storage only

**Decision:** Document files are stored in a private Supabase Storage bucket (`SUPABASE_STORAGE_BUCKET`, default `documents`), not on the backend's local filesystem and not as `bytea` in Postgres. `apps/api/app/core/storage.py` defines a small `DocumentStorage` abstract interface (`upload`/`delete`, later extended with `download` in Phase 5) and a `SupabaseStorage` implementation that calls Supabase's Storage REST API directly via `httpx` — no Storage SDK, matching the existing "plain REST/SQL, no Supabase client library" choice already made for the database (see the 2026-08-14 entry below). `documents` (migration `0003`) stores metadata only — `id`, `workspace_id`, `uploaded_by`, `filename`, `content_type`, `size_bytes`, `storage_path` — never the file bytes. Uploads are restricted to `application/pdf` and `text/plain`, capped at 10 MB, and rejected if empty. All four routes (`app/api/routes/documents.py`) sit under `/workspaces/{workspace_id}/documents` and reuse the existing `get_workspace_access` dependency, so authorization (membership-only, 404-never-403) is identical to the workspace routes with no new logic. `apps/api/tests/test_documents.py` overrides the `get_storage` FastAPI dependency with an in-memory fake, the same seam pattern already used for `get_db`/`get_current_user`, so `pytest` needs no real Supabase Storage credentials or bucket.

Because a private Storage bucket without RLS policies otherwise rejects all access, uploads/deletes require Supabase's **service_role** key — the single most powerful Supabase credential, since it bypasses RLS on both Postgres and Storage. `SUPABASE_SERVICE_ROLE_KEY` is now introduced into `apps/api`'s configuration, revisiting the Phase 3B decision (below) not to add it. Its use is deliberately narrow: only `app/core/storage.py` ever reads it, it is never used for direct Postgres access, and it is never sent to `apps/web`.

**Why:** Three storage options were considered. Local filesystem storage was rejected because most free backend hosting tiers have an ephemeral filesystem — uploaded files would not reliably survive a redeploy or restart, which is unacceptable for a feature whose whole point is that the file persists. Storing file bytes as Postgres `bytea` was rejected as atypical for file storage and something that would bloat the single free-tier database once real documents are uploaded, without buying any simplicity Supabase Storage doesn't already provide. Supabase Storage was chosen because it's already part of the connected, zero-cost Supabase project — no new platform, no new cost. Using the service_role key (rather than building out Storage RLS policies with a lesser-privileged key) mirrors the project's existing, already-documented choice to enforce all authorization in the FastAPI layer instead of database-level RLS (`docs/DATABASE.md`, "What's not built yet") — introducing Storage RLS now would mean maintaining two separate, parallel authorization systems (FastAPI membership checks, and Storage bucket policies) that must always agree, for no real safety gain given the FastAPI layer already fully gates access before any Storage call is made. Restricting the service_role key's use to a single module keeps that broadened exposure auditable and testable in isolation, rather than letting it leak into database code where the 2026-08-14 entry's original reasoning against it still fully applies.

**Update (2026-10-05):** the earlier real-environment verification gap is now closed. A private Supabase Storage bucket matching the configured bucket name exists in the real connected project, and document upload/list/delete has been exercised through the browser against real Supabase Storage. Phase 5 also verified Storage read-back by downloading and processing real TXT and PDF uploads through the same `DocumentStorage` abstraction.

---

## 2026-08-16 — Fix: `auth.users` stand-in table, so ORM queries stop failing against the real database

**Decision:** `apps/api/app/db/models/supabase_auth.py` registers a minimal, one-column (`id`) SQLAlchemy `Table` for `auth.users` (`schema="auth"`) into `Base.metadata`, imported (for its registration side effect, `# noqa: F401`) from `apps/api/app/db/models/__init__.py` alongside the real models. `apps/api/alembic/env.py` now passes `include_object=_include_object` to both `context.configure()` calls, a filter that excludes anything in the `auth` schema from autogenerate diffing. No migration was added or changed, and the real `profiles.id → auth.users.id` foreign key (migration `0002`) is untouched.

**Why:** `GET /me` and `GET /workspaces` were both returning 500 against the real Supabase database with `sqlalchemy.exc.NoReferencedTableError: ... could not find table 'auth.users'`. `profiles.id`'s foreign key is a *string* reference (`ForeignKey("auth.users.id")`); SQLAlchemy resolves that string against `Base.metadata.tables` during ORM mapper configuration — and mapper configuration runs once, globally, for every mapped class in the registry, triggered by the *first* ORM query of any kind. Since `auth.users` was never registered anywhere in production code (Supabase owns and creates that table; this codebase only ever added a foreign key *to* it via migration `0002`, never a `Table` object for it), that first query — even `GET /workspaces`, which never touches `profiles` — failed mapper configuration for the whole registry, not just for `Profile`. This is also why `pytest` reported 38/38 passing despite the bug: `apps/api/tests/test_workspaces.py` had its *own* local `auth.users` stub for its in-memory SQLite database, which happened to satisfy the same resolution requirement and masked the fact that production code never provided one. The fix moves that stub into production code (so real Postgres/Supabase gets it too) and removes the now-redundant copy from the test file. The `include_object` filter exists so that if this schema is later autogenerate-diffed, Alembic can never conclude it should alter or drop Supabase's real, much wider `auth.users` table to match this one-column stand-in. See `apps/api/tests/test_db_models.py` for the regression test (mapper configuration, no database required) and `docs/DATABASE.md` for the schema-level writeup.

---

## 2026-08-16 — Phase 3C Workspace Management: reuse `workspace_members.role` for ownership, membership-only authorization, Server Actions on the frontend

**Decision:** Workspace CRUD (`POST/GET /workspaces`, `GET/PATCH/DELETE /workspaces/{id}`, `apps/api/app/api/routes/workspaces.py`) is built entirely on the existing `workspaces`/`workspace_members` schema from migration `0001` — no new migration. `workspaces` has no `owner_id` column; instead, the member row created alongside a new workspace is written with `role = "owner"` instead of the default `"member"`. Authorization is membership-only, not role-based: any member (in practice, currently only the owner, since there's no invite flow) can rename or delete a workspace, matching the MVP non-goal on role-granularity in `docs/PRODUCT_REQUIREMENTS.md`. A single dependency, `get_workspace_access` (`apps/api/app/api/deps.py`), backs `GET`/`PATCH`/`DELETE` — it joins `workspaces`/`workspace_members` on `(workspace_id, profile.id)` in one query and returns 404, never 403, whether the workspace doesn't exist or the caller just isn't a member. `DELETE` issues a plain `DELETE FROM workspaces WHERE id = ...` rather than `session.delete()`, so the database's own `ON DELETE CASCADE` (already present on `workspace_members.workspace_id`) removes member rows — `session.delete()` would instead have the ORM try to null out `workspace_members.workspace_id`, which fails because that column is part of a composite primary key. On `apps/web`, workspace mutations go through Next.js Server Actions (`apps/web/src/app/dashboard/actions.ts`) that resolve the Supabase session server-side and call the backend, rather than exposing `API_BASE_URL` to browser JS and adding CORS to FastAPI — consistent with the existing server-side-only fetch pattern. Backend tests (`apps/api/tests/test_workspaces.py`) run against a real in-memory SQLite database (`aiosqlite`, added as a dev-only dependency) rather than hand-rolled mocks, since authorization correctness (row exists vs. row belongs to caller) needs a real query to be trustworthy.

**Why:** `workspace_members.role` already existed for exactly this purpose (see the Phase 3A entry below), so reusing it satisfies "a workspace has an owner" with zero schema change. Skipping owner-only permission gating avoids building authorization machinery for a role distinction the product requirements explicitly declare out of scope for MVP. Returning 404 uniformly (never 403) prevents a caller from using response codes to probe for the existence of other users' workspace UUIDs. Server Actions keep the access token and backend URL out of browser JavaScript without requiring a CORS policy change on `apps/api` — the same reasoning already used for the Phase 2 homepage health check. A real SQLite database in tests (over fakes) was chosen because the thing actually being tested — that user B's requests for user A's workspace correctly fail — is exactly the kind of query-level logic that's easy to get wrong and easy to fake into passing.

---

## 2026-08-14 — Phase 3B Supabase Authentication: dual-algorithm JWT verification, no service-role key, app-level profile creation

> **Update (2026-08-16):** a real Supabase project (ES256/JWKS signing) is now connected, migration `0002` has been applied to it, and the register → login → `/dashboard` → `GET /me` flow has been confirmed working end-to-end — see the Phase 3C entry above and `docs/ROADMAP.md`. The "not yet applied to any real database" note below describes the state at the time this decision was made, not the current state.

**Decision:** `apps/api` verifies Supabase Auth access tokens locally (`app/core/security.py`), never by calling the Supabase Auth API per request and never via the Supabase Python client — `PyJWT` is the only dependency added. Verification supports **either** signing algorithm a Supabase project might use, selected at runtime by which setting is configured: `SUPABASE_JWT_SECRET` for the legacy shared-secret (HS256) setup, or `SUPABASE_URL` (fetching the project's public JWKS) for asymmetric signing (RS256/ES256). Exactly one is expected to be set, matching whichever algorithm the real project actually uses — this is deliberately not assumed or hard-coded. A third setting, `SUPABASE_JWT_ISSUER`, is always required regardless of algorithm; the `iss` claim is validated on every token, and a token missing `iss` entirely is rejected, not silently accepted. `SUPABASE_SERVICE_ROLE_KEY` is not introduced anywhere in the codebase. `profiles.id` now has `FOREIGN KEY (id) REFERENCES auth.users(id) ON DELETE CASCADE` (migration `0002`, hand-written like `0001`, not yet applied to any real database), and profile rows are created app-level (`app/api/deps.py: get_current_profile`, a get-or-create keyed on the verified token's `sub` claim) rather than via a Postgres trigger on `auth.users`. A minimal `GET /me` endpoint is the protected-route proof-of-concept. On `apps/web`, `@supabase/ssr` + `@supabase/supabase-js` handle login/registration/logout and cookie-based sessions; `src/middleware.ts` guards `/dashboard` using `supabase.auth.getUser()` (which re-validates against Supabase rather than trusting the cookie's decoded payload); the existing homepage stays public. Email confirmation on signup is assumed disabled for this MVP (a Supabase dashboard setting, not yet applied).

**Why:** Calling the Supabase Auth API per request would add latency and an external dependency to every authenticated backend request; local verification avoids both. Not assuming a signing algorithm up front avoids hard-coding a choice that depends on a specific Supabase project's dashboard configuration, which wasn't known at implementation time. Requiring and validating `iss` (in addition to signature, expiration, and audience) closes a gap where a token issued by a different, unrelated Supabase project — if it happened to share a signing key/audience by coincidence — could otherwise pass verification. `SUPABASE_SERVICE_ROLE_KEY` is the most dangerous Supabase secret (bypasses all access control) and nothing in this phase's design needs it. App-level profile creation keeps the logic in testable Python rather than a SQL trigger living outside Alembic's normal review path, consistent with the Phase 3A decision below to keep database access as portable, standard code rather than Supabase-specific mechanisms. `getUser()` (not `getSession()`) is used in the middleware and dashboard page specifically because it re-validates the token against Supabase rather than trusting a potentially stale or tampered cookie.

---

## 2026-08-14 — `apps/api` Phase 3A database foundation: Supabase Postgres, SQLAlchemy async + asyncpg + Alembic

**Decision:** Supabase (free plan) replaces Neon as the single PostgreSQL platform for the project — this supersedes the Neon choice in the 2026-07-19 zero-cost-stack entry below. The backend connects directly via SQLAlchemy 2.x's async engine with the `asyncpg` driver; the Supabase Python client is not added. Schema changes go through Alembic, configured for the async engine, with `DATABASE_URL` read at runtime from environment/settings rather than written into `alembic.ini`. Three tables are introduced: `profiles` (Phase 3A: bare UUID primary key, no default, no foreign key, no rows created by this codebase yet), `workspaces` (id/name/timestamps), and `workspace_members` (composite PK of `workspace_id`/`profile_id`, both foreign keys with `ON DELETE CASCADE`, plus `role`). A `GET /ready` endpoint reports 200/503 based on real database connectivity (`SELECT 1`), never exposing the connection string or driver exception to the client, and is distinct from the existing `GET /health` liveness check.

**Why:** Supabase gives a Postgres platform that can later add managed Auth and Storage on the same project without introducing a second platform, which Neon (Postgres-only) would have required for Phase 3B/4. Direct SQLAlchemy/asyncpg access (rather than the Supabase client library) keeps the backend's database layer as portable, standard Python/SQL — the code isn't coupled to a Supabase-specific SDK, and it stays consistent with using Alembic for migrations. `workspace_members.profile_id` is given its `ON DELETE CASCADE` foreign key now, in Phase 3A, even though no profile rows exist yet, so that Phase 3B's auth wiring (which adds `profiles.id → auth.users.id`) doesn't require a schema migration just to add a constraint that was always going to be needed. The initial Alembic migration is hand-written rather than autogenerated, because autogenerate requires a live database connection to diff against, and this phase's development explicitly does not connect to the real hosted Supabase database — it was instead verified with Alembic's offline SQL-generation mode, which never opens a network connection.

---

## 2026-07-19 — `apps/web` Phase 2 frontend skeleton: npm, App Router, server-only health fetch

**Decision:** `apps/web` is scaffolded with `create-next-app` using npm, TypeScript, Tailwind CSS, ESLint, the App Router with a `src/` directory, and the `@/*` import alias. shadcn/ui is initialized (its current default style, "Neutral" base color) with only `card`, `badge`, and `button` added. The homepage's `GET /health` check runs as a server-side fetch inside an `async` Server Component (`src/lib/api.ts`), reading a server-only `API_BASE_URL` environment variable (no `NEXT_PUBLIC_` prefix, default `http://127.0.0.1:8000`, 3-second timeout, `cache: "no-store"`), with the page marked `export const dynamic = "force-dynamic"`.

**Why:** npm matches the approved stack and avoids introducing a second package manager alongside the backend's pip-based tooling. The App Router + `src/` dir is the current Next.js convention and keeps app code separate from config files. Fetching `/health` server-side means the request happens in Node.js, not the browser — so no CORS configuration is needed on the FastAPI backend for this phase, and the backend's base URL/config is never bundled into client JavaScript. `force-dynamic` keeps `npm run build` working without the backend running, since the page's data depends on a live request rather than build-time content. This corrected `.env.example`'s original Phase-0 placeholder (`NEXT_PUBLIC_API_BASE_URL`), which assumed a client-exposed variable rather than a server-only one.

---

## 2026-07-19 — `apps/api` packaging: Hatchling build backend + editable install

**Decision:** `apps/api/pyproject.toml` declares `hatchling` under `[build-system]` (a build-time-only dependency, not runtime or dev) and the package is installed with `pip install -e ".[dev]"`.

**Why:** FastAPI's tests need `from app.main import app` to work without manual `sys.path` hacking. Hatchling is the current minimal-config standard for turning a plain `app/` folder into an installable package (no `setup.py`), and editable install means code edits are picked up immediately with no reinstall step. `requires-python = ">=3.12"` is set as the project's minimum supported version, and Ruff's `target-version` is pinned to `"py312"` to match it — deliberately *not* matching the local dev interpreter (Python 3.14.6), so Ruff would flag any accidental use of 3.13+/3.14-only syntax as a portability problem.

---

## 2026-07-19 — Monorepo folder naming: `apps/web` + `apps/api`

**Decision:** Use `apps/web` (Next.js frontend) and `apps/api` (FastAPI backend) rather than flat top-level `frontend/` and `backend/` folders.

**Why:** This matches Vercel's monorepo auto-detection and common conventions (Turborepo/Nx), keeps each app's deployment root unambiguous, and scales cleanly if a third app (e.g. a worker or admin tool) is added later. Considered and rejected: flat `frontend/`/`backend/` — simpler to read for a first project, but less conventional if monorepo tooling is adopted later.

---

## 2026-07-19 — License: MIT

**Decision:** Public repository uses the MIT License.

**Why:** Most permissive, most common choice for a portfolio project — signals the code can be freely inspected and reused with attribution, which fits the goal of showing this work to recruiters/employers. Considered and rejected: no license — technically leaves the repo's reuse terms ambiguous (default copyright applies) even though it's public.

---

## 2026-07-19 — No monorepo build tool (Turborepo/Nx/pnpm workspaces) yet

**Decision:** Use plain folders (`apps/web`, `apps/api`) without adopting a monorepo build/task tool.

**Why:** With only two apps in two different languages (TypeScript and Python), a shared build tool doesn't yet pay for itself. Revisit only if a shared package (e.g. shared TypeScript types generated from the API) becomes necessary.

---

## 2026-07-19 — AI provider abstraction is a backend-only concern

**Decision:** All AI provider calls (Gemini, Ollama) go through a single abstraction layer inside `apps/api`. The frontend never calls an AI provider directly and never holds an AI provider key.

**Why:** Keeps the frontend simple and secret-free, and keeps provider-specific request/response formats from leaking into business logic — swapping or adding a provider later should only require a new adapter behind the same interface, not changes throughout the codebase.

---

## 2026-07-19 — Zero-cost stack for the public demo

> **Superseded in part on 2026-08-14:** the Postgres platform below was changed from Neon to Supabase — see that entry above. The rest of this decision (Gemini/Ollama, local embeddings, Vercel + free backend host) still stands.

**Decision:** Neon (Postgres + pgvector) free plan, Gemini free tier for the hosted demo, Ollama for local development, local Sentence Transformers for embeddings, Vercel + a free Python-compatible host for deployment.

**Why:** The project must be runnable and demoable at $0 cost. Trade-off accepted: free hosting tiers (especially the backend host) may have cold-start delays or usage limits, which will be documented as known limitations rather than hidden or worked around with paid infrastructure.