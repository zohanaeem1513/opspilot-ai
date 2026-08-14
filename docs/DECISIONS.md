# OpsPilot AI — Decisions Log

A running log of significant architecture decisions and the reasoning behind them, so the "why" isn't lost as the project grows. Newest entries at the top.

---

## 2026-08-14 — Phase 3B Supabase Authentication: dual-algorithm JWT verification, no service-role key, app-level profile creation

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
