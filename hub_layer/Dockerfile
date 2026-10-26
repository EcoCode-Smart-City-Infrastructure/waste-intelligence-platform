FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir flask>=3.0.0 psycopg2-binary gunicorn httpx
COPY hub_layer/ ./hub_layer/

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "hub_layer.api.app:create_app()"]
