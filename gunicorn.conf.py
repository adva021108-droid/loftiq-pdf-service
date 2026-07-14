"""Gunicorn configuration for the Loftiq PDF service.

Reads the listen port from the ``PORT`` environment variable (set by Railway
at runtime), falling back to 8080. Because gunicorn resolves the bind here in
Python, we no longer depend on shell variable expansion in the Dockerfile CMD.
"""

import multiprocessing
import os

# Bind to the platform-provided port, defaulting to 8080 for local runs.
port = os.environ.get("PORT", "8080")
bind = f"0.0.0.0:{port}"

# Modest worker count; overridable via WEB_CONCURRENCY.
workers = int(os.environ.get("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2 + 1))

# Log to stdout/stderr so container platforms capture the output.
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# PDF rendering can take a moment for large payloads.
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
