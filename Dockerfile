FROM python:3.12-slim

# Keep Python output unbuffered and skip .pyc files for cleaner container logs.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so Docker can cache this layer across code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY . .

# Railway provides $PORT at runtime; default to 8080 for local `docker run`.
ENV PORT=8080
EXPOSE 8080

# Use shell form so $PORT is expanded at container start.
CMD gunicorn app:app --bind 0.0.0.0:$PORT
