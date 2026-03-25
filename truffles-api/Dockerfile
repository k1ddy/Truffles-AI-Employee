FROM python:3.11-slim

WORKDIR /app

ARG APP_VERSION="unknown"
ARG GIT_COMMIT="unknown"
ARG BUILD_TIME="unknown"

ENV APP_VERSION=$APP_VERSION
ENV GIT_COMMIT=$GIT_COMMIT
ENV BUILD_TIME=$BUILD_TIME

COPY truffles-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY truffles-api/pyproject.toml .
COPY truffles-api/app/ ./app/
COPY truffles-api/tests/ ./tests/
COPY truffles-api/migrations/ ./migrations/
COPY truffles-api/scripts/ ./scripts/
COPY prompts/ ./prompts/
COPY contracts/ ./contracts/
COPY ops/ /ops/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
