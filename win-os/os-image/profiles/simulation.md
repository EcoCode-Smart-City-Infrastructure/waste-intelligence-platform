# WIN Simulation profile

Status: Partially implemented (v0.2)

Implemented: waste-flow diversion scenarios via POST /api/v1/simulations -
inputs (total kg, current vs target diversion, material/pathway) produce
projected diverted kg and CO2e using the WIN-ENV-ACCT factors. Every result
carries data_status=simulated and is excluded from environmental totals.
The existing web app's digital twin remains the geospatial visualisation.
Planned: route/facility capacity scenarios and forecast-vs-simulation
comparison views.
