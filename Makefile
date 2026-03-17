PYTHONPATH_BACKEND_SRC := $(subst \,/,$(abspath backend/src))
.PHONY: backend backend-dev backend-install frontend frontend-dev frontend-install seed

backend: backend-install backend-dev

backend-install:
	@powershell -NoProfile -Command "cd 'backend'; $$env:PYTHONPATH = '$(PYTHONPATH_BACKEND_SRC)'; poetry install"

backend-dev:
	@powershell -NoProfile -Command "cd 'backend'; $$env:PYTHONPATH = '$(PYTHONPATH_BACKEND_SRC)'; poetry run uvicorn src.app:app --reload"

frontend: frontend-install frontend-dev

frontend-install:
	@cd frontend && npm install

frontend-dev:
	@cd frontend && npm run dev

seed:
	@powershell -NoProfile -Command "cd 'backend'; $$env:PYTHONPATH = '$(PYTHONPATH_BACKEND_SRC)'; poetry run python -m src.scripts.reset_and_seed"

