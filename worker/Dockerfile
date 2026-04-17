FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/backend-requirements.txt
COPY worker/requirements.txt /tmp/worker-requirements.txt
RUN pip install --no-cache-dir -r /tmp/backend-requirements.txt -r /tmp/worker-requirements.txt

COPY backend /app/backend
COPY worker /app/worker

# Concurrency=2 for 2-core VPS (1 task per core)
CMD ["python", "-m", "celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
