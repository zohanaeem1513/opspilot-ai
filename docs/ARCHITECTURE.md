# OpsPilot AI — Architecture

> This document describes the target architecture for the full MVP. Not all of it is implemented yet — see `docs/ROADMAP.md` for current phase-by-phase status.

## Monorepo layout

```text
opspilot-ai/
├── apps/
│   ├── web/     # Next.js frontend
│   └── api/     # FastAPI backend
├── docs/        # Planning and architecture documentation

apps/web and apps/api follow the standard convention used by Vercel's monorepo detection and tools like Turborepo/Nx: each top-level app has its own deployment root, so the frontend host points at apps/web and the backend host points at apps/api, with no ambiguity. No monorepo build tool is adopted yet — two apps in two different languages don't need one; this would only be reconsidered if a shared package (e.g. shared TypeScript types) becomes necessary.
Responsibilities
Frontend — apps/web (Next.js + TypeScript + Tailwind CSS + shadcn/ui)
- All user-facing UI: authentication screens, workspace dashboard, document upload and processing-status display, the planned RAG chat interface, the complaint queue, approval screens, the task board, and the agent execution timeline viewer.
- Calls the backend API for all business logic and AI operations; holds no business logic or AI logic itself.
- Owns presentation-layer state only (forms, optimistic UI updates, the client-side auth session).
- Uses Next.js Server Actions for authenticated workspace and document operations so backend URLs and server-side credentials are not exposed to browser JavaScript.
Backend — apps/api (Python + FastAPI + Pydantic + LangGraph)
- Single source of truth for business logic: documents, document processing, embeddings, RAG retrieval, complaint-analysis agent orchestration (LangGraph), approval gating, task creation, execution tracing, and feedback storage.
- Owns document-processing services: Storage download, text extraction, chunking, local embedding generation, processing-state management, and persistence of document chunks and vectors.
- Owns the AI provider abstraction: one internal interface that the rest of the backend will call, implemented by a Gemini adapter (hosted demo) and an Ollama adapter (local dev). Business logic must never reference a specific provider's request/response format directly — this keeps provider swaps cheap and keeps agent/RAG code testable without live API calls.
- Owns all secrets and all outbound calls to external services (AI providers, database, storage). The frontend never holds an AI provider key and never calls an AI provider directly.
Data — PostgreSQL + pgvector (Supabase free plan)
- Supabase hosts the project's single Postgres database (free plan). The backend connects directly with SQLAlchemy's async engine (asyncpg driver) — the Supabase Python client is not used, keeping database access as plain, portable SQL/ORM code.
- Postgres holds relational data including profiles, workspaces, workspace memberships, documents, document-processing state, document chunks, and later complaints, tasks, agent run/trace records, and feedback.
- The pgvector extension stores document chunk embeddings in the same database, avoiding a separate vector store.
- Document chunks are stored with 384-dimensional embeddings generated locally by Sentence Transformers using all-MiniLM-L6-v2.
- Supabase Auth is the authentication provider: profiles.id is a foreign key to auth.users.id.
- Supabase Storage is the implemented document file store. Uploaded PDF/TXT file bytes live in a private Storage bucket, while document metadata, processing state, chunks, and embeddings live in PostgreSQL.
Data flow
1. Document upload and processing — implemented: a user uploads a PDF/TXT document to a workspace → backend stores the file in private Supabase Storage → document metadata is stored in Postgres → backend downloads the stored file through the DocumentStorage abstraction → extracts text → creates overlapping chunks → generates local Sentence Transformers embeddings → stores chunks + 384-dimensional vectors in Postgres/pgvector → document is marked processed or failed.
2. RAG Q&A — planned for Phase 6: a user asks a question → backend embeds the question → retrieves the most relevant chunks via pgvector similarity search → sends those chunks plus the question to the active AI provider (Gemini or Ollama, through the provider abstraction) → answer is returned with citations to the source chunks.
3. Complaint workflow — planned: a complaint comes in → a LangGraph agent runs: analyze → draft response → recommend action, persisting its state at each step for tracing → the workflow pauses and awaits human approval before any recommended action is considered final → on approval, a task is created.
Document processing architecture
Document processing is split into small backend services so each responsibility remains independently testable and replaceable:
- app/services/text_extraction.py — extracts UTF-8 text from plain-text files and selectable text from PDFs using pypdf.
- app/services/chunking.py — normalizes extracted text and splits it into overlapping chunks.
- app/services/embeddings.py — generates normalized local embeddings using Sentence Transformers and all-MiniLM-L6-v2.
- app/services/document_processing.py — coordinates Storage download, extraction, chunking, embedding generation, chunk persistence, and document processing state.
- app/core/storage.py — provides the DocumentStorage abstraction with upload, download, and delete, keeping Supabase-specific Storage calls outside document-processing business logic.
Processing status is stored explicitly on each document:
uploaded → processing → processed
                      ↘ failed

A processing failure does not remove the uploaded document. Instead, the document remains visible with status = "failed" and a safe processing_error message.
The current MVP processes documents synchronously as part of the upload flow. This keeps the architecture simple for the current scale, but the processing service is isolated enough that it can later be moved behind a background job/worker if document volume or processing latency grows.
Why this stack (zero-cost, portfolio-appropriate)
- Supabase free plan: managed Postgres with pgvector, Auth, and Storage at no cost, keeping database, authentication, and document storage on one platform without introducing additional infrastructure.
- Gemini free tier / Ollama: Gemini is planned to provide a hosted public demo without a paid provider key; Ollama allows local development and keeps the provider abstraction flexible by supporting a second provider.
- Local Sentence Transformers embeddings: avoids paying for or rate-limiting on a hosted embeddings API for what is, for MVP purposes, a modest volume of documents. all-MiniLM-L6-v2 produces the 384-dimensional embeddings currently stored in pgvector.
- PostgreSQL + pgvector: keeps relational document metadata and vector embeddings in the same database, avoiding a separate vector database and making workspace/document relationships straightforward to enforce.
- Vercel + a free Python-compatible host: standard, well-documented, zero-cost deployment path for a Next.js + FastAPI split app.
Known architectural risks
See docs/ROADMAP.md and the Phase 0 planning discussion for the full list; the most consequential ones to keep in mind while building later phases:
- The AI provider abstraction must be designed before Phase 6's RAG generation code is written, or provider-specific concepts could leak into business logic.
- Document processing currently runs synchronously during upload. Large files or cold Sentence Transformer model startup can increase request time; a background worker/job system may be needed later if throughput grows.
- Text-based PDFs are supported, but scanned/image-only PDFs do not currently use OCR and therefore may fail with no extractable text.
- Human-in-the-loop workflows require durable, Postgres-backed LangGraph state (a paused workflow may wait hours for approval) — this must be planned before Phase 7, not added afterward.
- Free hosting tiers (especially the backend host) may cold-start slowly; this is a known, documented limitation of the public demo, not a bug.
