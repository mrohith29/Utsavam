# Utsavam — Event Ticketing Platform

A scalable backend for **Utsavam**, an event ticketing platform built with modern technologies and concurrency-safe booking mechanisms.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Quick Start with Docker](#quick-start-with-docker)
- [Manual Setup](#manual-setup)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Useful Commands](#useful-commands)
- [Documentation](#documentation)

## 🎯 Overview

Utsavam is a robust event ticketing platform that provides:

- **User Management**: Browse events, book & cancel tickets, view booking history
- **Admin Panel**: Manage events, view analytics, seed demo data
- **Concurrency Safety**: PostgreSQL row locks and Redis token bucket to prevent overselling
- **Scalable Architecture**: Built with async/await patterns for high performance

## ✨ Features

### Core Functionality
- **Event Management**: Create, update, and manage events with capacity limits
- **Ticket Booking**: Safe concurrent booking with overselling prevention
- **User System**: User registration, authentication, and booking history
- **Admin Dashboard**: Complete event and user management capabilities

### Technical Features
- **Concurrency Control**: PostgreSQL row-level locking for data consistency
- **Rate Limiting**: Redis-based token bucket algorithm
- **Async Operations**: Full async/await support for better performance
- **Database Migrations**: Alembic for schema versioning
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

## 🛠 Tech Stack

- **Backend**: FastAPI, SQLAlchemy (async)
- **Database**: PostgreSQL with asyncpg driver
- **Cache**: Redis (async)
- **Migrations**: Alembic
- **Server**: Uvicorn
- **Containerization**: Docker & Docker Compose

## 🐳 Quick Start with Docker

### Prerequisites
- [Docker](https://www.docker.com/) and Docker Compose
- [Python 3.11+](https://www.python.org/downloads/)

### 1. Clone and Setup
```bash
git clone https://github.com/mrohith29/Utsavam.git
cd Utsavam
```

### 2. Start Services
```bash
docker compose up --build
```

This starts:
- **API**: http://localhost:8000
- **Postgres**: localhost:5432 (db=utsavam_dev, user=utsavam, pass=utsavam_pass)
- **Redis**: localhost:6379

### 3. Configure Environment
```bash
cp .env.example .env
```

Update `.env` with:
```env
DATABASE_URL=postgresql+asyncpg://utsavam:utsavam_pass@localhost:5433/utsavam_dev
REDIS_URL=redis://localhost:6379/0
ADMIN_KEY=change_me_admin_key
```

### 4. Run Migrations
```bash
cd backend
alembic upgrade head
```

### 5. Seed Demo Data
```bash
# Via script
python backend/scripts/seed_demo.py

# Or via API
curl -X POST http://localhost:8000/admin/seed_demo_data \
  -H "X-Admin-Key: change_me_admin_key"
```

### 6. Start Development Server
```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)

## 🔧 Manual Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Database
```bash
# Create database
createdb utsavam_dev

# Run migrations
cd backend
alembic upgrade head
```

### 3. Setup Redis
```bash
# Start Redis server
redis-server
```

### 4. Configure Environment
Set environment variables:
```bash
export DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/utsavam_dev"
export REDIS_URL="redis://localhost:6379/0"
export ADMIN_KEY="change_me_admin_key"
```

## 📚 API Documentation

### Public Endpoints

#### Health Check
```http
GET /health
```

#### Events
```http
GET /events                    # List all events
GET /events/{id}              # Get event details
```

#### Bookings
```http
POST /bookings                # Create booking
DELETE /bookings/{booking_id} # Cancel booking
```

#### User History
```http
GET /users/{user_id}/bookings # Get user's booking history
```

### Admin Endpoints (Requires `X-Admin-Key` header)

```http
GET /admin/users              # List all users
POST /admin/events           # Create event
PUT /admin/events/{id}       # Update event
DELETE /admin/events/{id}    # Delete event
GET /admin/events/{id}/bookings # Get event bookings
GET /admin/analytics         # Get platform analytics
POST /admin/seed_demo_data   # Seed demo data
```

### Example Booking Request
```json
POST /bookings
{
  "user_id": 1,
  "event_id": 1,
  "seats": 2
}
```

## 🧪 Testing

### Concurrency Testing
Test the system's ability to handle concurrent bookings:

```bash
python tests/concurrency_test.py
```

**Expected Results** (for event with capacity = 5):
```
total: 50 success: 5 conflict: 45 errors: 0
```

This test simulates 50 concurrent booking requests and verifies that only 5 succeed (matching the event capacity), with the rest properly rejected due to conflicts.

## 🔍 Useful Commands

### Database Operations
```bash
# Check events
docker exec -it utsavam-postgres psql -U utsavam -d utsavam_dev -c "SELECT * FROM events;"

# Check bookings
docker exec -it utsavam-postgres psql -U utsavam -d utsavam_dev -c "SELECT * FROM bookings;"
```

### Redis Operations
```bash
# Check available tokens
docker exec -it utsavam-redis redis-cli GET "event:1:tokens"

# Reset tokens manually
docker exec -it utsavam-redis redis-cli SET "event:1:tokens" 5
```

### Development
```bash
# Run migrations
alembic upgrade head

# Generate new migration
alembic revision --autogenerate -m "description"

# Run tests
python -m pytest tests/
```

## 📖 Documentation

- **OpenAPI Specification**: [docs/OPENAPI.yaml](https://github.com/mrohith29/Utsavam/blob/main/docs/OPENAPI.yaml)
- **Database Schema**: [docs/SCHEMA.sql](https://github.com/mrohith29/Utsavam/blob/main/docs/SCHEMA.sql)

---

## ✅ Getting Started Checklist

- [ ] Docker services running (`docker compose up --build`)
- [ ] Environment variables configured
- [ ] Database migrations applied (`alembic upgrade head`)
- [ ] Demo data seeded
- [ ] API server running (`uvicorn backend.app.main:app --reload`)
- [ ] Swagger UI accessible at http://localhost:8000/docs
- [ ] Concurrency test passing

**You're all set!** 🎉 You can now browse events, book tickets safely under concurrent load, and manage the platform through the admin interface.
