# OpsPilot AI — Decisions Log

A running log of significant architecture decisions and the reasoning behind them, so the "why" isn't lost as the project grows. Newest entries at the top.

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

**Decision:** Neon (Postgres + pgvector) free plan, Gemini free tier for the hosted demo, Ollama for local development, local Sentence Transformers for embeddings, Vercel + a free Python-compatible host for deployment.

**Why:** The project must be runnable and demoable at $0 cost. Trade-off accepted: free hosting tiers (especially the backend host) may have cold-start delays or usage limits, which will be documented as known limitations rather than hidden or worked around with paid infrastructure.
