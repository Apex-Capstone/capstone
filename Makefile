PYTHONPATH_BACKEND_SRC := $(subst \,/,$(abspath backend/src))
.PHONY: backend backend-dev backend-install frontend frontend-dev frontend-install db-migrate

backend: backend-install backend-dev

ifeq ($(OS),Windows_NT)
backend-install:
	@powershell -NoProfile -Command "cd 'backend'; $$env:PYTHONPATH = '$(PYTHONPATH_BACKEND_SRC)'; poetry install"

backend-dev:
	@powershell -NoProfile -Command "cd 'backend'; $$env:PYTHONPATH = '$(PYTHONPATH_BACKEND_SRC)'; poetry run uvicorn src.app:app --reload"

db-migrate:
	@powershell -NoProfile -Command "cd 'backend'; $$env:PYTHONPATH = '$(PYTHONPATH_BACKEND_SRC)'; poetry run alembic upgrade head"
else
backend-install:
	@cd backend && PYTHONPATH=$(PYTHONPATH_BACKEND_SRC) poetry install

backend-dev:
	@cd backend && PYTHONPATH=$(PYTHONPATH_BACKEND_SRC) poetry run uvicorn src.app:app --reload

db-migrate:
	@cd backend && PYTHONPATH=$(PYTHONPATH_BACKEND_SRC) poetry run alembic upgrade head
endif

frontend: frontend-install frontend-dev

frontend-install:
	@cd frontend && npm install

frontend-dev:
	@cd frontend && npm run dev
