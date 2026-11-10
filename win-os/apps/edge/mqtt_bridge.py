"""WIN Edge MQTT bridge: device telemetry -> WIN API, with local
store-and-forward. Runs on a depot/gateway host (WIN Edge profile).

Behaviour:
- Subscribes to win/telemetry/<device_id> on the local Mosquitto broker.
- Each message must be a telemetry event JSON (see
  data-platform/event-contracts/telemetry-event.schema.json) and must carry
  a client_event_id; messages without one are dropped and logged, because
  idempotency is what makes offline replay safe.
- Events are posted to the WIN API in batches. When the API is unreachable,
  events are buffered in a local SQLite file and flushed in order when the
  API returns (buffered_offline is set true for anything that waited).
- This bridge transports data; it never invents it. No event is created
  locally except the transport metadata above.

Requires: paho-mqtt, httpx (win-os/apps/edge/requirements.txt).
Config (env): WIN_API_URL, WIN_API_KEY (an 'integration' role key),
MQTT_HOST, MQTT_PORT, WIN_EDGE_BUFFER (default ./edge-buffer.db).
"""
from __future__ import annotations
import json, os, sqlite3, sys, time

API_URL = os.environ.get("WIN_API_URL", "http://127.0.0.1:8080")
API_KEY = os.environ.get("WIN_API_KEY", "")
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
BUFFER = os.environ.get("WIN_EDGE_BUFFER", "./edge-buffer.db")

def buffer_init(path: str = BUFFER):
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS buffer "
                 "(id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL)")
    conn.commit()
    return conn

def buffer_put(conn, event: dict) -> None:
    conn.execute("INSERT INTO buffer (payload) VALUES (?)", (json.dumps(event),))
    conn.commit()

def buffer_peek(conn, limit: int = 100) -> list[tuple[int, dict]]:
    rows = conn.execute("SELECT id, payload FROM buffer ORDER BY id LIMIT ?",
                        (limit,)).fetchall()
    return [(r[0], json.loads(r[1])) for r in rows]

def buffer_drop(conn, ids: list[int]) -> None:
    conn.executemany("DELETE FROM buffer WHERE id = ?", [(i,) for i in ids])
    conn.commit()

def post_events(events: list[dict]) -> bool:
    import httpx
    try:
        resp = httpx.post(f"{API_URL}/api/v1/telemetry/events",
                          headers={"X-API-Key": API_KEY},
                          json={"events": events}, timeout=15.0)
        return resp.status_code in (200, 201)
    except Exception:
        return False

def flush_buffer(conn) -> int:
    sent = 0
    while True:
        batch = buffer_peek(conn)
        if not batch:
            return sent
        events = []
        for _id, ev in batch:
            ev = dict(ev)
            ev["buffered_offline"] = True
            events.append(ev)
        if not post_events(events):
            return sent
        buffer_drop(conn, [i for i, _ in batch])
        sent += len(batch)

def handle_message(conn, topic: str, payload: bytes) -> str:
    try:
        event = json.loads(payload.decode("utf-8"))
    except Exception:
        return "dropped:unparseable"
    if not event.get("client_event_id") or not event.get("device_id"):
        return "dropped:missing-idempotency-fields"
    event.setdefault("data_status", "observed")
    buffer_put(conn, event)
    flush_buffer(conn)
    return "buffered-and-flushed" if not buffer_peek(conn, 1) else "buffered"

def main() -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        sys.exit("paho-mqtt is required: pip install -r win-os/apps/edge/requirements.txt")
    if not API_KEY:
        sys.exit("WIN_API_KEY must be set to an integration-role API key.")
    conn = buffer_init()

    def on_message(client, userdata, msg):
        result = handle_message(conn, msg.topic, msg.payload)
        print(f"edge-bridge topic={msg.topic} result={result}", flush=True)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_message
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    client.subscribe("win/telemetry/#")
    print(f"edge-bridge subscribed win/telemetry/# via {MQTT_HOST}:{MQTT_PORT} "
          f"-> {API_URL}", flush=True)
    while True:
        client.loop(timeout=1.0)
        flush_buffer(conn)
        time.sleep(5)

if __name__ == "__main__":
    main()
