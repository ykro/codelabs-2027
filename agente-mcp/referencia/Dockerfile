FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12.2 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY *.py chat.html ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}
