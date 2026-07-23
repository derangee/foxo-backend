# FOXO Inventory Service

A production-minded backend for managing products and their stock movements
(restocks, sales, and adjustments) with strict transactional integrity and a
fully auditable movement ledger.

Built with **FastAPI**, **async SQLAlchemy 2.0**, and **PostgreSQL**.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Folder Structure](#folder-structure)
- [Installation](#installation)
- [Environment Variables](#environment-variables)
- [Running the Project](#running-the-project)
- [Running Tests](#running-tests)
- [Database Migrations](#database-migrations)
- [API Endpoints](#api-endpoints)
- [Business Rules](#business-rules)
- [Transaction Strategy](#transaction-strategy)
- [Validation](#validation)
- [Error Handling](#error-handling)
- [Design Decisions](#design-decisions)
- [Tradeoffs](#tradeoffs)
- [Future Improvements](#future-improvements)
- [System Design Reflection](#system-design-reflection)

---

## Project Overview

The service maintains a catalog of **products**, each with an authoritative
on-hand `quantity`. Stock never changes arbitrarily: every change is applied as
an immutable **stock movement** (`RESTOCK`, `SALE`, or `ADJUSTMENT`) inside a
single database transaction. This gives two guarantees:

1. **Correctness under concurrency** — simultaneous operations on the same
   product cannot oversell or lose updates.
2. **Auditability** — the movement ledger is append-only and reconciles exactly
   with on-hand stock (`SUM(quantity_change) == quantity`).

## Architecture

A conventional layered (clean) architecture with a single, one-directional
dependency flow. Each layer has one responsibility and is independently testable.

```mermaid
flowchart TD
    Client -->|HTTP| Endpoint
    Endpoint -->|DTOs| Service
    Service -->|domain calls| Repository
    Repository -->|ORM| DB[(PostgreSQL)]
    Service -.raises.-> Exc[Domain exceptions]
    Exc -.handled by.-> Handlers[Central error handlers]
    Handlers -.consistent envelope.-> Client
```

| Layer | Responsibility | Key rule |
| --- | --- | --- |
| **API / Endpoints** | HTTP ⇄ DTO translation | Thin; no business logic |
| **Schemas (DTOs)** | Request/response contracts + validation | No ORM types leak out |
| **Services** | Business rules **and transaction boundaries** | Owns commit/rollback |
| **Repositories** | Data access | Never commits |
| **Models** | ORM mapping + DB constraints | Constraints as a backstop |

**Request lifecycle:** middleware assigns a correlation id → endpoint validates
the DTO → service opens a logical transaction, applies rules, commits → response
is wrapped in the standard envelope. Any raised domain exception is converted by
the central handlers into a consistent error body with the right HTTP status.

## Technology Stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.11+ |
| Web framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL (asyncpg driver) |
| Migrations | Alembic |
| Configuration | pydantic-settings |
| Lint / Format | Ruff / Black |
| Tests | pytest, pytest-asyncio, httpx |
| Packaging | Docker, docker-compose |

## Folder Structure

```
foxo-backend/
├── app/
│   ├── main.py                 # App factory, middleware, entrypoint
│   ├── core/
│   │   ├── config.py           # Typed settings (pydantic-settings)
│   │   ├── logging.py          # Central logging config
│   │   ├── middleware.py       # Request id + access logging
│   │   ├── exceptions.py       # Domain exception hierarchy
│   │   └── error_handlers.py   # Exception -> HTTP envelope
│   ├── db/
│   │   ├── base.py             # Declarative Base
│   │   └── session.py          # Async engine + session dependency
│   ├── models/                 # ORM models, enums, mixins
│   ├── schemas/                # Pydantic DTOs + response envelopes
│   ├── repositories/           # Data-access layer
│   ├── services/               # Business logic + transactions
│   └── api/
│       ├── deps.py             # Dependency wiring
│       └── v1/
│           ├── router.py       # Aggregated v1 router
│           └── endpoints/      # health, products, stock_movements
├── alembic/                    # Migration environment + versions
├── tests/
│   ├── unit/                   # Service + schema tests
│   └── integration/            # HTTP-level tests
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── pyproject.toml
└── .env.example
```

## Installation

**Prerequisites:** Python 3.11+, and either Docker (for PostgreSQL) or an
existing PostgreSQL instance.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"            # or: make install
cp .env.example .env               # then edit as needed
```

## Environment Variables

Configuration is loaded from the environment (and an optional `.env`). See
[.env.example](.env.example) for the documented reference.

| Variable | Default | Description |
| --- | --- | --- |
| `APP_NAME` | `FOXO Inventory Service` | Display name |
| `APP_ENV` | `development` | `development` / `production` |
| `DEBUG` | `false` | Debug flag |
| `API_V1_PREFIX` | `/api/v1` | API route prefix |
| `DATABASE_URL` | `postgresql+asyncpg://foxo:foxo@localhost:5432/foxo_inventory` | Async DB URL |
| `DB_ECHO` | `false` | Log SQL statements |
| `DB_POOL_SIZE` | `5` | Connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Pool overflow |
| `LOG_LEVEL` | `INFO` | Root log level |

## Running the Project

### Option A — Full stack with Docker (recommended)

```bash
docker compose up --build          # or: make up
```

This starts PostgreSQL and the API. The API container **runs migrations
automatically** on startup, then serves on `http://localhost:8000`.

### Option B — Locally, with Dockerized PostgreSQL

```bash
docker compose up -d db            # start only the database
alembic upgrade head               # apply migrations  (make migrate)
uvicorn app.main:app --reload      # run the API       (make run)
```

- Interactive docs (Swagger UI): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health: http://localhost:8000/api/v1/health

## Running Tests

```bash
pytest                             # or: make test
```

Tests run against an isolated in-memory SQLite database (one fresh schema per
test), covering the service layer (unit) and the full HTTP stack (integration):
business rules, negative-stock rejection, transaction/atomicity behavior, and
movement history.

> **Note on concurrency tests:** `SELECT ... FOR UPDATE` is a no-op on SQLite, so
> the suite validates the transactional *logic* and constraints but not the
> pessimistic lock itself. To exercise real row locking, point the tests at
> PostgreSQL and drive two concurrent SALE transactions against the same product;
> the second should block until the first commits, and the non-negative check
> constraint guarantees no oversell.

## Database Migrations

```bash
alembic upgrade head               # apply all migrations
alembic downgrade -1               # revert the last migration
alembic revision -m "message"      # create a new (empty) revision
```

The migration environment reads `DATABASE_URL` from application settings (single
source of truth) and targets `Base.metadata`.

## API Endpoints

Base path: `/api/v1`. All responses use a consistent envelope
(`{ "success", "message", "data" }`); errors use `{ "success", "message", "error" }`.

| Method | Path | Description | Success |
| --- | --- | --- | --- |
| GET | `/health` | Liveness + DB connectivity | 200 |
| POST | `/products` | Create a product (starts at 0 stock) | 201 |
| GET | `/products` | List products (paginated) | 200 |
| GET | `/products/{id}` | Get a product | 200 |
| PATCH | `/products/{id}` | Update metadata (optimistic locking) | 200 |
| DELETE | `/products/{id}` | Delete (only if no movement history) | 204 |
| POST | `/products/{id}/activate` | Activate | 200 |
| POST | `/products/{id}/deactivate` | Deactivate | 200 |
| GET | `/products/low-stock` | Products at/below a threshold | 200 |
| POST | `/products/{id}/restock` | Increase stock | 201 |
| POST | `/products/{id}/sale` | Decrease stock (rejects oversell) | 201 |
| POST | `/products/{id}/adjust` | Signed correction (reason required) | 201 |
| GET | `/products/{id}/movements` | Movement history (paginated, filterable) | 200 |

### Examples

Create a product:

```bash
curl -X POST http://localhost:8000/api/v1/products \
  -H "Content-Type: application/json" \
  -d '{"sku": "WIDGET-001", "name": "Standard Widget", "price": "19.99"}'
```

```json
{
  "success": true,
  "message": "Product created",
  "data": {
    "id": 1, "sku": "WIDGET-001", "name": "Standard Widget",
    "description": null, "price": "19.99", "quantity": 0,
    "is_active": true, "version": 1,
    "created_at": "2026-01-01T10:00:00Z", "updated_at": "2026-01-01T10:00:00Z"
  }
}
```

Restock, then sell:

```bash
curl -X POST http://localhost:8000/api/v1/products/1/restock \
  -H "Content-Type: application/json" -d '{"quantity": 100}'

curl -X POST http://localhost:8000/api/v1/products/1/sale \
  -H "Content-Type: application/json" -d '{"quantity": 30}'
```

Overselling is rejected atomically:

```json
{
  "success": false,
  "message": "Insufficient stock for product 1: requested 1000, available 70.",
  "error": { "code": "insufficient_stock", "details": null }
}
```

Optimistic locking on update (send the version you last read):

```bash
curl -X PATCH http://localhost:8000/api/v1/products/1 \
  -H "Content-Type: application/json" \
  -d '{"price": "24.99", "expected_version": 1}'
```

## Business Rules

- A product is **created with zero stock**; stock changes only via movements.
- **RESTOCK** increases stock; **SALE** decreases it; **ADJUSTMENT** applies a
  signed correction and **requires a reason**.
- **Negative inventory is rejected.** A sale or downward adjustment that would
  drive stock below zero fails and changes nothing.
- The **quantity update and the movement record are written in one transaction** —
  both succeed or both roll back.
- **Movements are immutable** — there is no update or delete path for them.
- A product with movement history **cannot be deleted**; deactivate it instead.
- Product metadata updates use **optimistic locking** via a `version` counter.

## Transaction Strategy

- **One session per request.** The `get_session` dependency yields a request-scoped
  async session. It deliberately does **not** commit — services own transaction
  boundaries, so a single unit of work is explicit and testable.
- **Atomic movements.** `_apply_movement` locks the product row, computes the new
  quantity, writes the movement, and commits — all in one transaction.
- **Pessimistic locking for stock.** Stock movements take a row-level lock
  (`SELECT ... FOR UPDATE`) on the product, serializing concurrent movements so the
  read-modify-write of `quantity` cannot lose updates or oversell.
- **Optimistic locking for metadata.** Product edits use SQLAlchemy's
  `version_id_col`; a stale write is rejected with `409 version_conflict`.
- **Defense in depth.** Database `CHECK (quantity >= 0)` is the final backstop: even
  a movement that somehow raced past the in-memory check is rejected by the
  constraint, and the resulting integrity error is mapped back to a clean `409`.

## Validation

Validation happens at the DTO boundary with Pydantic, before any business logic:

- **SKU** — 1–64 chars, pattern `^[A-Za-z0-9._-]+$` (no spaces).
- **Price** — non-negative `Decimal`, max 12 digits, 2 decimal places (money is
  never a float).
- **Quantities** — restock/sale magnitudes must be `> 0`; adjustments must be
  non-zero and carry a reason.
- **Pagination** — `page >= 1`, `1 <= size <= 100`.

Failed validation returns `422` with a list of field-level messages.

## Error Handling

All errors funnel through central handlers and share one response shape. Domain
exceptions carry an HTTP status and a stable machine-readable code:

| Code | HTTP | Meaning |
| --- | --- | --- |
| `validation_error` | 422 | Request body/params failed validation |
| `product_not_found` | 404 | No product with that id |
| `duplicate_sku` | 409 | SKU already exists |
| `insufficient_stock` | 409 | Movement would drive stock negative |
| `version_conflict` | 409 | Optimistic-lock version mismatch |
| `product_has_movements` | 409 | Delete blocked; deactivate instead |
| `internal_error` | 500 | Unexpected error (logged with request id) |

## Design Decisions

- **Denormalized `quantity` on the product**, with movements as the ledger. Reads
  are O(1) and the ledger reconciles the balance (`SUM(quantity_change)`). The
  alternative — summing movements on every read — does not scale.
- **Signed `quantity_change` + `resulting_quantity`** on each movement. One column
  captures direction and magnitude; storing the resulting balance makes the ledger
  self-verifying and easy to audit.
- **Stock is not mutable through CRUD.** Create starts at 0 and update touches only
  metadata, so the ledger remains the single source of truth for inventory levels.
- **Services own transactions, repositories never commit.** This keeps units of
  work explicit and makes both layers easy to test in isolation.
- **Constraints in the database, not just the app.** Non-negative stock/price, a
  non-zero movement check, and `ON DELETE RESTRICT` protect data even if the
  service layer is bypassed.
- **Pessimistic vs optimistic locking by contention.** Stock movements are a hot,
  contended path → row locks. Metadata edits rarely conflict → cheap version checks.

## Tradeoffs

- **Pessimistic locks add contention.** Under extreme write load on a single hot
  product, `FOR UPDATE` serializes writers. Acceptable here for correctness; a
  lock-free `UPDATE ... WHERE quantity >= :q` is a possible optimization (see
  reflection).
- **Denormalized quantity can drift in theory.** Mitigated by writing it only
  through the transactional movement path and by the reconcilable ledger.
- **SQLite in tests** trades fidelity (no real row locking) for fast, isolated
  runs. Concurrency is best validated against PostgreSQL.
- **`BaseHTTPMiddleware` access logging** is simple but not the lowest-overhead
  option; a pure ASGI middleware would shave microseconds at high throughput.

## Future Improvements

- Authentication/authorization (API keys or OAuth2) and per-actor audit fields.
- Idempotency keys on movement endpoints to make retries safe.
- A dedicated `Warehouse`/`Inventory` model for multi-location stock (below).
- Structured JSON logging and metrics/tracing (OpenTelemetry).
- A CI pipeline running lint + tests on every push.
- Bulk operations and cursor-based pagination for very large ledgers.

## System Design Reflection

### 1. Two warehouse terminals submit a SALE at nearly the same time — what could go wrong, and how do we solve it?

**The hazard: a lost update (race condition).** Selling is a read-modify-write:
read `quantity`, subtract, write it back, and record a movement. If two terminals
run this concurrently without coordination, both read the same starting value
(say `10`), each computes its own new value (`10 - 6 = 4` and `10 - 7 = 3`), and
the second write silently overwrites the first. One sale is effectively lost,
stock is wrong, and the ledger no longer reconciles — in the worst case we oversell
into negative inventory.

**How this service solves it (layered):**

1. **Pessimistic row lock (primary).** Each movement locks the product row with
   `SELECT ... FOR UPDATE`. The second transaction blocks until the first commits,
   then reads the *fresh* quantity. Writers are serialized, so no update is lost.
   This is the right default because stock decrement is a hot, highly contended
   path where conflicts are expected, and blocking briefly is cheaper than
   repeatedly retrying.

2. **Non-negative CHECK constraint (backstop).** `CHECK (quantity >= 0)` guarantees
   the database can never hold negative stock, even if application logic is bypassed
   or a race slips through. A violating write raises an integrity error that the
   service maps to a clean `409 insufficient_stock`.

3. **One atomic transaction.** The quantity update and the movement insert commit
   together, so we never end up with a decremented balance and no audit row (or vice
   versa).

**Alternatives and when they fit:**

- **Optimistic locking (version column).** Instead of blocking, let both proceed
  and reject the second commit if the version changed, then retry. Excellent under
  *low* contention (fewer locks held), but under high contention it degrades into
  retry storms — which is why we reserve it for product metadata, not stock.
- **Atomic conditional update (lock-free).**
  `UPDATE products SET quantity = quantity - :q WHERE id = :id AND quantity >= :q`,
  then check the affected row count. The decrement happens in a single statement
  with no read-modify-write window; zero rows affected means insufficient stock.
  This is the most scalable option for extreme throughput and is the natural next
  optimization if a single product becomes a hotspot.
- **Serializable isolation.** Correct, but it pushes the cost into transaction
  aborts/retries and is heavier than a targeted row lock for this specific
  operation.

**Summary:** we serialize the contended write with a row lock, guarantee the
invariant at the database with a check constraint, and keep the update atomic —
correctness first, with a clear, documented path to a lock-free decrement if
write throughput on a single product ever demands it.

### 2. How would the architecture evolve from one warehouse to fifty?

Today `quantity` lives on the product, implying a single stockroom. Scaling to many
warehouses means **stock becomes a property of (product, warehouse), not of the
product alone.**

**Data model.**

- Introduce a **`Warehouse`** entity (id, code, name, location).
- Move stock into an **`inventory`** (stock-level) table keyed by a **composite
  primary key `(product_id, warehouse_id)`**, holding `quantity` and its own
  `version` for optimistic locking. `Product` keeps only catalog attributes.
- **Scope movements per warehouse:** add `warehouse_id` (FK) to `stock_movement`.
  A stock transfer between warehouses becomes two movements — an outbound at the
  source and an inbound at the destination — recorded in one transaction (or a
  dedicated `TRANSFER` type linking the pair).

**Indexing.**

- `inventory (product_id, warehouse_id)` — the composite PK serves point lookups
  and "stock of product P at warehouse W".
- A secondary index on `inventory (warehouse_id, product_id)` for
  "everything in warehouse W", plus a partial index on low stock for alerting.
- `stock_movement (warehouse_id, product_id, created_at)` for per-warehouse,
  per-product history — the natural evolution of today's composite index.

**Concurrency.** The locking strategy is unchanged but now scoped to a single
`(product, warehouse)` row, which *reduces* contention: two warehouses selling the
same product no longer touch the same row at all.

**Scaling the reads/writes.**

- **Read replicas** for reporting and cross-warehouse availability queries; writes
  stay on the primary.
- **Partition** the movement ledger (by `warehouse_id` and/or time) so history stays
  fast as it grows into the billions of rows.
- **Cache** hot stock levels (e.g. Redis) with careful invalidation on movement
  commit, for read-heavy availability checks.
- Aggregate "total availability across all warehouses" via a query or a
  **materialized view**, refreshed on movement events.

**Toward microservices / event-driven.**

- Split along bounded contexts: a **Catalog** service (products) and an
  **Inventory** service (stock levels + movements) — they scale and deploy
  independently.
- On every committed movement, publish a **`StockMovementRecorded`** event using the
  **transactional outbox pattern** (write the event in the same transaction as the
  movement, relay it to a broker like Kafka), guaranteeing the ledger and the event
  stream never diverge.
- Downstream consumers build **CQRS read models** (per-warehouse dashboards, global
  availability, low-stock alerts) and trigger workflows (reordering, fulfillment)
  without coupling to the write path.
- Cross-warehouse totals become **eventually consistent** projections — a deliberate
  tradeoff: each warehouse stays strongly consistent for its own stock, while
  global views tolerate slight lag in exchange for scale.

**In short:** promote stock from a product attribute to a first-class
`(product, warehouse)` inventory record with composite keys and per-warehouse
movements; the transactional guarantees carry over unchanged (and contend less),
while replicas, partitioning, caching, and an outbox-backed event stream let the
system scale out to fifty warehouses and beyond.
