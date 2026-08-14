# CLAUDE.md

Instructions for Claude Code when working in this repository.

## Project

OpsPilot AI — an AI business-operations platform (RAG over uploaded documents, complaint analysis agent, human-in-the-loop approval, task creation, agent tracing, feedback/eval). Full context in `docs/PRODUCT_REQUIREMENTS.md` and `docs/ARCHITECTURE.md`.

This is the user's **first Claude Code / portfolio project**. Explain important architecture and coding decisions in simple, beginner-friendly language before making them. Do not make major decisions without explaining them first.

## Current phase

See `docs/ROADMAP.md` for the authoritative phase list and status. Work on **one phase at a time** — do not jump ahead to later phases or scaffold code for future phases "while we're at it."

## Monorepo layout

```
apps/web   — Next.js + TypeScript + Tailwind + shadcn/ui
apps/api   — Python + FastAPI + Pydantic + LangGraph
docs/      — planning and architecture docs
```

## Stack constraints

- Zero-cost stack only: Supabase (Postgres + pgvector) free plan, Gemini free tier for the hosted demo, Ollama for local dev, local Sentence Transformers for embeddings, Vercel + a free Python-compatible host for deployment.
- All AI provider calls must go through a single provider-abstraction layer in the backend — never call Gemini/Ollama-specific APIs directly from business logic.
- Frontend never holds AI provider keys or talks to AI providers directly; it only calls the backend API.

## Quality rules

- Never claim a planned feature already exists; mark unfinished functionality as planned.
- Never invent users, metrics, benchmarks, or performance numbers.
- Keep the MVP realistic — do not overengineer or add speculative abstractions.
- Keep documentation professional enough for a public GitHub repository.
- Never place secrets or real API keys in any file — use `.env.example` with placeholders only.
- Ask before destructive or major operations (deleting files, force-push, schema drops, etc.).
- No comments in code beyond what's needed to explain non-obvious "why" — see the user's global code style preferences.

## Workflow expectations

- Confirm architecture/approach with the user before writing code for a new phase.
- Prefer small, testable increments per phase over large multi-phase changes.
- Update `docs/ROADMAP.md` status and `docs/DECISIONS.md` when a phase completes or a significant decision is made.
