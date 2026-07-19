# OpsPilot AI — Decisions Log

A running log of significant architecture decisions and the reasoning behind them, so the "why" isn't lost as the project grows. Newest entries at the top.

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
