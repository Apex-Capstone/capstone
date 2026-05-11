# Running APEX with Docker

This guide covers the **optional** Docker workflow for the full stack (FastAPI backend + Vite/React frontend). It does **not** replace the existing Poetry + npm local setup in the repository root `README.md`.

**Render:** `backend/render_predeploy.sh`, `backend/README.md` deployment notes, and the Render dashboard configuration are unchanged. Validate Docker in staging before turning off Render.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- A **PostgreSQL** database reachable from the backend container — typically **Supabase** (same as production) with `DATABASE_URL` using `sslmode=require` where required
- Supabase project values: **JWT secret** (backend), **URL + anon key** (frontend build)

---

## Quick start (external database)

1. **Copy the environment template** at the repository root:

   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** and set at least:

   - `DATABASE_URL` — Supabase Postgres or other managed Postgres (not assumed to run inside Docker for production)
   - `SUPABASE_JWT_SECRET`
   - `OPENAI_API_KEY`, `GEMINI_API_KEY`
   - `CORS_ORIGINS` — include the origin where the SPA is served (e.g. `http://localhost:8080` for the compose frontend port mapping)
   - `PUBLIC_BASE_URL` — the URL browsers use to reach the API (e.g. `http://localhost:8000` when using default compose ports)
   - `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` — used **at frontend image build time** (see below)

3. **Build and run:**

   ```bash
   docker compose build
   docker compose up
   ```

4. **Verify the API:**

   ```bash
   curl http://localhost:8000/health
   ```

5. **Open the UI:** [http://localhost:8080](http://localhost:8080)

---

## Local PostgreSQL (optional)

For a **self-contained local database** only (not for production), use the overlay file. This starts **PostgreSQL 16** with user/password/database `apex` / `apex` / `apex` and a named volume for data. The backend’s `DATABASE_URL` is overridden to point at that service.

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up --build
```

- Postgres is exposed on the host at **port 5433** (mapped to 5432 in the container) to reduce clashes with an existing Postgres on 5432.
- You still need valid Supabase **Auth** configuration in `.env` if you exercise login flows (JWT verification uses `SUPABASE_JWT_SECRET`).

---

## Frontend `VITE_*` variables (build-time)

The frontend Docker image runs `npm run build` during **`docker compose build`**. Values such as `VITE_API_URL` and `VITE_SUPABASE_*` are **compiled into the static bundle**. Changing them requires **rebuilding** the frontend image (or passing new build args), not only restarting the container.

Compose passes these from your root `.env` into the frontend build `args` section in `docker-compose.yml`.

---

## Migrations (Alembic)

The backend container **entrypoint** runs `alembic upgrade head` before starting Uvicorn by default (similar in spirit to `backend/render_predeploy.sh` on Render).

- To **skip** migrations in the container (e.g. multiple replicas; run migrations once elsewhere): set `RUN_MIGRATIONS=0` in `.env`.
- For a **one-off migration** with compose:

  ```bash
  docker compose run --rm backend poetry run alembic upgrade head
  ```

---

## Volumes

- **`backend_storage`:** mounted at `/app/storage` for local media cache and default `LOCAL_STORAGE_PATH` / `AUDIO_CACHE_PATH` behavior. Ephemeral cache is fine for many deployments; assistant audio durability is expected via Supabase when configured.

---

## Troubleshooting

- **CORS errors:** ensure `CORS_ORIGINS` includes the exact browser origin (scheme + host + port), e.g. `http://localhost:8080`.
- **Broken assistant audio links:** set `PUBLIC_BASE_URL` to the public URL of the API.
- **WebSockets:** the default `nginx.conf` does not proxy `/v1/ws`; the browser connects to `VITE_API_URL` directly. Ensure that origin allows WebSockets and that proxies (if any) forward `Upgrade` / `Connection` headers.

---

## Render unchanged

Building these images does **not** modify Render services. Render continues to use its configured build/start commands and `backend/render_predeploy.sh` until you change hosting.
