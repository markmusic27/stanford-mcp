FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Optional: build tooling for any wheels that may require it
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && rm -rf /var/lib/apt/lists/*

# Install deps directly from pyproject's list (no build backend defined)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
      "anyio>=4.10.0" \
      "click>=8.2.1" \
      "explorecourses>=1.0.6" \
      "httpx>=0.28.1" \
      "mcp[cli]>=1.14.0" \
      "starlette>=0.47.3" \
      "uvicorn>=0.32.0"

# Copy source
COPY src/ /app/src/
COPY README.md pyproject.toml /app/

# Cloud Run provides PORT; default to 8080 for local runs
ENV PORT=8080
EXPOSE 8080

# Use the package entrypoint
CMD ["python", "-m", "src"]