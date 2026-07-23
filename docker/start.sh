#!/bin/sh
set -e

run_migrate() {
  echo "Running database migrations..."
  python manage.py migrate --noinput
  echo "Migrations complete."
}

run_collectstatic() {
  if [ "${RUN_COLLECTSTATIC:-true}" = "true" ]; then
    echo "Collecting static files into ${STATIC_ROOT:-public/static}..."
    python manage.py collectstatic --noinput
    echo "collectstatic complete."
  else
    echo "Skipping collectstatic (RUN_COLLECTSTATIC=false)."
  fi
}

PROCESS_TYPE="${PROCESS_TYPE:-web}"

case "${PROCESS_TYPE}" in
  web)
    run_migrate
    run_collectstatic
    echo "Starting Gunicorn..."
    exec gunicorn core.wsgi:application -c gunicorn.conf.py
    ;;
  worker)
    echo "Starting Celery worker..."
    exec celery -A core worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-8}" -Q webhooks,campaigns,instagram
    ;;
  beat)
    echo "Starting Celery beat..."
    exec celery -A core beat --loglevel=info
    ;;
  *)
    echo "Unknown PROCESS_TYPE=${PROCESS_TYPE}" >&2
    exit 2
    ;;
esac
