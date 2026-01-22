import json
import time
import random
import paho.mqtt.client as mqtt


BROKER_HOST = "localhost"
BROKER_PORT = 1883

DEVICE_ID = "meter-001"
TOPIC = f"meters/{DEVICE_ID}/telemetry"


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=30)
    client.loop_start()

    seq = 0
    try:
        while True:
            seq += 1
            payload = {
                "device_id": DEVICE_ID,
                "type": "water",
                "value": round(random.uniform(0, 50), 2),
                "unit": "L/min",
                "ts": int(time.time()),
                "seq": seq,
            }

            client.publish(TOPIC, json.dumps(payload), qos=1)
            print(f"[DEVICE] published topic={TOPIC} payload={payload}", flush=True)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n[DEVICE] stopping...", flush=True)
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
