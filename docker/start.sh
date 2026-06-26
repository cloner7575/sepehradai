#!/bin/sh
set -e

shutdown() {
  echo "Shutting down services..."
  [ -n "${CELERY_WORKER_PID:-}" ] && kill "${CELERY_WORKER_PID}" 2>/dev/null || true
  [ -n "${CELERY_BEAT_PID:-}" ] && kill "${CELERY_BEAT_PID}" 2>/dev/null || true
  [ -n "${GUNICORN_PID:-}" ] && kill "${GUNICORN_PID}" 2>/dev/null || true
  wait 2>/dev/null || true
}

trap shutdown TERM INT

CELERY_CONCURRENCY="${CELERY_CONCURRENCY:-8}"

echo "Starting Celery worker..."
celery -A core worker \
  --loglevel=info \
  --concurrency="${CELERY_CONCURRENCY}" \
  -Q webhooks,campaigns &
CELERY_WORKER_PID=$!

echo "Starting Celery beat..."
celery -A core beat --loglevel=info &
CELERY_BEAT_PID=$!

echo "Starting Gunicorn..."
gunicorn core.wsgi:application -c gunicorn.conf.py &
GUNICORN_PID=$!

wait "${GUNICORN_PID}"
