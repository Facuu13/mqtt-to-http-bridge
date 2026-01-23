import json
import os
import time
from typing import Any, Dict, Optional

import requests
import paho.mqtt.client as mqtt


# MQTT
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "meters/+/telemetry")

# Legacy HTTP
LEGACY_URL = os.getenv("LEGACY_URL", "http://localhost:8080/ingest")
HTTP_TIMEOUT_S = float(os.getenv("HTTP_TIMEOUT_S", "5.0"))

MAX_RETRIES = int(os.getenv("MAX_RETRIES", "5"))
BACKOFF_BASE_S = float(os.getenv("BACKOFF_BASE_S", "1.0"))
BACKOFF_MAX_S = float(os.getenv("BACKOFF_MAX_S", "10.0"))

DLQ_PATH = os.getenv("DLQ_PATH", "failed.jsonl")

def write_dlq(data: dict, error: str) -> None:
    record = {
        "ts_dlq": int(time.time()),
        "error": error,
        "data": data,
    }
    with open(DLQ_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_message(topic: str, payload: bytes) -> Dict[str, Any]:
    """
    Convierte (topic, payload) a un dict normalizado para mandarlo al legacy.

    - topic esperado: meters/<device_id>/telemetry
    - payload esperado: JSON con device_id, type, value, unit, ts (ts opcional)
    """
    text = payload.decode("utf-8", errors="replace").strip()

    # Saco device_id del topic si viene con ese formato
    parts = topic.split("/")
    topic_device_id: Optional[str] = None
    if len(parts) >= 3 and parts[0] == "meters":
        topic_device_id = parts[1]

    # Intento parsear JSON
    try:
        obj = json.loads(text)
        if not isinstance(obj, dict):
            obj = {"raw": obj}
    except json.JSONDecodeError:
        obj = {"raw": text}

    device_id = obj.get("device_id") or topic_device_id or "unknown"
    ts = obj.get("ts") or int(time.time())

    out = {
        "device_id": device_id,
        "ts": ts,
        "reading": {
            "type": obj.get("type", "unknown"),
            "value": obj.get("value", obj.get("raw")),
            "unit": obj.get("unit"),
        },
        "meta": {
            "topic": topic,
        }
    }
    return out


def forward_to_legacy(data: dict) -> None:
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.post(LEGACY_URL, json=data, timeout=HTTP_TIMEOUT_S)

            # Si responde 4xx normalmente es error permanente (payload mal, auth, etc.)
            # 5xx suele ser transitorio (server caído / problema temporal)
            if 400 <= r.status_code < 500:
                r.raise_for_status()

            if r.status_code >= 500:
                raise requests.HTTPError(f"Legacy 5xx: {r.status_code} body={r.text[:200]}")

            return  # OK

        except Exception as e:
            last_err = e

            # Backoff exponencial con tope
            delay = min(BACKOFF_BASE_S * (2 ** (attempt - 1)), BACKOFF_MAX_S)
            print(
                f"[BRIDGE] WARN forward failed attempt={attempt}/{MAX_RETRIES} "
                f"delay={delay:.1f}s err={e}",
                flush=True,
            )
            time.sleep(delay)

    # Si llegamos acá, falló todo: DLQ
    write_dlq(data, error=str(last_err))
    raise RuntimeError(f"Forward failed after {MAX_RETRIES} attempts; sent to DLQ: {last_err}")



def on_connect(client, userdata, flags, reason_code, properties=None):
    print(f"[BRIDGE] Connected rc={reason_code}. Subscribing to {MQTT_TOPIC}", flush=True)
    client.subscribe(MQTT_TOPIC, qos=1)


def on_message(client, userdata, msg):
    try:
        normalized = parse_message(msg.topic, msg.payload)
        forward_to_legacy(normalized)
        print(f"[BRIDGE] OK device={normalized['device_id']} topic={msg.topic}", flush=True)
    except Exception as e:
        print(f"[BRIDGE] ERROR topic={msg.topic} err={e}", flush=True)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    print(f"[BRIDGE] Connecting to mqtt://{MQTT_HOST}:{MQTT_PORT} ...", flush=True)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_forever()


if __name__ == "__main__":
    main()
