FROM python:3.11-slim

WORKDIR /app

COPY --from=astral/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade heads && uv run uvicorn main:app --host :: --port 8080"]



