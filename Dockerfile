FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY arus/ ./arus/
RUN find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
COPY alembic.ini .
COPY alembic/ ./alembic/
RUN find /app -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8081/api/health || exit 1

CMD ["uvicorn", "arus.main:app", "--host", "0.0.0.0", "--port", "8081"]
