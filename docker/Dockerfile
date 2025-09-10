FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend ./backend

# Expose port for uvicorn
EXPOSE 8000

# Default envs (override in runtime)
ENV PORT=8000 \
    HOST=0.0.0.0 \
    DATABASE_URL=postgresql+asyncpg://utsavam:utsavam_pass@postgres:5433/utsavam_dev \
    REDIS_URL=redis://redis:6379/0 \
    ADMIN_KEY=change_me_admin_key

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]


