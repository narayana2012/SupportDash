---
name: supportdash-support
description: Agent procedure for building, reviewing, or testing the supportdash support-resolution platform (Project 1). Use for any change to supportdash code, docs, tests, or phase work. Reads CLAUDE.md first, follows the order in PLAN_PHASE.md and TASKS.md, keeps policy in rules and approvals outside the model, and keeps status claims honest.
---

# supportdash support: agent procedure

`CLAUDE.md` is the spec. If this file disagrees with it, `CLAUDE.md` wins. If `PLAN_PHASE.md` disagrees with `CLAUDE.md`, `CLAUDE.md` wins too.

## 1. Before you change anything

1. Read `CLAUDE.md` sections that touch your change. Section 18 is the coding rules. Section 18.1 is what must never happen.
2. Find the phase and the task. Use `PLAN_PHASE.md` for exit criteria and `TASKS.md` for the branch name (`feature/<name>`).
3. Read the requirement row in `PLAN.md` (F1–F14, N1–N8) and the existing test for that area.
4. For any route or payload, read `docs/API_CONTRACT.md` first. It is the source of truth for routes and types.
5. Check what really exists with `ls` and `git log`. Do not assume a file, test, or merge exists because a document says so. `MEMORY.md` "Honest status" records what is verified.

## 2. How to work

- One `TASKS.md` row is one branch and one pull request. Branch from an up-to-date `development`. Open the PR against `development`. Never commit to `development`, `testing`, or `main` directly. See `docs/Git_GitHub_Workflow_Guide.md`.
- Commit or push only when the user asks.
- Keep the layers from `CLAUDE.md` 4.2. API code holds no business rules. Repositories hold all SQL. Agents never write SQL. Only `ToolRegistry` runs tools. `core` never imports `agents/`.

## 3. Non-negotiable rules

1. **Rules before the model.** Policy cases (dispute, deletion, security, data loss, legal, enterprise outage) are decided by `agents/rules.py`, deterministically and with tests. The model adds judgement only in grey areas.
2. **Severity only goes up.** Rules can raise the model's severity. They never lower it.
3. **Structured outputs.** Every agent returns a Pydantic model through `call_structured`. No free-text parsing. No LLM call outside `call_structured`.
4. **Tools only through the registry.** `ToolRegistry.execute(name, args, approved=…)` is the one path. Unknown tools need approval. Tool exceptions become `ToolResult(ok=False)`.
5. **Plans are deterministic.** `ResolutionAgent.plan_actions` decides actions. The model does not invent tool calls.
6. **Ticket text is data.** Anything from a ticket, email, file, or web page goes through `wrap_untrusted`. CD-1013 must never export records or change the route.
7. **Money and accounts need approval.** Refunds, setting resets, deletions, and disputes never run unattended. `CD-1002` must pause.
8. **Interrupts stay small.** No side effects before `interrupt()`, because code before it re-runs on resume.
9. **Reducers append.** `errors` and `completed_nodes` are appended, never overwritten.
10. **Customer output is validated.** `validate_customer_output` runs before any reply is shown. A failure raises risk to `high`.
11. **Memory is scrubbed.** Notes go through `scrub()`. Never store card numbers, keys, passwords, raw ticket bodies, or another customer's data.
12. **Secrets stay out of git.** Never commit `.env`, `data/`, `*.db`, `terraform.tfvars`, `backend.hcl`, `tfplan`, or any real key. Only `.env.example` is committed, with placeholders.
13. **Migrations are additive.** Never edit an applied migration. Never drop data without an explicit decision.

## 4. Roles and access

`viewer` reads tickets, customers, knowledge, and audit. `agent` also runs workflows, replies, requests info, approves or rejects, and escalates. `admin` also reindexes knowledge and changes settings. A viewer gets 403 on run, reply, approve, and reject. `docs/API_CONTRACT.md` has the full access table.

## 5. Contract and status discipline

- If a route changes, update `docs/API_CONTRACT.md`, `backend/app/schemas/`, and `frontend/lib/types.ts` in the same change.
- If a requirement changes, update `PLAN.md`, the affected phase in `PLAN_PHASE.md`, and the test that proves it.
- Every new test names the requirement ID it proves (for example `F9`, `N4`).
- Use the honest-status ladder: implemented, validated locally, needs cloud credentials, actually deployed. Do not write "deployed" or "passes in CI" until that is true. Update `MEMORY.md` "Honest status" when status changes.

## 6. Before you report done

1. Run the offline tests. Once `make test` exists it must pass with no network and no API key. Until then, say that no test command exists yet.
2. For a phase checkpoint, run `make demo` when it exists. It must still pause on `CD-1002` and escalate `CD-1005`.
3. Check the layer rules and the things that must never happen (`CLAUDE.md` 18.1).
4. Update `MEMORY.md` honest status and the `PLAN_PHASE.md` status row if a phase moved.
5. Say what is not done. Do not hide a skipped step.

## 7. Commands

Commands and their status are listed in `README.md`. Stubs in `Makefile` fail on purpose until their phase lands. Setup is `make setup`. Frontend commands run from `frontend/` once it exists: `npm run dev`, `npm run lint`, `npm run test -- --run`, `npm run build`.

On Windows, use `.venv/Scripts/python.exe`, set `PYTHONPATH` to include `backend` (with `;`), and set `PYTHONIOENCODING=utf-8` for CLI output with symbols.

## 8. Where things live

| Need | File |
|---|---|
| Spec and coding rules | `CLAUDE.md` |
| Requirement catalog and acceptance | `PLAN.md` |
| Phase order and exit criteria | `PLAN_PHASE.md` |
| Execution tasks and branches | `TASKS.md` |
| Routes and types | `docs/API_CONTRACT.md` |
| Design and diagrams | `docs/ARCHITECTURE.md` |
| Locked facts and honest status | `MEMORY.md` |
| Git and PR flow | `docs/Git_GitHub_Workflow_Guide.md` |
| Environment variables | `.env.example` |
