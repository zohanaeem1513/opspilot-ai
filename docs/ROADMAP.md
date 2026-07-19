# OpsPilot AI — Roadmap

Development proceeds one phase at a time. Each phase should be independently runnable and testable before the next one starts. Status is updated as work progresses.

| Phase | Description | Status |
|---|---|---|
| 0 | Planning & repository foundation (this phase: docs, license, gitignore, env example) | ✅ Done |
| 1 | Backend skeleton — FastAPI app, health-check endpoint, project structure, pytest set up. No DB, no AI calls. | 🟡 Implemented — Ruff verification pending |
| 2 | Frontend skeleton — Next.js + TypeScript + Tailwind + shadcn/ui, one page calling the backend health-check. | ✅ Done — mobile visual check pending |
| 3 | Database & auth — Neon Postgres with pgvector enabled, auth wired up, workspace/user data model. | ⏳ Planned |
| 4 | Document upload & storage — upload endpoint, file storage, document metadata records. | ⏳ Planned |
| 5 | Chunking & embeddings — text extraction, chunking strategy, local Sentence Transformers embeddings stored in pgvector. | ⏳ Planned |
| 6 | RAG Q&A — AI provider abstraction (Gemini/Ollama), retrieval + generation with source citations. | ⏳ Planned |
| 7 | Complaint analysis agent — LangGraph workflow: classify → draft response → recommend action. | ⏳ Planned |
| 8 | Human-in-the-loop approval — pause/resume workflow, approval UI, task creation on approval. | ⏳ Planned |
| 9 | Agent execution tracing — persisted step-by-step timeline and a UI viewer for it. | ⏳ Planned |
| 10 | Feedback & evaluation — thumbs up/down on AI outputs, a simple eval script/dataset. | ⏳ Planned |
| 11 | Testing polish, deployment configuration, final documentation pass. | ⏳ Planned |

## Notes

- Phases are intentionally small. A phase should not start until the previous one works end-to-end for its own scope.
- No phase beyond the current one should be scaffolded "early" — this avoids half-finished code sitting unused and keeps the repo honest about what's actually working.
- This table should be updated whenever a phase's status changes.
- **Phase 1 known limitation:** `ruff check`/`ruff format --check` could not be run on the development machine used to build this phase — a Windows Application Control policy blocks execution of the downloaded `ruff.exe`, unrelated to the code itself. `pytest`, the app import check, and a live `uvicorn` + `GET /health` request all passed. Ruff config is in place in `apps/api/pyproject.toml`; running the lint/format checks on a machine without this restriction is a follow-up, not a blocker for later phases.
- **Phase 2 known limitation:** `npm run lint`, `npm run typecheck`, and `npm run build` all passed, and the page was verified live against a running FastAPI backend (real `service`/`version`/`environment` values rendered) and verified to degrade gracefully (no crash) when the backend was stopped. Responsive Tailwind classes were implemented for mobile widths, but no browser/viewport tool was available in the development environment to visually confirm the mobile layout — that manual check is still pending.
