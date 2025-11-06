"""Gunicorn/Uvicorn worker configuration."""

# TODO: Configure production-ready ASGI server:
# - Worker count
# - Timeout settings
# - Graceful shutdown
# - Logging configuration

import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8000"
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

