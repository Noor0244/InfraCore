FROM python:3.11-slim

# Minimal, production-safe defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the whole project (do not refactor or move files)
COPY . /app

# Render provides $PORT at runtime; EXPOSE is informational (default local port is 10000)
EXPOSE 10000

# Runs the existing entrypoint (main.py), which reads $PORT and binds 0.0.0.0
CMD ["python", "main.py"]
