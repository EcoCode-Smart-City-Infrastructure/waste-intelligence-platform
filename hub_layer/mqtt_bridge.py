"""MQTT bridge: subscribes to waste telemetry topics and persists bin readings.

Subscribes to the topic layout documented in
``mesh-network/mqtt/mosquitto.conf``:

- ``waste/bin/telemetry``      -> validated and stored in the ``telemetry`` table
- ``waste/cluster/aggregates`` -> logged (no storage table yet)
- ``waste/facility/dispatch``  -> logged (no storage table yet)

Bin payloads follow the ESP32 firmware format::

    {"sensor_id": "esp32-bin-001", "fill_level_percent": 42.0,
     "mass_kg": 18.5, "timestamp": 123456}

The firmware's ``timestamp`` is device uptime in milliseconds, not wall
time, so ``reported_at`` is set to the database ``NOW()`` at insert time.

On startup the bridge applies ``hub_layer/database/schema.sql`` (all
statements are ``CREATE TABLE IF NOT EXISTS``, so this is idempotent) to
guarantee the tables it writes to exist.

Configuration via environment:
    MQTT_BROKER  hostname of the broker (default: localhost)
    MQTT_PORT    broker port (default: 1883)
    MQTT_TOPICS  comma-separated topic list (default: the three above)
    DATABASE_URL Postgres DSN (see hub_layer.db)
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
from pathlib import Path

import paho.mqtt.client as mqtt

from .db import execute_sql

logger = logging.getLogger("mqtt_bridge")

BIN_TELEMETRY_TOPIC = "waste/bin/telemetry"
DEFAULT_TOPICS = (
    "waste/bin/telemetry",
    "waste/cluster/aggregates",
    "waste/facility/dispatch",
)

REQUIRED_BIN_FIELDS = ("sensor_id", "fill_level_percent", "mass_kg")

SCHEMA_PATH = Path(__file__).resolve().parent / "database" / "schema.sql"


def ensure_schema() -> None:
    """Apply the hub-layer schema so the tables we write to exist."""
    if not SCHEMA_PATH.exists():
        logger.warning("schema file not found at %s - skipping", SCHEMA_PATH)
        return
    sql = SCHEMA_PATH.read_text(encoding="utf-8")
    # psycopg2 executes one statement at a time; split on semicolons.
    statements = [s.strip() for s in sql.split(";") if s.strip()]
    applied = 0
    for stmt in statements:
        try:
            execute_sql(stmt)
            applied += 1
        except Exception as exc:  # noqa: BLE001 - keep the bridge alive
            logger.error("schema statement failed: %s", exc)
    logger.info("schema ensured (%d statements applied)", applied)


def parse_bin_payload(raw: bytes) -> dict:
    """Parse and validate a bin telemetry payload. Raises ValueError."""
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"payload is not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("payload must be a JSON object")
    missing = [f for f in REQUIRED_BIN_FIELDS if f not in payload]
    if missing:
        raise ValueError(f"missing required fields: {missing}")
    try:
        fill = float(payload["fill_level_percent"])
        mass = float(payload["mass_kg"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"fill_level_percent/mass_kg must be numeric: {exc}") from exc
    return {
        "sensor_id": str(payload["sensor_id"]),
        "fill_level_percent": fill,
        "mass_kg": mass,
    }


def store_bin_telemetry(reading: dict) -> None:
    execute_sql(
        "INSERT INTO telemetry (bin_id, fill_level_percent, mass_kg) "
        "VALUES (%s, %s, %s)",
        (reading["sensor_id"], reading["fill_level_percent"], reading["mass_kg"]),
    )


def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage) -> None:  # noqa: ARG001
    topic = msg.topic
    if topic == BIN_TELEMETRY_TOPIC:
        try:
            reading = parse_bin_payload(msg.payload)
        except ValueError as exc:
            logger.warning("dropping invalid bin payload: %s", exc)
            return
        try:
            store_bin_telemetry(reading)
        except Exception as exc:  # noqa: BLE001 - keep the bridge alive
            logger.error("failed to store telemetry for %s: %s",
                         reading["sensor_id"], exc)
            return
        logger.info("stored telemetry: %s fill=%.1f%% mass=%.2fkg",
                    reading["sensor_id"], reading["fill_level_percent"],
                    reading["mass_kg"])
    else:
        # Cluster aggregates and facility dispatches have no storage table
        # yet; log receipt so the flow is observable.
        logger.info("received on %s (%d bytes) - no storage, logged only",
                    topic, len(msg.payload))


def on_connect(client: mqtt.Client, userdata, flags, rc, properties=None) -> None:  # noqa: ARG001
    if rc == 0:
        topics = os.environ.get("MQTT_TOPICS", ",".join(DEFAULT_TOPICS)).split(",")
        for topic in topics:
            topic = topic.strip()
            if topic:
                client.subscribe(topic)
                logger.info("subscribed to %s", topic)
    else:
        logger.error("MQTT connection failed with code %s", rc)


def _make_client() -> mqtt.Client:
    # paho-mqtt 2.x requires an explicit callback API version; 1.x takes none.
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
    except AttributeError:
        return mqtt.Client()


def main() -> int:
    logging.basicConfig(
        level=os.environ.get("MQTT_BRIDGE_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
        stream=sys.stderr,
    )
    broker = os.environ.get("MQTT_BROKER", "localhost")
    port = int(os.environ.get("MQTT_PORT", "1883"))

    ensure_schema()

    client = _make_client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.reconnect_delay_set(min_delay=1, max_delay=60)

    stop = False

    def _handle_signal(signum, frame):  # noqa: ARG001
        nonlocal stop
        stop = True
        client.disconnect()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    logger.info("connecting to MQTT broker %s:%d", broker, port)
    try:
        client.connect(broker, port, keepalive=60)
    except Exception as exc:  # noqa: BLE001
        logger.error("could not connect to broker: %s", exc)
        return 1
    client.loop_forever()
    return 0 if stop else 1


if __name__ == "__main__":
    raise SystemExit(main())
