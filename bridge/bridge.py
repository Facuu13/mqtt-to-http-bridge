import json
import os
import time
from typing import Any, Dict, Optional

import requests
import paho.mqtt.client as mqtt

from datetime import datetime


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


class InvalidPayload(Exception):
    pass

def validate_normalized(data: dict) -> None:
    if not isinstance(data.get("device_id"), str) or not data["device_id"]:
        raise InvalidPayload("device_id inválido")

    if not isinstance(data.get("ts"), int):
        raise InvalidPayload("ts debe ser int (epoch)")

    reading = data.get("reading")
    if not isinstance(reading, dict):
        raise InvalidPayload("reading debe ser objeto")

    if not isinstance(reading.get("type"), str):
        raise InvalidPayload("reading.type inválido")

    value = reading.get("value")
    if not isinstance(value, (int, float)):
        raise InvalidPayload("reading.value debe ser numérico")


def log(level: str, event: str, **ctx):
    # ISO time (UTC) para que sea consistente en todos lados
    ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    # Formato "key=value" (simple, legible, parseable)
    ctx_str = " ".join(f"{k}={repr(v)}" for k, v in ctx.items())

    if ctx_str:
        print(f"{ts} [{level}] {event} {ctx_str}", flush=True)
    else:
        print(f"{ts} [{level}] {event}", flush=True)

def log_info(event: str, **ctx): log("INFO", event, **ctx)
def log_warn(event: str, **ctx): log("WARN", event, **ctx)
def log_error(event: str, **ctx): log("ERROR", event, **ctx)


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
            log_warn(
                "legacy_forward_retry",
                attempt=attempt,
                max_retries=MAX_RETRIES,
                delay_s=round(delay, 2),
                err=str(e),
                device_id=data.get("device_id"),
                )

            time.sleep(delay)

    log_error(
        "sent_to_dlq",
        dlq_path=DLQ_PATH,
        device_id=data.get("device_id"),
        err=str(last_err),
    )

    write_dlq(data, error=str(last_err))
    raise RuntimeError(f"Forward failed after {MAX_RETRIES} attempts; sent to DLQ: {last_err}")



def on_connect(client, userdata, flags, reason_code, properties=None):
    log_info("mqtt_connected", rc=reason_code, topic=MQTT_TOPIC, host=MQTT_HOST, port=MQTT_PORT)
    client.subscribe(MQTT_TOPIC, qos=1)



def on_message(client, userdata, msg):
    try:
        normalized = parse_message(msg.topic, msg.payload)

        # ⬅ VALIDACIÓN
        validate_normalized(normalized)

        forward_to_legacy(normalized)

        log_info(
            "forward_ok",
            device_id=normalized["device_id"],
            topic=msg.topic,
            value=normalized["reading"]["value"],
        )

    except InvalidPayload as e:
        log_error(
            "invalid_payload_dlq",
            topic=msg.topic,
            err=str(e),
        )
        write_dlq(
            normalized if "normalized" in locals() else {"raw": msg.payload.decode()},
            error=str(e),
        )

    except Exception as e:
        log_error("forward_failed", topic=msg.topic, err=str(e))




def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message

    log_info("bridge_start", mqtt_host=MQTT_HOST, mqtt_port=MQTT_PORT, topic=MQTT_TOPIC, legacy_url=LEGACY_URL)
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=30)
    client.loop_forever()


if __name__ == "__main__":
    main()
