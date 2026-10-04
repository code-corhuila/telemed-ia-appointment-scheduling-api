# telemed-ia-appointment-scheduling

Appointment Scheduling API of **TeleMed IA**.  
Part of team `telemed-ia`, Grupo 2.

## What this repo is

The service that implements the Appointment Scheduling bounded context: scheduling, cancellation, rescheduling, status changes, and queries.

It owns **availability** and **appointment lifecycle**. It does not own the pre-consultation summary, the clinical information, or the PDF documents. Those belong to other domains.

- **Language**: Python 3.12.
- **Web framework**: FastAPI.
- **Database**: PostgreSQL 16, schema `appointment_scheduling`, inside the single instance owned by `telemed-ia-infra-postgres`.
- **Architecture**: Hexagonal (ports & adapters).

## Endpoints

Public (through the API Gateway, prefixed `/api/v1/appointments`):

| Method | Path | Role |
|---|---|---|
| POST | `/` | PATIENT, PROFESSIONAL |
| GET | `/patient/{id}` | PATIENT, PROFESSIONAL, ADMIN |
| GET | `/professional/{id}` | PROFESSIONAL, ADMIN |
| PATCH | `/{id}/cancel` | PATIENT, PROFESSIONAL, ADMIN |
| PATCH | `/{id}/reschedule` | PATIENT, PROFESSIONAL, ADMIN |
| PATCH | `/{id}/status` | PROFESSIONAL, ADMIN |
| GET | `/health` | public |

## Structure

```text
src/appointment/
├── domain/                  # entities, value objects, invariants
│   ├── model/
│   └── exception.py
├── application/             # use cases and ports
│   ├── dto/
│   ├── events/
│   ├── ports/
│   │   ├── inbound/
│   │   └── outbound/
│   └── usecase/
├── adapter/
│   ├── inbound/http/        # FastAPI routers, middlewares, auth, errors
│   └── outbound/
│       ├── persistence/     # asyncpg repositories
│       └── messaging/       # no-op event publisher
└── config/
    ├── database.py          # asyncpg pool with explicit limits
    └── settings.py          # pydantic-settings
apps/api/                    # entry point: python -m apps.api
tests/                       # unit, HTTP and (with TEST_DATABASE_URL) integration
deploy/                      # Dockerfile and compose.yml
```

The domain imports nothing outside the Python standard library. Use cases depend only on Protocols (ports), never on infrastructure.

## Local development

### Prerequisites

- Python 3.12 (use `py -3.12 -m venv .venv` on Windows if the `python` alias points to the Microsoft Store stub).
- Docker Desktop.
- Git Bash on Windows.

### Setup

```bash
python -m venv .venv
source .venv/Scripts/activate     # Windows Git Bash
# source .venv/bin/activate       # Linux / macOS
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

### Tests

```bash
ruff check src/ tests/
pytest -q
```

The HTTP tests use `TestClient` with a fake in-memory container. They do not need a database.

### Run the service

Requires a running PostgreSQL with the `appointment_scheduling` schema applied (see `telemed-ia-appointment-scheduling-db`).

```bash
cp .env.example .env
# edit .env: DB_PASSWORD, JWT_PUBLIC_KEY
python -m apps.api
```

The service listens on `:8080`.

### Docker

```bash
docker network create platform
docker compose -f deploy/compose.yml up -d --build
```

## Contract notes

### Listings are paginated
The OpenAPI contract (`07-api/contracts/openapi/appointment-service.yaml`) declares listings as plain arrays. The project norm (5.3.6) requires `{data, meta}` with `page` and `limit`. This service implements the norm. A follow-up issue will update the OpenAPI in `-docs` to match.

### Pre-consultation is not implemented here
The OpenAPI contract also lists `/preconsultation` endpoints. Those belong to `agent-service`, not to this service. They are intentionally absent here.

## Known limitations

- **Idempotency store is in-process.** The `Idempotency-Key` responses live in an in-memory dictionary. Horizontal scaling requires a shared store (Postgres table `idempotency_key`, following the `patient-management` pattern). Tracked as low-complexity debt.
- **Event publisher is a no-op.** Per ADR-011 the message broker (RabbitMQ) is still Proposed. The `NoOpEventPublisher` logs each event and does nothing else. Replacing it with a RabbitMQ adapter requires no changes to use cases.
- **Slot computation is not implemented yet.** The `PostgresAvailabilityRepository` is wired but not consumed by any endpoint. A future endpoint will compute bookable slots from recurring availability plus existing appointments.
- **No integration tests against a real database in CI.** They exist locally but require `TEST_DATABASE_URL`. Adding them to CI is a follow-up.

## Repository rules

- JWT is validated in the service itself (norm 5.3.7).
- Error envelope on every failure (norm 5.3.5).
- `X-Correlation-Id` reused or generated and echoed (norm 5.3.9).
- Creation is idempotent (norm 5.3.8).
- Listings are paginated (norm 5.3.6).
- Explicit server and database limits (norm 5.3.10).
- The schema lives only in `telemed-ia-appointment-scheduling-db`.
- The three permanent branches (`develop`, `qa`, `main`) never receive a direct commit.
- Promotion is by re-application (`git cherry-pick -x`).

## Related documentation

- `telemed-ia-docs/02-domain/domain-map.md`
- `telemed-ia-docs/09-microservices/services/06-appointment-service/`
- `telemed-ia-docs/05-architecture/decisions/records/ADR-009-appointment-availability-ownership.md`
- `telemed-ia-docs/07-api/contracts/openapi/appointment-service.yaml`
- Anexo C of the repo norm.