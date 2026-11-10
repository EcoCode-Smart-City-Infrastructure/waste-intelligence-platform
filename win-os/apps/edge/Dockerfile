FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /edge
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mqtt_bridge.py .
RUN useradd --system --uid 10002 edge && chown -R edge /edge
USER edge
CMD ["python", "mqtt_bridge.py"]
