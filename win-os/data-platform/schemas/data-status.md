# Data status vocabulary (canonical)

| Status | Meaning | UI convention |
| --- | --- | --- |
| observed | Directly measured by a sensor or verified count | plain value |
| reported | Supplied by a person or external system, not directly measured | plain value + source |
| derived | Calculated from other records (formula + version recorded) | value + "derived" label |
| forecast | Model prediction about the future | value + interval + "forecast" label |
| simulated | Produced by a scenario/simulation, not the real world | value + "simulated" label, never mixed into observed totals |
| unavailable | Not known | shown as "unavailable" / empty - never 0 |

Rules: missing values stay NULL; a planned route is never an executed route;
a forecast capacity is never a measured capacity; an offline sensor is
`unavailable`, never zero. Freshness and quality are recorded separately
(`quality_status`, `ingested_at`, `observed_at`).
