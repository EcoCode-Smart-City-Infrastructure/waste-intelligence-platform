# Contamination Inference Service

Vision microservice for waste contamination detection. Serves the YOLOv11-seg
litter-material model (`CatSat/yolov11-litter-materials`, MIT, fine-tuned on
TACO) over HTTP for the waste-intelligence API.

## Endpoints

- `GET /health` — liveness + model identifier
- `POST /predict` — multipart `image`, query `stream` (recycling | organics |
  landfill, default recycling), `conf` (default 0.25).
  Returns detections (material, confidence, bbox) and a contamination verdict:
  any detected material not accepted for the stream is a contaminant.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8005
```

Weights download from HuggingFace Hub on first request (~40MB).

## Configuration

| Env var          | Default                          |
|------------------|----------------------------------|
| MODEL_REPO       | CatSat/yolov11-litter-materials  |
| MODEL_FILE       | best.pt                          |
| CONF_THRESHOLD   | 0.25                             |

## Wiring

The waste-intelligence API calls this service when `CONTAMINATION_SERVICE_URL`
is set (see `docker-compose.yml`). Without it, `/mcp/waste/contamination`
returns the honest "model not deployed" error instead of fabricated results.

## Production notes

- Runs on CPU; add `--gpus all` and a CUDA torch build for GPU inference.
- For the sorting-line domain, fine-tune on conveyor-belt imagery (e.g. the
  WaRP dataset) — current weights are trained on in-the-wild litter photos.
