FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       curl \
       chromium \
       chromium-driver \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

WORKDIR /tmp/recipe-python
COPY pyproject.toml ./
RUN uv sync --no-dev

WORKDIR /workspace/python
CMD ["uv", "run", "flask", "--app", "app.api:app", "run", "--host=0.0.0.0", "--port=5000"]
