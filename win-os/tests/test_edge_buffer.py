import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "edge"))
import mqtt_bridge as bridge

def test_buffer_roundtrip(tmp_path):
    conn = bridge.buffer_init(str(tmp_path / "b.db"))
    bridge.buffer_put(conn, {"device_id": "d1", "client_event_id": "e1"})
    rows = bridge.buffer_peek(conn)
    assert len(rows) == 1 and rows[0][1]["device_id"] == "d1"
    bridge.buffer_drop(conn, [rows[0][0]])
    assert bridge.buffer_peek(conn) == []

def test_handle_message_drops_unidentifiable(tmp_path):
    conn = bridge.buffer_init(str(tmp_path / "b.db"))
    assert bridge.handle_message(conn, "win/telemetry/d1", b"not json") == "dropped:unparseable"
    assert bridge.handle_message(conn, "win/telemetry/d1", b'{"device_id":"d1"}') == "dropped:missing-idempotency-fields"
    assert bridge.buffer_peek(conn) == []
