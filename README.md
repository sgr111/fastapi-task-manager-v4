# FastAPI Task Manager v4

![CI](https://github.com/sgr111/fastapi-task-manager-v4/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue)
![License](https://img.shields.io/badge/license-MIT-green)

A production-grade REST API for task management built with FastAPI, PostgreSQL, JWT authentication, JSONB metadata, soft deletes, Change Data Capture (CDC) audit logs, and rate limiting.

---

## Features

| Feature | Details |
|---|---|
| **Pagination** | skip/limit with `has_more` field — silently clamps limit to MAX_PAGE_SIZE |
| **Soft Deletes** | `deleted_at` timestamp — data preserved, audit log retained after deletion |
| **JSONB Metadata** | Flexible per-task schema-less data stored in PostgreSQL JSONB column |
| **CDC Audit Logs** | Every CREATE, UPDATE, DELETE recorded with old/new values and `changed_by` |
| **JWT Auth** | Access tokens (30 min) + Refresh tokens (7 days) with unique JTI per token |
| **Rate Limiting** | Per-user slowapi limits — 30 writes/min, 100 reads/min, 30 auth/min |
| **Alembic Migrations** | Version-controlled schema — users, tasks (JSONB), audit_logs tables |
| **Async Throughout** | asyncpg + SQLAlchemy 2.0 async + httpx — non-blocking I/O at every layer |
| **GitHub Actions CI** | 29 unit tests run automatically on every push with PostgreSQL service |
| **bcrypt Hashing** | Passwords hashed with configurable rounds — never stored in plain text |
| **Password Validation** | Pydantic `field_validator` enforces uppercase + digit requirements |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 15 (production), SQLite (testing) |
| Migrations | Alembic |
| Auth | python-jose (JWT), bcrypt |
| Rate Limiting | slowapi |
| Testing | pytest, pytest-asyncio, httpx |
| Validation | Pydantic v2 |
| DB Driver | asyncpg (PostgreSQL), aiosqlite (SQLite) |

---

## Project Structure

```
fastapi_task_manager_v4/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── auth.py        # Register, login, refresh
│   │       │   └── tasks.py       # CRUD + audit log endpoints
│   │       ├── dependencies.py    # get_current_user
│   │       └── router.py
│   ├── core/
│   │   ├── config.py              # Settings from .env
│   │   ├── limiter.py             # Shared slowapi Limiter instance
│   │   └── security.py            # JWT + bcrypt utilities
│   ├── db/
│   │   └── session.py             # Async engine + get_db dependency
│   ├── models/
│   │   ├── task.py                # Task + AuditLog ORM models
│   │   └── user.py                # User ORM model
│   ├── schemas/
│   │   ├── task.py                # Pydantic schemas for tasks
│   │   └── user.py                # Pydantic schemas for users
│   ├── services/
│   │   ├── task_service.py        # Task business logic
│   │   └── user_service.py        # User business logic
│   ├── utils/
│   │   └── pagination.py          # calculate_pagination helper
│   ├── exceptions.py
│   └── main.py                    # App factory + middleware
├── alembic/
│   └── versions/
│       └── 001_phase_1.py         # Initial migration
├── tests/
│   ├── conftest.py                # Fixtures + limiter disabled for unit tests
│   ├── test_auth.py               # 11 auth unit tests
│   ├── test_tasks.py              # 18 task unit tests
│   └── test_rate_limiting.py      # 4 integration tests (needs live server)
├── verify_rate_limiting.py        # Manual rate limit verification script
├── .env.example
├── alembic.ini
├── pytest.ini
└── requirements.txt
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/sgr111/fastapi-task-manager-v4.git
cd fastapi-task-manager-v4
```

### 2. Create virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\Activate.ps1

# Mac/Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/fastapi_taskdb
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=development
BCRYPT_ROUNDS=12
```

### 5. Create PostgreSQL database

```bash
psql -U postgres -c "CREATE DATABASE fastapi_taskdb;"
```

### 6. Run migrations

```bash
alembic upgrade head
```

### 7. Start the server

```bash
uvicorn app.main:app --reload
```

API is now live at `http://localhost:8000`
Swagger docs at `http://localhost:8000/docs`

---

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, get access + refresh tokens |
| POST | `/api/v1/auth/refresh` | Get new access token using refresh token |

### Tasks

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/tasks/` | List all tasks (paginated) |
| POST | `/api/v1/tasks/` | Create new task |
| GET | `/api/v1/tasks/{id}` | Get single task |
| PUT | `/api/v1/tasks/{id}` | Update task |
| DELETE | `/api/v1/tasks/{id}` | Soft delete task |
| GET | `/api/v1/tasks/{id}/audit` | Get task audit log (CDC) |

### Health

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check |

---

## Running Tests

### Unit Tests (no server needed)

```bash
pytest tests/test_auth.py tests/test_tasks.py -v
```

29 tests covering auth flows, task CRUD, pagination, soft deletes, audit logs, and error cases. Rate limiter is disabled for these tests via mock.patch in conftest.py.

### Rate Limiting Integration Tests (live server required)

Start the server first:

```bash
uvicorn app.main:app --reload
```

Then in another terminal:

```bash
pytest tests/test_rate_limiting.py -v
```

4 tests verifying rate limits fire at correct request counts against the real server.

### Manual Rate Limit Verification

```bash
uvicorn app.main:app --reload   # terminal 1
python verify_rate_limiting.py  # terminal 2
```

---

## Rate Limiting

| Endpoint Group | Limit |
|---|---|
| Auth (register, login, refresh) | 30 requests/minute |
| Task reads (list, get, audit) | 100 requests/minute |
| Task writes (create, update, delete) | 30 requests/minute |

Rate limits are **per user** when authenticated (extracted from JWT), falling back to IP address for unauthenticated requests.

**Important:** Rate limiting tests require a live server because pytest's isolated client cannot simulate stateful request counting across tests.

---

## JSONB Metadata

Tasks support flexible metadata stored as JSONB:

```json
{
  "title": "Deploy to production",
  "metadata": {
    "tags": ["urgent", "backend"],
    "department": "engineering",
    "deadline": "2026-05-10",
    "assignee": "john"
  }
}
```

No schema changes needed to add new metadata fields.

---

## Audit Log (CDC)

Every task change is recorded:

```json
[
  {
    "id": 1,
    "task_id": 1,
    "action": "CREATE",
    "old_values": null,
    "new_values": {"title": "New Task"},
    "changed_by": 1,
    "changed_at": "2026-05-02T10:00:00"
  },
  {
    "id": 2,
    "task_id": 1,
    "action": "UPDATE",
    "old_values": {"title": "New Task"},
    "new_values": {"title": "Updated Task"},
    "changed_by": 1,
    "changed_at": "2026-05-02T10:05:00"
  }
]
```

---

## CI/CD

GitHub Actions runs on every push and pull request to main:

- Sets up Python 3.11
- Starts PostgreSQL 15 service
- Installs dependencies
- Runs Alembic migrations
- Runs 29 unit tests (test_auth.py + test_tasks.py)

Rate limiting integration tests are excluded from CI as they require a separately running server instance.

---

## License

MIT
