# WIN Intelligence profile

Status: Partially implemented (v0.2)

Baseline forecasting (linear trend, with model metadata) and z-score anomaly
detection run inside the WIN API. The intelligence Compose profile also joins
the existing forecasting and copilot services unchanged. Scenario comparison
is available as clearly-labelled simulations (POST /api/v1/simulations).
Planned: OR-Tools-based optimisation service, model registry UI, forecast
evaluation against held-out data.
