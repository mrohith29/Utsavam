# Utsavam — Backend Documentation

This project implements a scalable backend for **Utsavam**, an event ticketing platform. It supports:

* Users: browse events, book & cancel tickets, view booking history.
* Admins: manage events, view analytics, seed demo data.
* Concurrency-safe booking using **PostgreSQL row locks** and a **Redis token bucket** to prevent overselling.

Built with **FastAPI**, **SQLAlchemy (async)**, **PostgreSQL**, and **Redis (async)**, **Alembic**, and **Uvicorn**.

---

## Docs
- OpenAPI spec: [docs/OPENAPI.yaml](https://github.com/mrohith29/Utsavam/blob/main/docs/OPENAPI.yaml)
- Schema: [docs/SCHEMA.sql](https://github.com/mrohith29/Utsavam/blob/main/docs/SCHEMA.sql)

---

## 1. Prerequisites

Install:

* [Docker](https://www.docker.com/) (for Postgres + Redis)
* [Python 3.11+](https://www.python.org/downloads/)

---

## 2. Clone and install dependencies

```bash
git clone https://github.com/mrohith29/Utsavam.git
cd Utsavam
pip install -r requirements.txt
```

---

## 3. Start services locally with Docker Compose

Use the provided `docker-compose.yml` to run API + Postgres + Redis:

```bash
docker compose up --build
```

This starts:
- API: http://localhost:8000
- Postgres: localhost:5432 (db=utsavam_dev, user=utsavam, pass=utsavam_pass)
- Redis: localhost:6379

---

## 4. Configure environment variables

Copy `.env.example` → `.env`:

```bash
cp .env.example .env
```

Ensure it contains:

```
DATABASE_URL=postgresql+asyncpg://utsavam:utsavam_pass@localhost:5433/utsavam_dev
REDIS_URL=redis://localhost:6379/0
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
$env:DATABASE_URL = "postgresql+asyncpg://utsavam:utsavam_pass@localhost:5433/utsavam_dev"
$env:REDIS_URL="redis://localhost:6379/0"

alembic upgrade head

ADMIN_KEY=change_me_admin_key
```

---

## 5. Run database migrations

Use Alembic to create tables:

```bash
cd backend
alembic upgrade head
```

---

## 6. Seed demo data

Seed users, events, and initialize Redis token counters:

```bash
# Option A: seed script
$env:DATABASE_URL = "postgresql+asyncpg://utsavam:utsavam_pass@localhost:5433/utsavam_dev"
python backend/scripts/seed_demo.py

# Option B: via API (Swagger) with ADMIN_KEY
curl -X POST http://localhost:8000/admin/seed_demo_data \
  -H "X-Admin-Key: change_me_admin_key"
```

---

## 7. Run the FastAPI server

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 8. API Overview

* **Health check**

  ```
  GET /health
  ```
* **Events**

  ```
  GET /events
  GET /events/{id}
  ```
* **Bookings**

  ```
  POST /bookings   { "user_id": 1, "event_id": 1, "seats": 1 }
  DELETE /bookings/{booking_id}
  ```
* **User history**

  ```
  GET /users/{user_id}/bookings
  ```
* **Admin (requires `X-Admin-Key` header)**

  ```
  GET /admin/users
  POST /admin/events
  PUT /admin/events/{id}
  GET /admin/events/{id}/bookings
  GET /admin/analytics
  DELETE /admin/events/{id}
  POST /admin/seed_demo_data
  ```

---

## 9. Concurrency Testing

We provide a stress test script:

```bash
python tests/concurrency_test.py
```

* Simulates 50 concurrent booking requests for the same event.
* Expected outcome (if event capacity = 5):

```
total: 50 success: 5 conflict: 45 errors: 0
```

---

## 10. Useful Docker Commands

Check Postgres contents:

```bash
docker exec -it utsavam-postgres psql -U utsavam -d utsavam_dev -c "SELECT * FROM events;"
docker exec -it utsavam-postgres psql -U utsavam -d utsavam_dev -c "SELECT * FROM bookings;"
```

Check Redis tokens:

```bash
docker exec -it utsavam-redis redis-cli GET "event:1:tokens"
```

Reset tokens manually:

```bash
docker exec -it utsavam-redis redis-cli SET "event:1:tokens" 5
```

---
```bash
alembic upgrade head
```

---
✅ At this point:

* You can browse events via Swagger.
* Book tickets safely under concurrency load.
* Admins can create/update events and seed demo data.
