# Waste Intelligence — Web App

Zero-build static web app for the EcoCode Waste Intelligence Platform, published by GitHub Pages from branch `web-app`, folder `docs/`.

## Views
- **Dashboard** — demo fleet KPIs, urgent bins, live DSNY tonnage aggregated by borough.
- **Live NYC Data** — direct Socrata queries: `ebb7-mvp5` (tonnage), `gaq9-z3hz` (diversion/capture), `6yag-pnij` (organics), `6r9j-qrwz` (facilities). Labelled sample fallback only if the live call fails.
- **Bins & Routes** — demo fleet (hub API returns no bins), add/collect bins, nearest-neighbour collection route, localStorage persistence.
- **Forecasting** — ports `services/forecasting/app.py`: current-cycle cut on a drop > 30 points, least-squares slope, R², time-to-full, z-score anomaly.
- **Knowledge Graph** — the repo's real sample: `cloud_platform/analytics/kg/data/w2rkg_nyc_sample.json` (31 nodes, 55 edges), in `kg.json`.
- **Contamination** — backend acceptance map from `services/contamination/app.py`, with manual material tagging. YOLOv11 itself needs the backend service and cannot run on Pages.
- **Connect** — probes a locally running hub / forecasting / contamination service at `/health`.

## Run locally
```bash
python3 -m http.server 8000   # then open http://localhost:8000/
```
No build step, no API key.
