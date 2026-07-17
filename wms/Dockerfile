FROM python:3.11-slim

WORKDIR /app

RUN pip install poetry==1.8.3 && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root --no-interaction

COPY . .

# Startda: migratsiya → demo seed (idempotent) → server ($PORT).
CMD ["sh", "start.sh"]
