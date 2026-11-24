# Voice ERP kit — shortcuts. `make help` lists them.
.DEFAULT_GOAL := help
COMPOSE := docker compose
API_PORT ?= $(or $(shell grep -E '^API_PORT=' .env 2>/dev/null | cut -d= -f2),4000)
WEB_PORT ?= $(or $(shell grep -E '^WEB_PORT=' .env 2>/dev/null | cut -d= -f2),5173)

help: ## list the commands
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

setup: ## first run: checks, builds, starts everything in Docker (see SETUP.md)
	@COMPANY=$(COMPANY) ./scripts/setup.sh

up: ## start backend + ai + web in Docker (http://localhost:5173)
	$(COMPOSE) up -d --build
	@echo "→ http://localhost:$(WEB_PORT)   (logs: make logs)"

down: ## stop the containers (data is kept)
	$(COMPOSE) down

restart: ## restart after editing .env
	$(COMPOSE) up -d --force-recreate

logs: ## follow the logs of all services
	$(COMPOSE) logs -f --tail=100

ps: ## container status
	$(COMPOSE) ps

reset: ## reload the ERP from the data pack (wipes your changes; works for Docker and local)
	@curl -fsS -X POST http://localhost:$(API_PORT)/api/admin/reset && echo

rebuild: ## after adding a dependency (pyproject.toml or package.json changed)
	$(COMPOSE) build --no-cache && $(COMPOSE) up -d

clean: ## stop and delete the containers AND the database volume
	$(COMPOSE) down -v

offline: ## no internet: load the images from the USB stick (IMAGES=/path/to/voice-erp-kit-images-<arch>.tar or .tar.gz) and start
	@test -n "$(IMAGES)" || { echo "usage: make offline IMAGES=/path/to/voice-erp-kit-images-<arch>.tar"; exit 1; }
	@test -f "$(IMAGES)" || { echo "file not found: $(IMAGES)"; exit 1; }
	@test -f .env || cp .env.example .env
	docker load -i "$(IMAGES)"   # accepts .tar and .tar.gz
	$(COMPOSE) up -d --no-build
	@echo "→ http://localhost:$(WEB_PORT)"

local: ## run without Docker (uv + Node 22): installs then starts the 3 services
	@COMPANY=$(COMPANY) ./scripts/setup.sh --local

dev: ## run locally, already installed (live reload)
	@./scripts/dev.sh

chat: ## talk to the agent in the terminal
	@if $(COMPOSE) ps --status running ai 2>/dev/null | grep -q ai; then $(COMPOSE) exec ai python -m app.cli; else cd apps/ai && uv run python -m app.cli; fi

calls: ## replay the test calls of SCENARIOS.md and check the ERP (resets the ERP! ARGS="T3 T6" or "--repeat 3")
	@python3 evals/run_calls.py $(ARGS)

calls-test: ## check the test-call checks themselves, both ways (no model, no credits; ERP running)
	@python3 evals/test_checks.py

jury: ## replay the jury-style hard calls of evals/jury_calls.json (resets the ERP! ARGS="J1 J5" or "-v")
	@python3 evals/run_jury.py $(ARGS)

types: ## regenerate frontend types from the Python OpenAPI schemas (services running; needs Node + pnpm)
	@./scripts/gen-types.sh

test: ## AI service tests (offline: adapters, tools, mock); needs uv
	cd apps/ai && uv run pytest -q

check: ## frontend typecheck + design guards (needs Node + pnpm)
	pnpm --filter @kit/web typecheck && ./scripts/check-no-native-controls.sh

.PHONY: help setup up down restart logs ps reset rebuild clean offline local dev chat types test check

chaos: ## « Cassez le matin »: write a product off and empty it on today's trucks (PRODUCT=prd_0011 WHY="…" ARGS="--short 30"); make reset undoes it
	@python3 evals/break_morning.py $(PRODUCT) --why "$(or $(WHY),Lot écarté cette nuit par précaution)" $(ARGS)

chaos-check: ## « Cassez le matin »: stage the five sabotage cards of DEMO.md § 9 and check the board, no model (resets the ERP!)
	@python3 evals/break_morning.py --cards
