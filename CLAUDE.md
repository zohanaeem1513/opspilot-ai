# CLAUDE.md

Instructions for Claude Code when working in this repository.

## Project

OpsPilot AI — an AI business-operations platform (RAG over uploaded documents, complaint analysis agent, human-in-the-loop approval, task creation, agent tracing, feedback/eval). Full context in `docs/PRODUCT_REQUIREMENTS.md` and `docs/ARCHITECTURE.md`.

This is the user's **first Claude Code / portfolio project**. Explain important architecture and coding decisions in simple, beginner-friendly language before making them. Do not make major decisions without explaining them first.

## Current phase

Phases 0–5 are complete. The next phase is **Phase 6 — RAG Q&A**.

See `docs/ROADMAP.md` for the authoritative phase list and status. Work on **one phase at a time** — do not jump ahead to later phases or scaffold code for future phases "while we're at it."

Phase 6 should build on the existing Phase 5 document-processing foundation:

- uploaded PDF/TXT files are stored in Supabase Storage
- extracted text is split into document chunks
- local Sentence Transformers embeddings are generated with `all-MiniLM-L6-v2`
- embeddings are stored in PostgreSQL/pgvector as `vector(384)`
- document processing state is tracked with `uploaded`, `processing`, `processed`, and `failed`

Do not rebuild or replace this pipeline unless there is a specific reason discussed with the user first.

## Monorepo layout

```text
apps/web   — Next.js + TypeScript + Tailwind + shadcn/ui
apps/api   — Python + FastAPI + Pydantic + LangGraph
docs/      — planning and architecture docs

##Stack constraints

- Zero-cost stack only: Supabase (Postgres + pgvector, Auth, Storage) free plan, Gemini free tier for the hosted demo, Ollama for local dev, local Sentence Transformers for embeddings, Vercel + a free Python-compatible host for deployment.
- All AI provider calls must go through a single provider-abstraction layer in the backend — never call Gemini/Ollama-specific APIs directly from business logic.
- Frontend never holds AI provider keys or talks to AI providers directly; it only calls the backend API.
- Existing document embeddings use all-MiniLM-L6-v2 and are stored as 384-dimensional pgvector values.
- Supabase Storage access stays behind the existing DocumentStorage abstraction rather than being called directly from business logic.
- PostgreSQL remains the relational database and vector store; do not introduce a separate vector database for the MVP.

 ##Quality rules

- Never claim a planned feature already exists; mark unfinished functionality as planned.
- Never invent users, metrics, benchmarks, or performance numbers.
- Keep the MVP realistic — do not overengineer or add speculative abstractions.
- Keep documentation professional enough for a public GitHub repository.
- Never place secrets or real API keys in any file — use .env.example with placeholders only.
- Ask before destructive or major operations (deleting files, force-push, schema drops, etc.).
- No comments in code beyond what's needed to explain non-obvious "why" — see the user's global code style preferences.
- Preserve workspace isolation in all document retrieval and future RAG queries.
- Do not expose DATABASE_URL, SUPABASE_SERVICE_ROLE_KEY, AI provider keys, or other backend-only credentials to browser JavaScript.
- When changing database schema, use Alembic migrations and review them before applying them.
- Keep document-processing failures explicit and user-safe rather than silently ignoring them.

 ## Workflow expectations

- Confirm architecture/approach with the user before writing code for a new phase.
- Prefer small, testable increments per phase over large multi-phase changes.
- Update docs/ROADMAP.md status and docs/DECISIONS.md when a phase completes or a significant decision is made.
- Update docs/DATABASE.md when schema or persistence behavior changes.
- Update docs/ARCHITECTURE.md when a meaningful system-level flow or responsibility changes.
- Run the relevant backend/frontend checks before considering a phase complete.
- Verify important integrations against the real connected environment when unit tests use fakes or local substitutes.