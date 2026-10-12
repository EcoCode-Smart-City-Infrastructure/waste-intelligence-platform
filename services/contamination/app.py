"""Contamination detection inference service.

Loads the YOLOv11-seg litter-material model (CatSat/yolov11-litter-materials,
fine-tuned on TACO) and exposes a /predict endpoint. Material classes map
directly to recycling streams; contamination = detected material not accepted
for the stream being checked.

Called by the waste-intelligence API's /mcp/waste/contamination endpoint via
the CONTAMINATION_SERVICE_URL environment variable.
"""

from __future__ import annotations

import io
import logging
import os

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image

logger = logging.getLogger(__name__)

MODEL_REPO = os.getenv("MODEL_REPO", "CatSat/yolov11-litter-materials")
MODEL_FILE = os.getenv("MODEL_FILE", "best.pt")
CONF_THRESHOLD = float(os.getenv("CONF_THRESHOLD", "0.25"))

# Recycling-stream acceptance map: which detected materials belong in which bin.
STREAM_MATERIALS = {
    "recycling": {"Plastic", "Metal", "Glass", "Paper"},
    "organics": set(),
    "landfill": {"Other"},
}

app = FastAPI(title="Waste Contamination Inference")
_model = None


def get_model():
    """Lazy-load the YOLO model (downloads weights from HF Hub on first use)."""
    global _model
    if _model is None:
        from huggingface_hub import hf_hub_download
        from ultralytics import YOLO

        logger.info("Downloading %s/%s", MODEL_REPO, MODEL_FILE)
        weights = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE)
        _model = YOLO(weights)
        logger.info("Model loaded: %s", _model.names)
    return _model


@app.get("/health")
def health():
    return {"status": "ok", "model": f"{MODEL_REPO}/{MODEL_FILE}"}


@app.post("/predict")
async def predict(
    image: UploadFile = File(...),
    stream: str = "recycling",
    conf: float = CONF_THRESHOLD,
):
    data = await image.read()
    try:
        pil = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid image: {e}")

    model = get_model()
    results = model.predict(pil, conf=conf, verbose=False)
    r = results[0]

    accepted = STREAM_MATERIALS.get(stream, STREAM_MATERIALS["recycling"])
    detections = []
    contaminants = []
    for box, cls_id, score in zip(r.boxes.xyxy, r.boxes.cls, r.boxes.conf):
        material = r.names[int(cls_id)]
        det = {
            "material": material,
            "confidence": round(float(score), 3),
            "bbox": [round(float(v), 1) for v in box.tolist()],
        }
        detections.append(det)
        if material not in accepted:
            contaminants.append(det)

    return JSONResponse(
        {
            "stream": stream,
            "is_contaminated": len(contaminants) > 0,
            "contaminant_count": len(contaminants),
            "contaminants": contaminants,
            "detections": detections,
            "model": f"{MODEL_REPO}/{MODEL_FILE}",
        }
    )
