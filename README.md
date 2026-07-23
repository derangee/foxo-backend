# FOXO Inventory Service

A production-minded backend service for managing products and their stock
movements (restocks, sales, and adjustments) with transactional integrity.

> **Status:** Under active development. This README grows with the project; a
> full reference is delivered in the final phase.

---

## Tech Stack

| Concern            | Choice                                  |
| ------------------ | --------------------------------------- |
| Language           | Python 3.11+                            |
| Web framework      | FastAPI                                 |
| ORM                | SQLAlchemy 2.0 (async)                   |
| Database           | PostgreSQL (asyncpg driver)             |
| Migrations         | Alembic                                 |
| Configuration      | pydantic-settings                       |
| Lint / Format      | Ruff / Black                            |
| Tests              | pytest, pytest-asyncio, httpx           |

## Project Structure

```
foxo-backend/
├── app/
│   ├── main.py              # App factory + entrypoint
│   ├── core/                # Config, logging, cross-cutting concerns
│   ├── db/                  # Engine, session, declarative base
│   ├── api/v1/              # Versioned routers and endpoints
│   └── schemas/             # Pydantic DTOs / response envelopes
├── tests/                   # Unit and integration tests
├── docker-compose.yml       # Local PostgreSQL
├── pyproject.toml           # Dependencies + tooling config
└── .env.example             # Reference environment configuration
```

## Getting Started

### 1. Prerequisites
- Python 3.11+
- Docker (for local PostgreSQL) or an existing PostgreSQL instance

### 2. Install
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. Configure
```bash
cp .env.example .env             # then edit as needed
```

### 4. Start the database
```bash
docker compose up -d
```

### 5. Run the API
```bash
uvicorn app.main:app --reload
```

- Interactive docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

## Development

```bash
ruff check .        # lint
black .             # format
pytest              # run tests
```

## Environment Variables

See [.env.example](.env.example) for the full, documented list.

---

## Roadmap (delivered incrementally)

- [x] Phase 1 — Project setup, configuration, health endpoint
- [ ] Phase 2 — Product & StockMovement models + migrations
- [ ] Phase 3 — Product CRUD APIs
- [ ] Phase 4 — Transactional stock movements
- [ ] Phase 5 — Movement history
- [ ] Phase 6 — Bonus inventory features
- [ ] Phase 7 — Test coverage
- [ ] Phase 8 — Polish & refactor
- [ ] Phase 9 — Full documentation & design reflection
