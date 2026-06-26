#!/bin/sh
set -e

wait_for_tcp() {
  host="$1"
  port="$2"
  label="$3"
  echo "Waiting for ${label} (${host}:${port})..."
  i=0
  while [ "$i" -lt 60 ]; do
    if python - <<PY
import socket
s = socket.socket()
s.settimeout(1)
try:
    s.connect(("${host}", int("${port}")))
except OSError:
    raise SystemExit(1)
finally:
    s.close()
PY
    then
      echo "${label} is ready."
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  echo "Timed out waiting for ${label}."
  return 1
}

if [ -n "${POSTGRES_HOST:-}" ] && [ "${POSTGRES_HOST}" != "localhost" ] && [ "${POSTGRES_HOST}" != "127.0.0.1" ]; then
  wait_for_tcp "${POSTGRES_HOST}" "${POSTGRES_PORT:-5432}" "PostgreSQL"
fi

if [ -n "${REDIS_URL:-}" ]; then
  redis_host=$(python - <<'PY'
import os
from urllib.parse import urlparse
url = os.environ.get('REDIS_URL', '')
parsed = urlparse(url)
print(parsed.hostname or '127.0.0.1')
PY
)
  redis_port=$(python - <<'PY'
import os
from urllib.parse import urlparse
url = os.environ.get('REDIS_URL', '')
parsed = urlparse(url)
print(parsed.port or 6379)
PY
)
  if [ "${redis_host}" != "127.0.0.1" ] && [ "${redis_host}" != "localhost" ]; then
    wait_for_tcp "${redis_host}" "${redis_port}" "Redis"
  fi
fi

echo "Running migrations..."
python manage.py migrate --noinput

if [ "${RUN_COLLECTSTATIC:-true}" = "true" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput
fi

exec "$@"
