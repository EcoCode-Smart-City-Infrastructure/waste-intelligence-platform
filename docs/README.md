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
- **Kepler 3D Map** (`kepler.html`, real Kepler.gl 3.0.0 loaded from unpkg, no build step) — geospatial operations view over the same data: demo fleet points coloured/sized by fill, a 3D fill-density grid, urgent-route arcs, live tonnage-by-borough points, and 48-hour fill tracking with a time-range filter. Kepler's own side panel provides layer switching, filters, split maps, drag-and-drop CSV/GeoJSON, and config/image export. Presets (Fleet 3D / Routes / Tonnage / Tracking) move the camera and switch layers through Kepler actions. Default basemap is CARTO Dark Matter (supplied to Kepler as a custom style, no token). Kepler's Dark/Light/Muted/Satellite styles are mapbox:// URLs and show a blank canvas without a token; a Mapbox token can be pasted on the page (stored in that browser's localStorage only) to unlock them. The knowledge graph is deliberately not geo-plotted — its nodes have no coordinates.

## Run locally
```bash
python3 -m http.server 8000   # then open http://localhost:8000/
```
No build step, no API key.

## Sign-in (login.html)
- **Email accounts**: fully working in-browser. Create an account on `login.html` (name, email, password ≥ 8 chars); the password is stored only as a SHA-256 hash in `localStorage` (`wi-accounts-v1`), the session in `sessionStorage`. Accounts do not travel between devices and no verification email is sent — demo-grade local auth, not a server account system. Do not reuse a real password.
- **Google / Apple**: wired to their real client SDKs in `auth.js`, gated by `auth-config.js`. With no client ID configured (the shipped state) the buttons open a setup panel instead of faking a sign-in. Add a Google OAuth client ID / Apple Service ID for the Pages origin to enable them; for shared, server-verified accounts, replace the local store with Firebase Auth, Auth0, or Supabase.
- The app header shows the signed-in account and a Sign out link; signing in is optional — the demo remains open to guests.
