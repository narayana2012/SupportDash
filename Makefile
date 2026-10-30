.PHONY: help setup backend seed ingest demo mcp test lint smoke terraform-validate

# Commands from CLAUDE.md section 14. Only setup works today.
# The rest fail on purpose until the phase that adds them lands (see PLAN_PHASE.md),
# so nothing reports success for code that does not exist yet.

help:
	@echo "setup               install dependencies and create .env from .env.example (works)"
	@echo "backend seed ingest demo mcp test lint smoke terraform-validate"
	@echo "                    not implemented yet; each prints the phase that adds it"

setup:
	uv sync
	@test -f .env || cp .env.example .env
	@echo "Created .env if it was missing. Keep DEMO_MODE=true and LLM_PROVIDER=fake for offline runs."

backend:
	@echo "make backend: not implemented yet. Phase 1 (runtime skeleton) adds backend/app/main.py." >&2
	@exit 1

seed:
	@echo "make seed: not implemented yet. Phase 2 (persistence and demo data) adds it." >&2
	@exit 1

ingest:
	@echo "make ingest: not implemented yet. Phase 5 (knowledge pipeline) adds it." >&2
	@exit 1

demo:
	@echo "make demo: not implemented yet. Phase 10 adds the CD-1002 pause; Phase 13 completes the checkpoint." >&2
	@exit 1

mcp:
	@echo "make mcp: not implemented yet. Phase 10 or later adds the read-only MCP server (integrations/mcp/server.py)." >&2
	@exit 1

test:
	@echo "make test: not implemented yet. Phase 1 adds the offline pytest harness (tests/conftest.py)." >&2
	@exit 1

lint:
	@echo "make lint: not implemented yet. Add ruff config with the backend in Phase 1." >&2
	@exit 1

smoke:
	@echo "make smoke: not implemented yet. Phase 13 (evaluation and delivery) adds it. Needs BASE_URL." >&2
	@exit 1

terraform-validate:
	@echo "make terraform-validate: not implemented yet. Phase 13 adds deployment/{aws,azure,gcp}." >&2
	@exit 1
