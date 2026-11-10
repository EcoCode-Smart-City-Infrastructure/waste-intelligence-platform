# WIN OS web application integration

The existing WIN web application is preserved as-is:

- Live: https://ecocode-smart-city-infrastructure.github.io/waste-intelligence-platform/#dashboard
- Source: branch `web-app`, `docs/` (static, zero-build)
- It consumes NYC Socrata open data directly and labels demo/simulated data;
  that honesty contract is unchanged by WIN OS.

WIN OS integration path (incremental, no rebuild):

1. Point the app's backend configuration (`docs/backend.js` on the web-app
   branch) at a deployed WIN API (`/api/v1/...`) when one exists.
2. Until then the app keeps its current behaviour and explicit empty/demo
   states; no screen is claimed backend-connected before it is.
3. Workspace mapping: the app's existing views group into the seven WIN
   workspaces - Command Center (dashboard), Operations (bins, routes,
   network, admin), Intelligence (forecasting, assistant), Circular Economy
   (knowledge graph, contamination), Digital Twin (twin, Kepler),
   Data and Integrations (live data, connect), WIN Control Center
   (admin dashboard/settings) - without renaming or removing any view.
