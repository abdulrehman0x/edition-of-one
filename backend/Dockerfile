FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \
    libffi-dev fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app /app/app
COPY backend/prompts /app/prompts
COPY pdf_generator /app/pdf_generator
COPY pipelines /app/pipelines
COPY data/fallback_articles.json /app/data/fallback_articles.json

# config.py resolves data/ relative to APP_ROOT (inside the image the file
# lives at /app/app/core, so the parents[3] heuristic would point at "/").
ENV APP_ROOT=/app
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
