# Crime Intelligence API (FastAPI) + OpenEnv package
# Build from repository root: docker build -t crime-intelligence .
# Run: docker run -p 8000:8000 -e DATABASE_URL=sqlite:////data/crime.db -v crime_data:/data crime-intelligence

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libsm6 libxext6 libxrender1 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend /app/backend
COPY openenv /app/openenv

ENV PYTHONPATH=/app/backend:/app/openenv
WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
