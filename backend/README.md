# Medical Case Simulation Backend

FastAPI backend for AI-powered medical case simulations with SPIKES protocol.

## Architecture

```
backend/
├── src/
│   ├── app.py                    # FastAPI instance & router mounting
│   ├── config/                   # Settings & logging
│   ├── core/                     # Security, errors, deps, events
│   ├── db/                       # Database setup & migrations
│   ├── domain/                   # Entities (models) & schemas
│   ├── repositories/             # Data access layer
│   ├── adapters/                 # External service adapters
│   │   ├── llm/                  # LLM adapters (OpenAI, Gemini)
│   │   ├── asr/                  # Speech-to-text (Whisper)
│   │   ├── tts/                  # Text-to-speech
│   │   ├── nlu/                  # Natural language understanding
│   │   └── storage/              # File storage (S3)
│   ├── services/                 # Business logic
│   ├── controllers/              # API routes/controllers
│   └── tests/                    # Test suite
├── pyproject.toml                # Dependencies
└── README.md

```

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL (or SQLite for development)
- Poetry for dependency management

### Installation

1. Install dependencies:
```bash
cd backend
poetry install
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Initialize database:
```bash
poetry run alembic upgrade head
```

4. Run the application:
```bash
poetry run python src/app.py
```

Or with uvicorn directly:
```bash
poetry run uvicorn src.app:app --reload --host 0.0.0.0 --port 8000
```

### Seeding Dev Data

Create admin accounts plus several trainee users with example cases:

- Admin:           admin@example.com / admin123
- Additional Admin: admin2@example.com / admin123
- Trainees:        alice.trainee@example.com / changeme, etc.

Run:

    poetry run seed

Re-seed from scratch (dev only):

    poetry run seed --reset

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/v1/docs
- ReDoc: http://localhost:8000/v1/redoc

## Key Features

### SPIKES Protocol
The dialogue service implements the SPIKES protocol for breaking bad news:
- **S**etting up the interview
- **P**erception - assess patient's perception
- **I**nvitation - obtain invitation to share info
- **K**nowledge - give knowledge and information
- **E**mpathy - address emotions with empathy
- **S**ummary - strategy and summary

### AI Adapters
- **LLM**: OpenAI GPT-4 or Google Gemini for patient simulation
- **ASR**: Whisper for speech-to-text
- **TTS**: Generic TTS adapter (extensible)
- **NLU**: Rule-based NLU for empathy detection and question classification
- **Storage**: S3 for audio file storage

### Scoring & Feedback
Automated scoring based on:
- Empathy level
- Question types (open vs closed)
- SPIKES protocol completion
- Communication effectiveness

## Testing

Run tests:
```bash
$env:PYTHONPATH = "$PWD\src"
poetry run pytest
```

With coverage:
```bash
poetry run pytest --cov=src --cov-report=html
```

## Development

### Database Migrations

Create a new migration:
```bash
poetry run alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
poetry run alembic upgrade head
```

### Code Quality

Format code:
```bash
poetry run black src/
```

Lint code:
```bash
poetry run ruff src/
```

Type check:
```bash
poetry run mypy src/
```

## Deployment

1. Set production environment variables
2. Use production database (PostgreSQL)
3. Run with production ASGI server:
```bash
gunicorn src.app:app -w 4 -k uvicorn.workers.UvicornWorker
```

## License

[Your License Here]

