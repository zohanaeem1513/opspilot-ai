# OpsPilot AI — Roadmap

Development proceeds one phase at a time. Each phase should be independently runnable and testable before the next one starts. Status is updated as work progresses.

| Phase | Description | Status |
|---|---|---|
| 0 | Planning & repository foundation (this phase: docs, license, gitignore, env example) | ✅ Done |
| 1 | Backend skeleton — FastAPI app, health-check endpoint, project structure, pytest set up. No DB, no AI calls. | ⏳ Planned |
| 2 | Frontend skeleton — Next.js + TypeScript + Tailwind + shadcn/ui, one page calling the backend health-check. | ⏳ Planned |
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
