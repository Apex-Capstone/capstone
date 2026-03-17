# APEX Backend – Database Connection Guide

This guide explains how to configure and connect the APEX backend to a PostgreSQL database, load environment variables, and automatically create all tables using SQLAlchemy.  
This version includes additional details specifically for **Supabase-hosted PostgreSQL**, the recommended database for collaborative development.

---

## 1. Requirements

- Python 3.11+
- Poetry
- PostgreSQL (local) *or* Supabase PostgreSQL
- Backend project directory structure (`src/db`, `src/domain`, etc.)

---

## 2. Environment Setup (.env)

The project already includes a `.env.example` file.

Copy it to `.env`:

```
cp .env.example .env
```

Then update the `DATABASE_URL` field inside `.env`.

### 📌 Where to find your Supabase Database URL

1. Go to **Supabase Dashboard**
2. Select your project
3. Navigate to **Connect**
4. Change `Method` to **Session Pooler**
5. Copy the Postgres connection string
6. Change password in URL to actual Database password

Example:

```
DATABASE_URL=postgresql://postgres:MyPassword@db.flbzefzyxgxpmorwlcxp.supabase.co:5432/postgres
```

### Notes About Supabase

- Supabase requires SSL by default. SQLAlchemy handles this automatically for standard Postgres URLs.
- Your teammates can all use the same Supabase database without needing local Postgres installed.
- The database is hosted in the cloud → your API must have internet access.
- Supabase enforces strong passwords — avoid weak passwords or connection will fail.
- You can view and edit tables from the **Table Editor** in Supabase.

---

## 3. Backend Database Initialization

The backend loads environment variables and initializes SQLAlchemy:

```
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

All ORM models (`User`, `Case`, `Session`, `Turn`, etc.) inherit from `Base`.  
The tables are created automatically when `Base.metadata.create_all(engine)` runs.

---

## 4. Creating Tables

You have two options:

### **Option A – Reset and Seed**

This fully wipes and rebuilds your schema:

```
poetry run python -m src.scripts.reset_and_seed
```

This will:

- Drop existing tables  
- Recreate schema  
- Insert Admin and Trainee users  
- Insert all default patient cases  

Perfect for development or teammates pulling the project for the first time.

---

### **Option B – Auto Creation on App Start**

Running the backend normally will auto-create tables if they don’t exist:

```
poetry run uvicorn app:app --reload
```

This triggers:

```
Base.metadata.create_all(engine)
```

Useful when deploying or running in a fresh Supabase database.

---

## 5. Testing the Database Connection

Run this:

```
poetry run python - << 'EOF'
from db.base import engine
print(engine.connect())
EOF
```

If successful, you’ll see a connection object printed.

If not, check the following:
- Wrong password
- Wrong host
- Supabase project paused
- Internet connection blocked

---

## 6. Common Errors (Supabase-Specific Included)

### ❌ “Could not translate host name”
- Your Supabase hostname is misspelled
- Your computer is offline or DNS is blocked

### ❌ “password authentication failed”
- Wrong database password
- Password contains special characters → must be URL-encoded

### ❌ “no such table”
- Tables were never created  
Fix:

```
poetry run python -m src.scripts.reset_and_seed
```

### ❌ “ModuleNotFoundError”
Always run scripts with the correct path:

```
PYTHONPATH="$PWD/src" poetry run python -m src.scripts.seed
```

---

## 7. Commands Summary

| Action | Command |
|--------|---------|
| Start backend | `poetry run uvicorn app:app --reload` |
| Reset DB + Seed | `poetry run python -m src.scripts.reset_and_seed` |
| Seed only | `poetry run python -m src.scripts.seed` |
| Test connection | See section above |
| View tables | Supabase Table Editor |

---

## 8. Supabase-Specific Notes

- Supabase automatically assigns your database a unique hostname.
- Connection remains active even if hosted locally — teammates anywhere can connect.
- Supabase logs every query → useful for debugging.
- Postgres extensions (e.g., `pgcrypto`) can be enabled from the Dashboard.
- Your project may sleep if you’re on the free tier — wake it up from Dashboard if connection fails.

---

## 9. Summary

Once `DATABASE_URL` is correctly set in `.env`, the backend can:

- Connect to Supabase PostgreSQL  
- Auto-create all required tables  
- Run seeding scripts  
- Work for every teammate without needing local Postgres  

This setup makes the APEX backend fully cloud-ready and team-friendly.

