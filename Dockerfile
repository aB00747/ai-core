FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies for psycopg2 and chroma-hnswlib
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq-dev gcc g++ build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py config.py database.py dependencies.py ./
COPY core/ core/
COPY chat/ chat/
COPY insights/ insights/
COPY documents/ documents/
COPY health/ health/

# Create data directory and non-root user
RUN mkdir -p /app/data && \
    addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser && \
    chown -R appuser:appgroup /app

USER appuser

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
