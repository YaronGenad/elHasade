# Build context must be the repository ROOT (one level above backend/).
# Example: docker build -f backend/Dockerfile -t alhasade-backend .
#
FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies (backend + pipeline)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright Chromium to a shared path that the non-root runtime user can read.
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN playwright install-deps chromium && \
    playwright install chromium && \
    chmod -R a+rX /opt/playwright

# Copy the source generation pipeline
COPY src/ ./src/

# Copy the backend application
COPY backend/app/ ./app/
COPY backend/alembic/ ./alembic/
COPY backend/alembic.ini ./alembic.ini

EXPOSE 8000

ENV NAME=AlHasadehBackend

# Run as non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser && \
    chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
