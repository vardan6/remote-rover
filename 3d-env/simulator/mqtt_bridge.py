"""
mqtt_bridge.py -- MQTT runtime bridge for simulator control and telemetry.
"""

from __future__ import annotations

import json
import threading
import time
import uuid

try:
    import paho.mqtt.client as mqtt
except Exception:  # pragma: no cover - optional dependency at import time
    mqtt = None


def _topic_join(prefix: str, leaf: str) -> str:
    p = (prefix or "").strip().rstrip("/")
    l = (leaf or "").strip().strip("/")
    if p and l:
        return f"{p}/{l}"
    return p or l


class MQTTBridge:
    def __init__(self, mqtt_cfg: dict):
        self._cfg = dict(mqtt_cfg or {})
        self._lock = threading.Lock()
        self._client = None
        self._running = False
        self._status = "disabled"
        self._latest_control = None
        self._latest_rx_mono = 0.0

    def start(self):
        if mqtt is None:
            self._status = "unavailable"
            print("[MQTT] paho-mqtt is not installed. MQTT bridge disabled.")
            return
        if self._running:
            return

        self._status = "connecting"
        client_id = (self._cfg.get("client_id") or "").strip()
        if not client_id:
            client_id = f"sim-{uuid.uuid4().hex[:10]}"

        self._client = mqtt.Client(client_id=client_id, clean_session=True)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        # Keep reconnect retries quiet but resilient if broker drops.
        self._client.reconnect_delay_set(min_delay=5, max_delay=30)

        host = str(self._cfg["broker_host"]).strip()
        port = int(self._cfg["broker_port"])
        try:
            self._client.connect_async(host, port, keepalive=30)
            self._client.loop_start()
            self._running = True
        except Exception as exc:
            self._status = f"error ({exc})"
            print(f"[MQTT] Connect failed: {exc}")

    def stop(self):
        if not self._running:
            return
        self._running = False
        try:
            if self._client is not None:
                self._client.loop_stop()
                self._client.disconnect()
        except Exception:
            pass
        self._status = "stopped"

    def status_text(self) -> str:
        return self._status

    def _on_connect(self, client, _userdata, _flags, rc):
        if rc == 0:
            self._status = "connected"
            control_topic = _topic_join(
                self._cfg["topic_prefix"],
                self._cfg["control_topic"],
            )
            try:
                client.subscribe(control_topic, qos=0)
                print(f"[MQTT] Subscribed: {control_topic}")
            except Exception as exc:
                self._status = f"subscribe error ({exc})"
                print(f"[MQTT] Subscribe failed: {exc}")
        else:
            self._status = f"connect failed (rc={rc})"

    def _on_disconnect(self, _client, _userdata, rc):
        if not self._running:
            return
        self._status = "reconnecting" if rc != 0 else "disconnected"

    def _on_message(self, _client, _userdata, msg):
        try:
            payload = msg.payload.decode("utf-8", errors="replace")
            frame = json.loads(payload)
            if not isinstance(frame, dict):
                return
        except Exception:
            return

        with self._lock:
            self._latest_control = frame
            self._latest_rx_mono = time.monotonic()

    def get_control_frame(self, timeout_s: float):
        now = time.monotonic()
        with self._lock:
            frame = self._latest_control
            rx = self._latest_rx_mono
        if frame is None:
            return None, None
        age = now - rx
        if age > timeout_s:
            return None, age
        return frame, age

    def publish_state(self, state_payload: dict):
        if not self._running or self._client is None:
            return
        topic = _topic_join(
            self._cfg["topic_prefix"],
            self._cfg["state_topic"],
        )
        try:
            payload = json.dumps(state_payload, separators=(",", ":"))
            self._client.publish(topic, payload=payload, qos=0, retain=False)
        except Exception:
            pass

    def publish_camera_frame(self, frame_bytes: bytes):
        if not self._running or self._client is None or not frame_bytes:
            return
        topic = _topic_join(
            self._cfg["topic_prefix"],
            self._cfg["camera_topic"],
        )
        try:
            self._client.publish(topic, payload=frame_bytes, qos=0, retain=False)
        except Exception:
            pass
