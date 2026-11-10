# WIN Edge profile

Status: Partially implemented (v0.2)

Implemented: device registration, telemetry batch ingestion with
store-and-forward idempotency ((org, device, client_event_id)), the edge
MQTT bridge (win-os/apps/edge/mqtt_bridge.py) with a local SQLite buffer that
flushes in order when the API returns, and the Mosquitto broker via the edge
Compose profile. A device that has never reported reads as telemetry
'unavailable' - never zero. Not yet done: MQTT broker authentication rollout
(password file/TLS), OTA update channel, on-device buffering firmware.
Simulated telemetry must always be labelled simulated.
