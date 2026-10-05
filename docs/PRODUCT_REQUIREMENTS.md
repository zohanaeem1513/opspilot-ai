# OpsPilot AI — Product Requirements

## Problem

Small and mid-size businesses accumulate internal knowledge (policies, FAQs, product docs) that's hard to search, and handle customer complaints manually with no consistent trail of what was decided, why, or who approved it. OpsPilot AI addresses both: a searchable knowledge base with cited answers, and an AI-assisted complaint-handling workflow that keeps a human in control of any consequential action.

## Target user

A small business team (e.g. a support/ops team) that wants AI assistance answering internal questions and triaging customer complaints, without giving an AI system unsupervised authority to act on customers' behalf.

## MVP feature set

The following describe the target MVP feature set; see `docs/ROADMAP.md` for the authoritative implementation status. Items 1–4 are now implemented; item 5 onward remains planned.

1. **User authentication** — sign up / log in, scoped to a business workspace.
2. **Business workspace** — a tenant boundary; a workspace's documents, complaints, and tasks are isolated from other workspaces.
3. **Document upload** — upload internal documents (e.g. PDFs, text) into a workspace's knowledge base.
4. **Document chunking and embeddings** — documents are split into chunks and embedded (locally, via Sentence Transformers) for retrieval.
5. **RAG questions with source citations** — ask a natural-language question, get an answer grounded in the workspace's documents, with citations back to the source chunks.
6. **Customer complaint analysis** — submit or ingest a customer complaint; an AI agent analyzes its content (e.g. category, sentiment, urgency).
7. **AI-generated response drafts** — the agent drafts a suggested reply to the customer.
8. **Recommended business actions** — the agent recommends a follow-up action (e.g. "issue refund," "escalate to manager").
9. **Human approval before important actions** — any recommended action pauses for a human to approve, edit, or reject before it's considered "done."
10. **Internal task creation** — an approved action creates a trackable internal task.
11. **Agent execution timeline** — a step-by-step, inspectable trace of what the agent did for a given complaint (what it read, what it decided, what tools it called).
12. **Basic feedback and evaluation** — users can rate AI outputs (e.g. thumbs up/down), building a small dataset for future evaluation.

## Out of scope for MVP

To keep this a realistic first portfolio project, the following are explicitly **not** planned for the MVP and would only be considered afterward:

- Multi-language support
- Real-time customer-facing chat widget
- Billing/subscriptions
- Fine-tuning custom models
- Mobile apps
- Role-based permission granularity beyond a single "workspace member" role
- Automated (non-human-approved) execution of any action with real-world/customer-facing effect

## Success criteria for the portfolio goal

The project should demonstrably show, in working code: RAG with citations, a LangGraph-based stateful agent, tool calling, a human-in-the-loop pause/resume workflow, structured (Pydantic-validated) AI outputs, an inspectable execution trace, and a basic feedback/evaluation loop — running as a real FastAPI + Next.js application, documented and tested well enough for a public repository.