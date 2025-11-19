# MedLLM Backend – Database Connection Guide

This guide explains how to configure and connect the MedLLM backend to a PostgreSQL database, load environment variables, and automatically create all tables using SQLAlchemy.

## 1. Requirements

- Python 3.11+
- Poetry
- PostgreSQL (local) or Supabase PostgreSQL
- Backend project files

## 2. Environment Setup (.env)

The project already includes a `.env.example` file.  
Copy it to `.env`: `cp .env.example .env`

Then update the `DATABASE_URL` field inside `.env`
Find DB URL by copying it from the `Connection` tab in Supabase

## 3. Backend Database Initialization

The backend loads the environment variables, reads `DATABASE_URL`, and initializes SQLAlchemy:

```
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

All ORM models inherit from `Base`.

## 4. Creating Tables

### Option A – Reset and Seed

```
poetry run python -m src.scripts.reset_and_seed
```

Drops tables, recreates schema, and seeds data.

### Option B – Auto Creation on App Start

Running:

```
poetry run uvicorn app:app --reload
```

Automatically creates all tables if missing.

## 5. Testing the Database Connection

```
poetry run python - << 'EOF'
from db.base import engine
print(engine.connect())
EOF
```

A successful connection prints a connection object.

## 6. Common Errors

### “Could not translate host name”
Incorrect hostname or network issue.

### “password authentication failed”
Incorrect database password.

### “no such table”
Tables were not created. Run:

```
poetry run python -m src.scripts.reset_and_seed
```

### “ModuleNotFoundError”
Run scripts with PYTHONPATH:

```
PYTHONPATH="$PWD/src" poetry run python -m src.scripts.seed
```

## 7. Commands Summary

| Action | Command |
|--------|---------|
| Start backend | `poetry run uvicorn app:app --reload` |
| Reset DB + Seed | `poetry run python -m src.scripts.reset_and_seed` |
| Seed only | `poetry run python -m src.scripts.seed` |
| Test DB connection | See above |
| View DB | pgAdmin or Supabase dashboard |

## 8. Summary

Once `DATABASE_URL` is properly configured, the backend can connect to PostgreSQL, create all required tables, and run seed scripts. This setup works with both local and Supabase databases.
