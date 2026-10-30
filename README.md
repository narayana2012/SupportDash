# SupportDash

Autonomous customer-support resolution platform for the fictional SaaS **supportdash**. A support agent opens a ticket, runs one AI workflow, inspects every step, and approves anything that spends money or changes an account. Demo mode runs offline with no API key.

## Status

This repository holds the specification and scaffolding. The backend, frontend, tests, and delivery files are not in the repo yet. Phase 1 has not started in the repo. `MEMORY.md` "Honest status" is the authority on what is implemented, validated, and deployed.

## Documents

| File | Purpose |
|---|---|
| `CLAUDE.md` | Specification. Wins over every other document. |
| `PLAN.md` | Requirement catalog (F1–F14, N1–N8) and acceptance bar |
| `PLAN_PHASE.md` | 13-phase build order and exit criteria |
| `TASKS.md` | Execution checklist with `feature/<name>` branches |
| `MEMORY.md` | Locked decisions and honest status |
| `docs/API_CONTRACT.md` | Routes, payloads, and roles |
| `docs/ARCHITECTURE.md` | Components, workflow, data model, infrastructure |
| `docs/Git_GitHub_Workflow_Guide.md` | Branches and pull requests |
| `.cursor/skills/supportdash-support/SKILL.md` | Agent procedure for working on this repo |
| `.env.example` | Every environment variable, with placeholders only |

## Stack

Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async), LangChain and LangGraph, PyJWT, pytest.
Frontend: Next.js 15 (App Router), TypeScript, Tailwind.
Data: PostgreSQL (Supabase) or SQLite in demo, Redis or fakeredis, Qdrant or an in-memory vector store.

## Commands

Run from the repository root. Each command is listed in `CLAUDE.md` section 14. Commands that do not exist yet fail on purpose in the `Makefile`.

| Command | Status | Added by |
|---|---|---|
| `make setup` | Works. Runs `uv sync` and creates `.env` from `.env.example` if missing. | Now |
| `make backend` | Not implemented | Phase 1 |
| `make test` | Not implemented | Phase 1 |
| `make seed` | Not implemented | Phase 2 |
| `make ingest` | Not implemented | Phase 5 |
| `make demo` | Not implemented | Phase 10, checkpoint in Phase 13 |
| `make demo TICKET=CD-1005` | Not implemented | Phase 10 |
| `make mcp` | Not implemented | Phase 10 or later |
| `make lint` | Not implemented | Phase 1 |
| `make smoke` | Not implemented | Phase 13 |
| `make terraform-validate` | Not implemented | Phase 13 |

Frontend commands (`npm run dev`, `lint`, `test -- --run`, `build`) run from `frontend/` once it exists.

## Demo data

Thirteen tickets (`CD-1001` to `CD-1013`) and eight customers. Demo users: `admin@supportdash.demo`, `sam.agent@supportdash.demo`, `vic.viewer@supportdash.demo`.

## Git

Feature branches come from `development` and open pull requests against `development`. `testing` and `main` are promotion branches. See `docs/Git_GitHub_Workflow_Guide.md`.
