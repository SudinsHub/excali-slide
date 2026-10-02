FROM python:3.12-slim

# Install system dependencies including graphviz
RUN apt-get update && apt-get install -y --no-install-recommends \
    graphviz \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency files
COPY pyproject.toml .

# Install dependencies
RUN uv sync --frozen --no-cache || uv sync --no-cache

# Copy application code
COPY . .

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
