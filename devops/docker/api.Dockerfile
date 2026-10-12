FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 5000

# Run as a module from /app so `hub_layer.*` absolute imports resolve.
# The old entrypoint (`python hub-layer/api/app.py`) put hub_layer/api on
# sys.path, breaking every absolute import and crash-looping the container.
CMD ["python", "-m", "hub_layer.api.app"]
