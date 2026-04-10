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
        self._gcs_presence: dict[str, dict[str, float | bool]] = {}

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
            presence_topic = self._presence_topic_filter()
            try:
                client.subscribe(control_topic, qos=0)
                print(f"[MQTT] Subscribed: {control_topic}")
                client.subscribe(presence_topic, qos=0)
                print(f"[MQTT] Subscribed: {presence_topic}")
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
        control_topic = _topic_join(
            self._cfg["topic_prefix"],
            self._cfg["control_topic"],
        )
        if msg.topic == control_topic:
            self._handle_control_message(msg)
            return
        if self._is_presence_topic(msg.topic):
            self._handle_presence_message(msg)

    def _handle_control_message(self, msg):
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

    def _handle_presence_message(self, msg):
        try:
            payload = msg.payload.decode("utf-8", errors="replace")
            frame = json.loads(payload)
            if not isinstance(frame, dict):
                return
        except Exception:
            return

        gcs_id = str(frame.get("gcs_id") or self._presence_topic_suffix(msg.topic)).strip()
        if not gcs_id:
            return
        active = bool(frame.get("active", True))
        try:
            timestamp = float(frame.get("timestamp", 0.0))
        except Exception:
            timestamp = 0.0

        with self._lock:
            self._gcs_presence[gcs_id] = {
                "active": active,
                "timestamp": timestamp,
            }

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

    def has_active_gcs(self, timeout_s: float) -> bool:
        return self.active_gcs_count(timeout_s) > 0

    def active_gcs_count(self, timeout_s: float) -> int:
        now = time.time()
        timeout_s = max(0.0, float(timeout_s))
        active_count = 0
        with self._lock:
            entries = list(self._gcs_presence.values())
        for entry in entries:
            if not bool(entry.get("active")):
                continue
            timestamp = float(entry.get("timestamp", 0.0) or 0.0)
            if timestamp <= 0.0:
                continue
            if now - timestamp <= timeout_s:
                active_count += 1
        return active_count

    def _presence_topic_filter(self) -> str:
        base = _topic_join(
            self._cfg.get("topic_prefix", ""),
            self._cfg.get("gcs_presence_topic", "gcs/presence"),
        ).rstrip("/")
        return f"{base}/+"

    def _presence_topic_base(self) -> str:
        return _topic_join(
            self._cfg.get("topic_prefix", ""),
            self._cfg.get("gcs_presence_topic", "gcs/presence"),
        ).rstrip("/")

    def _is_presence_topic(self, topic: str) -> bool:
        base = self._presence_topic_base()
        return bool(base) and topic.startswith(f"{base}/")

    def _presence_topic_suffix(self, topic: str) -> str:
        base = self._presence_topic_base()
        if not base or not topic.startswith(f"{base}/"):
            return ""
        return topic[len(base) + 1 :].strip("/")
