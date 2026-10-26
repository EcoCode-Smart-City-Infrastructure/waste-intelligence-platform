FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY services/kg/requirements.txt .
RUN pip install -r requirements.txt
COPY services/kg/app.py .
COPY cloud_platform/__init__.py ./cloud_platform/__init__.py
COPY cloud_platform/analytics/__init__.py ./cloud_platform/analytics/__init__.py
COPY cloud_platform/analytics/kg/ ./cloud_platform/analytics/kg/

EXPOSE 8003

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8003"]
