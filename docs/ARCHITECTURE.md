# OpsPilot AI — Architecture

> This document describes the *planned* architecture. As of Phase 0, none of it is implemented — see `docs/ROADMAP.md` for current status.

## Monorepo layout

```
opspilot-ai/
├── apps/
│   ├── web/     # Next.js frontend
│   └── api/     # FastAPI backend
├── docs/        # Planning and architecture documentation
```

`apps/web` and `apps/api` follow the standard convention used by Vercel's monorepo detection and tools like Turborepo/Nx: each top-level app has its own deployment root, so the frontend host points at `apps/web` and the backend host points at `apps/api`, with no ambiguity. No monorepo build tool is adopted yet — two apps in two different languages don't need one; this would only be reconsidered if a shared package (e.g. shared TypeScript types) becomes necessary.

## Responsibilities

### Frontend — `apps/web` (Next.js + TypeScript + Tailwind CSS + shadcn/ui)

- All user-facing UI: authentication screens, workspace dashboard, document upload, the RAG chat interface, the complaint queue, approval screens, the task board, and the agent execution timeline viewer.
- Calls the backend API for all business logic and AI operations; holds no business logic or AI logic itself.
- Owns presentation-layer state only (forms, optimistic UI updates, the client-side auth session).

### Backend — `apps/api` (Python + FastAPI + Pydantic + LangGraph)

- Single source of truth for business logic: documents, embeddings, RAG retrieval, complaint-analysis agent orchestration (LangGraph), approval gating, task creation, execution tracing, and feedback storage.
- Owns the **AI provider abstraction**: one internal interface that the rest of the backend calls, implemented by a Gemini adapter (hosted demo) and an Ollama adapter (local dev). Business logic never references a specific provider's request/response format directly — this keeps provider swaps cheap and keeps agent/RAG code testable without live API calls.
- Owns all secrets and all outbound calls to external services (AI providers, database, storage). The frontend never holds an AI provider key and never calls an AI provider directly.

### Data — PostgreSQL + pgvector (Supabase free plan)

- Supabase hosts the project's single Postgres database (free plan). The backend connects directly with SQLAlchemy's async engine (`asyncpg` driver) — the Supabase Python client is not used, keeping database access as plain, portable SQL/ORM code.
- Postgres holds relational data (users, workspaces, documents, complaints, tasks, agent run/trace records, feedback).
- The `pgvector` extension stores document chunk embeddings in the same database, avoiding a separate vector store.
- Supabase Auth is the planned authentication provider (Phase 3B): `profiles.id` will become a foreign key to `auth.users.id`. Supabase Storage is a candidate for document file storage from Phase 4 onward.

## Data flow (planned)

1. A user uploads a document to a workspace → backend stores the file, extracts text, chunks it, and generates embeddings locally (Sentence Transformers) → chunks + embeddings stored in Postgres/pgvector.
2. A user asks a question → backend embeds the question, retrieves the most relevant chunks via pgvector similarity search, and sends them plus the question to the active AI provider (Gemini or Ollama, via the abstraction layer) → answer returned with citations to the source chunks.
3. A complaint comes in → a LangGraph agent runs: analyze → draft response → recommend action, persisting its state at each step (for tracing) → the workflow pauses and awaits human approval before any recommended action is considered final → on approval, a task is created.

## Why this stack (zero-cost, portfolio-appropriate)

- **Supabase free plan**: managed Postgres with `pgvector` support at no cost, avoiding local database setup for a hosted demo, with a path to add Supabase Auth/Storage later without introducing a second platform.
- **Gemini free tier / Ollama**: Gemini gives a working hosted public demo without a paid key; Ollama lets development continue offline/free and keeps the provider abstraction honest by supporting two real providers from day one.
- **Local Sentence Transformers embeddings**: avoids paying for or rate-limiting on a hosted embeddings API for what is, for MVP purposes, a modest volume of documents.
- **Vercel + a free Python-compatible host**: standard, well-documented, zero-cost deployment path for a Next.js + FastAPI split app.

## Known architectural risks

See `docs/ROADMAP.md` and the Phase 0 planning discussion for the full list; the most consequential ones to keep in mind while building later phases:

- The AI provider abstraction must be designed before any RAG or agent code is written, or provider-specific concepts will leak into business logic.
- Human-in-the-loop workflows require durable, Postgres-backed LangGraph state (a paused workflow may wait hours for approval) — this must be planned before Phase 7, not added afterward.
- Free hosting tiers (especially the backend host) may cold-start slowly; this is a known, documented limitation of the public demo, not a bug.
