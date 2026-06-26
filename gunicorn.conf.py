import multiprocessing
import os

bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
workers = int(os.environ.get('GUNICORN_WORKERS', '4'))
threads = int(os.environ.get('GUNICORN_THREADS', '2'))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '30'))
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '2000'))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '100'))
worker_class = 'gthread' if threads > 1 else 'sync'
accesslog = '-'
errorlog = '-'
capture_output = True

# Respect container CPU limits when GUNICORN_WORKERS is not set explicitly.
if 'GUNICORN_WORKERS' not in os.environ:
    try:
        cpu_count = len(os.sched_getaffinity(0))
    except AttributeError:
        cpu_count = multiprocessing.cpu_count()
    workers = max(2, min(8, cpu_count * 2 + 1))

wsgi_app = 'core.wsgi:application'
