# OpsPilot AI

An intelligent business-operations platform: upload internal documents, ask questions over them with cited sources (RAG), analyze customer complaints with an AI agent, draft responses, recommend actions, require human approval before anything consequential happens, and track the resulting tasks — with full visibility into what the AI agent did and why.

> **Status: Phase 3A — Database Foundation (done).**
> `apps/api` is a working, runnable FastAPI backend with `GET /health` and `GET /ready` (real Postgres connectivity check) endpoints, plus a Supabase Postgres schema (`profiles`, `workspaces`, `workspace_members`) defined with SQLAlchemy 2.x async models and Alembic migrations. `apps/web` is a working, runnable Next.js frontend that displays the real status of `GET /health`. pytest (mocked database behavior, no real credentials needed), `ruff check`/`ruff format --check`, the app import check, `npm run lint`/`typecheck`/`build`, and a live frontend↔backend check have all passed. Migrations have not been applied to any real database, and no auth is wired up yet (planned for Phase 3B). See [docs/ROADMAP.md](docs/ROADMAP.md) for what's built vs. planned and [docs/DATABASE.md](docs/DATABASE.md) for schema details.

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
- pytest passed (health-check, readiness, and database-session test suites — all using mocked database behavior, no real Supabase credentials required).
- App import check passed.
- Live `GET /health` check against a running `uvicorn` server passed.
- `ruff check` and `ruff format --check` both pass with no findings.

`apps/web` is implemented and runnable:

- Next.js frontend is implemented and runnable, showing a small OpsPilot AI dashboard-style homepage.
- The homepage fetches the backend's `GET /health` endpoint server-side (never in browser JavaScript) and displays **Operational** with the real `service`/`version`/`environment` values when the backend is reachable, or **Unavailable** without crashing when it isn't.
- `npm run lint`, `npm run typecheck`, and `npm run build` all passed; `build` succeeds without the backend running.
- A live check against a running FastAPI backend passed, and the graceful "Unavailable" fallback was verified by stopping the backend and reloading the page.
- Manual visual verification of the layout at a narrow/mobile viewport is **pending** — responsive Tailwind classes are implemented, but no browser/viewport tool was available in the development environment to confirm the result visually.

No AI integration has been built yet, and no data has been written to a real database. Development proceeds one phase at a time; see the roadmap for details.

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
