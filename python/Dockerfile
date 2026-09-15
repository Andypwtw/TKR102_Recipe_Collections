FROM python:3.12-slim

WORKDIR /workspace/python

RUN apt-get update     && apt-get install -y --no-install-recommends build-essential curl     && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH=/workspace/python
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml ./
COPY uv.lock* ./
RUN uv sync || true

COPY . .

EXPOSE 5000
