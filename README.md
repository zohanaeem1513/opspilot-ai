# OpsPilot AI

An intelligent business-operations platform: upload internal documents, ask questions over them with cited sources (RAG), analyze customer complaints with an AI agent, draft responses, recommend actions, require human approval before anything consequential happens, and track the resulting tasks — with full visibility into what the AI agent did and why.

> **Status: Phase 5 — Chunking & Embeddings complete. Phase 6 — RAG Q&A is next.**
>
> Phases 0–5 are now implemented. Users can authenticate, create workspaces, upload PDF/TXT documents to real Supabase Storage, and have those documents processed automatically. The backend downloads the stored file, extracts text, splits it into overlapping chunks, generates local Sentence Transformers embeddings, and stores the chunks plus 384-dimensional vectors in PostgreSQL/pgvector.
>
> Phase 4's real-environment verification is complete: the private Supabase Storage bucket is configured and document upload/list/delete has been exercised through the real browser flow. Phase 5 has also been verified end-to-end: TXT and text-based PDF uploads reach `Processed`, whitespace-only text reaches `Failed` with a useful processing error, and a stored embedding was verified directly in `document_chunks` with `vector_dims(embedding) = 384`. `pytest` (52/52), `ruff check`, `npm run lint`, and `npm run build` pass. See [docs/ROADMAP.md](docs/ROADMAP.md) for what's built vs. planned and [docs/DECISIONS.md](docs/DECISIONS.md) for the design decisions.

This is a portfolio project built to demonstrate practical, production-style AI engineering: Retrieval-Augmented Generation, stateful AI agents, tool calling, human-in-the-loop workflows, structured outputs, agent execution tracing, and evaluation/feedback — on top of a real FastAPI + Next.js application.

## Planned tech stack

**Frontend:** Next.js, TypeScript, Tailwind CSS, shadcn/ui  
**Backend:** Python, FastAPI, Pydantic, LangGraph  
**AI:** Provider-agnostic abstraction — Gemini free tier (hosted demo), Ollama (local dev), local Sentence Transformers (embeddings)  
**Data:** PostgreSQL + pgvector (via Supabase free plan), Supabase Auth, Supabase Storage  
**Deployment:** Vercel (frontend), a free Python-compatible host (backend), GitHub (source control)

All choices above target a **$0 cost** setup suitable for a public portfolio demo. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the reasoning behind each choice.

## Repository layout

```text
opspilot-ai/
├── apps/
│   ├── web/     # Next.js frontend (auth pages + workspace/document dashboard)
│   └── api/     # FastAPI backend (health/readiness, Supabase Auth, workspace + document processing API)
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
- [Database](docs/DATABASE.md) — schema, migrations, pgvector, Storage, and the `/ready` connectivity check

## Development status

`apps/api` is implemented and runnable:

- FastAPI backend is implemented and runnable, with `GET /health` (liveness) and `GET /ready` (Postgres connectivity check — 200 when reachable, 503 when `DATABASE_URL` is missing or the database can't be reached) endpoints.
- Supabase Postgres schema is defined via SQLAlchemy 2.x async models with Alembic migrations and **applied to the real Supabase project**. Migrations now cover the initial workspace schema (`0001`), Supabase Auth profile foreign key (`0002`), document metadata (`0003`), and document processing/chunk embeddings (`0004`) — see [docs/DATABASE.md](docs/DATABASE.md).
- Supabase Auth access tokens are verified locally (`app/core/security.py`) — HS256 with a shared secret or JWKS with asymmetric keys, whichever the Supabase project actually uses (this project uses ES256/JWKS); no algorithm is hard-coded, and no Supabase SDK is involved in token verification.
- A protected `GET /me` endpoint and an app-level profile get-or-create (`app/api/deps.py`) demonstrate the auth flow end-to-end; `profiles.id` has a foreign key to `auth.users.id` (migration `0002`).
- Workspace management is implemented: `POST/GET /workspaces` and `GET/PATCH/DELETE /workspaces/{id}`, authorized per-caller via `get_workspace_access` (`app/api/deps.py`) — a workspace that doesn't exist and one the caller isn't a member of both return 404, never 403. No new migration was needed; workspace ownership is represented by `workspace_members.role = "owner"` on the creating member. See [docs/DATABASE.md](docs/DATABASE.md).
- Document upload is implemented: `POST/GET /workspaces/{id}/documents` and `GET/DELETE /workspaces/{id}/documents/{document_id}`, reusing the same `get_workspace_access` authorization. Document metadata lives in the `documents` table (migration `0003`); file bytes live in a private Supabase Storage bucket via the `DocumentStorage` abstraction (`app/core/storage.py`), which calls Supabase's Storage REST API directly with `httpx`. The real Storage bucket is configured and the browser upload flow has been verified against the connected Supabase project.
- Document processing is implemented (Phase 5): the Storage abstraction now supports file download, `app/services/text_extraction.py` extracts UTF-8 TXT and text-based PDF content, `app/services/chunking.py` creates overlapping chunks, `app/services/embeddings.py` generates local Sentence Transformers embeddings with `all-MiniLM-L6-v2`, and `app/services/document_processing.py` coordinates the complete processing flow.
- Migration `0004_document_processing.py` adds document processing status/error fields and the `document_chunks` table with pgvector `vector(384)` embeddings. Documents move through `uploaded`, `processing`, `processed`, or `failed`, and safe processing errors are retained for failed documents.
- Phase 5 has been exercised against the real environment: TXT and text-based PDF documents reached `Processed`; a whitespace-only TXT file reached `Failed` with `document contains no extractable text`; and a direct database query confirmed a real stored document chunk with a 384-dimensional embedding.
- pytest passed — 52/52, covering health-check, readiness, database-session, JWT verification (both signing paths), `/me`, workspace API, document API (including cross-user access-denial and upload-validation cases), and ORM mapper configuration. Workspace and document API tests use an in-memory SQLite database and fake in-memory Storage rather than requiring production credentials.
- `profiles.id`'s foreign key to Supabase's `auth.users.id` needs a matching `Table` object in SQLAlchemy's metadata to resolve — production code registers a minimal stand-in for it (`app/db/models/supabase_auth.py`), excluded from Alembic autogenerate so it's never mistaken for a table this project should manage. See [docs/DECISIONS.md](docs/DECISIONS.md).
- App import check passed.
- Live `GET /health` check against a running `uvicorn` server passed.
- `ruff check` passes with no findings.

`apps/web` is implemented and runnable:

- Next.js frontend is implemented and runnable, showing a small OpsPilot AI dashboard-style homepage.
- The homepage fetches the backend's `GET /health` endpoint server-side (never in browser JavaScript) and displays **Operational** with the real `service`/`version`/`environment` values when the backend is reachable, or **Unavailable** without crashing when it isn't.
- `npm run lint` and `npm run build` pass; the production build succeeds with Next.js 16.3.8. The current build only reports the non-blocking Next.js deprecation warning for the `middleware` file convention.
- A live check against a running FastAPI backend passed, and the graceful "Unavailable" fallback was verified by stopping the backend and reloading the page.
- Manual visual verification of the layout at a narrow/mobile viewport is **pending** — responsive Tailwind classes are implemented, but no browser/viewport tool was available in the original development environment to confirm the result visually.
- `/login`, `/register`, `/dashboard` pages, session-refreshing middleware (`src/middleware.ts`), and Supabase browser/server client helpers (`src/lib/supabase/`), using `@supabase/supabase-js` and `@supabase/ssr`. The register → login → `/dashboard` flow has been confirmed working against the real, connected Supabase project.
- The dashboard fetches, creates, renames, and deletes real workspaces via Next.js Server Actions (`src/app/dashboard/actions.ts`) that resolve the session server-side and call the backend — the browser never receives `API_BASE_URL`, `DATABASE_URL`, or any service-role key.
- Each workspace has a document upload form and document list (`src/components/workspaces/document-manager.tsx`), backed by the same Server Actions pattern. The document list now also displays processing status (`Processed` / `Failed`) and processing errors returned by the backend.

Local embedding generation and pgvector persistence are now implemented. Generative AI, semantic retrieval, and RAG Q&A are not built yet; development proceeds one phase at a time, with Phase 6 next. See the roadmap for details.

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

Then visit `http://localhost:3000`. The frontend reads the backend's URL from a server-only `API_BASE_URL` environment variable (see `.env.example`), defaulting to `http://127.0.0.1:8000` if unset. An `apps/web/.env.local` (git-ignored, see `.env.example`) is required for the auth pages and dashboard to work — it must set `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` for your own Supabase project; the homepage's health check works without it.

## License

MIT — see [LICENSE](LICENSE).