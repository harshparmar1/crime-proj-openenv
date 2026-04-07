# ─── HF Spaces Docker image for CrimeTriageOpenEnv ──────────────────────────
# Build: docker build -t crime-triage-openenv .
# Run:   docker run -p 7860:7860 crime-triage-openenv
# URL:   http://localhost:7860

FROM python:3.11-slim

# Metadata
LABEL maintainer="CrimeTriageOpenEnv"
LABEL description="Real-world crime-incident triage environment with Gradio UI"

# System dependencies (minimal)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the full openenv directory
COPY . .

# Hugging Face Spaces requires port 7860
EXPOSE 7860

# Health-check so HF knows the container is ready
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:7860/ || exit 1

# Entry point: Gradio app (app.py calls demo.launch on 0.0.0.0:7860)
CMD ["python", "app.py"]
