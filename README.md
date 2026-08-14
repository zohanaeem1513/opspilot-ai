# OpsPilot AI

An intelligent business-operations platform: upload internal documents, ask questions over them with cited sources (RAG), analyze customer complaints with an AI agent, draft responses, recommend actions, require human approval before anything consequential happens, and track the resulting tasks — with full visibility into what the AI agent did and why.

> **Status: Phase 3B — Supabase Authentication (in progress).**
> `apps/api` now also verifies Supabase Auth access tokens locally (HS256 or JWKS, whichever the Supabase project uses — no algorithm is hard-coded), exposes a protected `GET /me`, and creates a `profiles` row for each newly authenticated user (`profiles.id` now foreign-keys to `auth.users.id`). `pytest` (25/25, mocked/local-only, no real Supabase credentials), `ruff check`, and `ruff format --check` all pass. `apps/web` has Supabase login/registration/logout pages, a session-refreshing middleware guarding `/dashboard`, and an auth-aware homepage. `npm install`, `npm run lint`, `npm run typecheck`, and `npm run build` all pass. No real Supabase project has been created or connected to, no `.env`/`.env.local` was created, and no migration has been applied to any database — so the auth flow has not yet been exercised against a live login. See [docs/ROADMAP.md](docs/ROADMAP.md) for what's built vs. planned and [docs/DECISIONS.md](docs/DECISIONS.md) for the Phase 3B design.

This is a portfolio project built to demonstrate practical, production-style AI engineering: Retrieval-Augmented Generation, stateful AI agents, tool calling, human-in-the-loop workflows, structured outputs, agent execution tracing, and evaluation/feedback — on top of a real FastAPI + Next.js application.

## Planned tech stack

**Frontend:** Next.js, TypeScript, Tailwind CSS, shadcn/ui
**Backend:** Python, FastAPI, Pydantic, LangGraph
**AI:** Provider-agnostic abstraction — Gemini free tier (hosted demo), Ollama (local dev), local Sentence Transformers (embeddings)
**Data:** PostgreSQL + pgvector (via Supabase free plan), Supabase Auth planned for a later phase
**Deployment:** Vercel (frontend), a free Python-compatible host (backend), GitHub (source control)

All choices above target a **$0 cost** setup suitable for a public portfolio demo. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the reasoning behind each choice.

## Repository layout

```
opspilot-ai/
├── apps/
│   ├── web/     # Next.js frontend (Phase 2: health-status dashboard skeleton)
│   └── api/     # FastAPI backend (Phase 3A: health/readiness + Supabase Postgres schema)
├── docs/        # Planning and architecture documentation
├── README.md
├── CLAUDE.md
├── LICENSE
├── .gitignore
└── .env.example
```

## Documentation

- [Product Requirements](docs/PRODUCT_REQUIREMENTS.md) — what OpsPilot AI does and the MVP feature set
- [Architecture](docs/ARCHITECTURE.md) — system design and stack rationale
- [Roadmap](docs/ROADMAP.md) — development phases and current progress
- [Decisions](docs/DECISIONS.md) — a log of significant architecture decisions and why they were made
- [Database](docs/DATABASE.md) — schema, migrations, and the `/ready` connectivity check

## Development status

`apps/api` is implemented and runnable:

- FastAPI backend is implemented and runnable, with `GET /health` (liveness) and `GET /ready` (Postgres connectivity check — 200 when reachable, 503 when `DATABASE_URL` is missing or the database can't be reached) endpoints.
- Supabase Postgres schema is defined via SQLAlchemy 2.x async models (`profiles`, `workspaces`, `workspace_members`) with Alembic migrations, but **has not been applied to any real database** — see [docs/DATABASE.md](docs/DATABASE.md).
- Supabase Auth access tokens are verified locally (`app/core/security.py`) — HS256 with a shared secret or JWKS with asymmetric keys, whichever the Supabase project actually uses; no algorithm is hard-coded, and no Supabase SDK or service-role key is involved.
- A protected `GET /me` endpoint and an app-level profile get-or-create (`app/api/deps.py`) demonstrate the auth flow end-to-end; `profiles.id` now has a foreign key to `auth.users.id` (migration `0002`, not yet applied to any real database).
- pytest passed — 25/25, covering health-check, readiness, database-session, JWT verification (both signing paths), and `/me` route test suites, all using mocked/local-only behavior, no real Supabase credentials required.
- App import check passed.
- Live `GET /health` check against a running `uvicorn` server passed.
- `ruff check` and `ruff format --check` both pass with no findings.

`apps/web` is implemented and runnable:

- Next.js frontend is implemented and runnable, showing a small OpsPilot AI dashboard-style homepage.
- The homepage fetches the backend's `GET /health` endpoint server-side (never in browser JavaScript) and displays **Operational** with the real `service`/`version`/`environment` values when the backend is reachable, or **Unavailable** without crashing when it isn't.
- `npm run lint`, `npm run typecheck`, and `npm run build` all passed; `build` succeeds without the backend running.
- A live check against a running FastAPI backend passed, and the graceful "Unavailable" fallback was verified by stopping the backend and reloading the page.
- Manual visual verification of the layout at a narrow/mobile viewport is **pending** — responsive Tailwind classes are implemented, but no browser/viewport tool was available in the development environment to confirm the result visually.
- **New in Phase 3B:** `/login`, `/register`, `/dashboard` pages, session-refreshing middleware (`src/middleware.ts`), and Supabase browser/server client helpers (`src/lib/supabase/`), using `@supabase/supabase-js` and `@supabase/ssr`. `npm run lint`, `npm run typecheck`, and `npm run build` all pass with these additions. Not yet manually verified against a real login — that requires a real Supabase project, which has not been created (see `docs/DECISIONS.md`).

No AI integration has been built yet, no data has been written to a real database, and no real Supabase project has been created or connected to. Development proceeds one phase at a time; see the roadmap for details.

To run the backend locally:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Then visit `http://127.0.0.1:8000/health`.

To run the frontend locally (in a separate terminal, with the backend running):

```powershell
cd apps/web
npm install
npm run dev
```

Then visit `http://localhost:3000`. The frontend reads the backend's URL from a server-only `API_BASE_URL` environment variable (see `.env.example`), defaulting to `http://127.0.0.1:8000` if unset — no `.env.local` file is required for local development unless you want to override that default.

## License

MIT — see [LICENSE](LICENSE).
