# Forecasting Service

Statistical forecasting and anomaly detection over bin telemetry.
Replaces the phantom `ml-service` placeholder — this one is real.

## Model

No black box: for each bin it takes the current fill cycle (history after
the last collection event, detected as a >30-point fill drop), fits a
least-squares linear trend, and projects it to the requested horizon.
Confidence comes from the fit quality (R²), discounted for thin data.
Anomaly detection is z-score based per metric against the bin's own history.

Honest about limits: with <2 readings (forecast) or <5 (anomaly) it returns
422 instead of fabricating numbers.

## Endpoints

- `GET /health` — liveness + DB reachability
- `POST /forecast` — `{bin_id, horizon_hours?, history_limit?}` →
  `predicted_value`, `confidence`, `hours_until_full`, `trend_fill_per_hour`,
  `r_squared`, `readings_used`
- `POST /anomaly` — `{bin_id, features: {filllevelpct?, mass_kg?}, threshold?}` →
  `is_anomaly`, `anomaly_score`, `z_scores`

## Run

```bash
pip install -r requirements.txt
DATABASE_URL=postgresql://timescale:password@localhost:5432/wasteintel \
  uvicorn app:app --port 8002
```

## Wiring

`docker-compose.yml` runs this as `ml-service:8002`; the waste-intel API
calls it via `ML_URL`. Response shapes match what
`ml_inference.run_forecast` / `run_anomaly` validate (`predicted_value`,
`is_anomaly`), so no API changes were needed.
