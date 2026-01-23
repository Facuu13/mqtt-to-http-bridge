# MQTT → Legacy Bridge (Python)

Este proyecto implementa un **bridge liviano** que toma datos publicados por dispositivos vía **MQTT** (por ejemplo medidores de agua/electricidad), los **parsea/normaliza** y los **reenvía** a un “sistema legacy” que **no habla MQTT** (por ejemplo un stack LAMP viejo con scripts en PHP/Apache).

La idea es replicar un escenario típico real: los dispositivos envían telemetría por MQTT a un broker, pero el servidor legacy solo puede consumir datos por mecanismos simples (HTTP, archivos, ejecución de scripts).

---

## Objetivo

- Recibir mensajes MQTT desde uno o varios *topics*.
- Extraer campos clave (por ejemplo `device_id`, `value`, `type`, `ts`).
- Normalizar el payload a un formato consistente (*legacy-friendly*).
- Forward de ese contenido a un receptor legacy (en el MVP: un endpoint HTTP que simula un script PHP).

---

## Arquitectura (MVP)

[Device MQTT] -> [MQTT Broker (Mosquitto)] -> [Bridge Python Subscriber] -> [Legacy Receiver (HTTP/PHP-like)]


Componentes:
- **Mosquitto**: broker MQTT mínimo (Docker).
- **Device simulator**: script Python que publica telemetría (simula medidores).
- **Bridge**: servicio Python que se subscribe, parsea y reenvía.
- **Legacy receiver**: endpoint HTTP (Flask) que simula un “script legacy” receptor.

---

## ¿Por qué hace falta un broker?

MQTT es un protocolo *pub/sub* y normalmente requiere un broker (Mosquitto, EMQX, HiveMQ, etc.).  
Lo que se evita en este proyecto no es el broker (que puede ser liviano), sino montar una plataforma completa con reglas complejas, múltiples servicios o un backend moderno grande. Este bridge es la “pieza intermedia” para que un sistema antiguo pueda integrarse sin migrarlo.

---

## Funcionalidades (MVP)

- Suscripción a un patrón de topics (ej: `meters/+/telemetry`).
- Parsing de payload en JSON (con fallback simple si viene texto plano).
- Normalización a un esquema consistente:
  - `device_id`
  - `ts`
  - `reading: { type, value, unit }`
  - `meta: { topic }`
- Forward a un endpoint HTTP (`POST /ingest`).

---


## ▶️ Quickstart — Run with one command

Este proyecto puede ejecutarse **completamente con Docker Compose**, sin necesidad de instalar Python, MQTT ni dependencias adicionales en el host (excepto Docker).

### Requisitos

* Docker
* Docker Compose (plugin `docker compose`)

---

### 1️⃣ Levantar todos los servicios

Desde la raíz del repositorio:

```bash
cd docker
docker compose up --build
```

Esto levanta automáticamente:

* **Mosquitto** (broker MQTT) en `localhost:1883`
* **Legacy receiver** (simula un sistema legacy PHP/LAMP) en `localhost:8080`
* **Bridge** (MQTT → HTTP forwarder con retries, DLQ y logs)

---

### 2️⃣ Publicar un mensaje de prueba (sin Python)

En otra terminal, ejecutá:

```bash
docker run --rm --network host eclipse-mosquitto:2 \
  mosquitto_pub \
  -h localhost -p 1883 \
  -t "meters/meter-001/telemetry" \
  -m '{"device_id":"meter-001","type":"water","value":12.3,"unit":"L/min","ts":1700000000}'
```

---

### 3️⃣ Verificar el flujo end-to-end

Si todo está funcionando correctamente, deberías ver:

#### En los logs del **bridge**:

```
[INFO] mqtt_connected ...
[INFO] forward_ok device_id='meter-001' ...
```

#### En los logs del **legacy**:

```
[LEGACY] received: {'device_id': 'meter-001', ...}
```

Esto confirma que:

```
MQTT → Bridge → Legacy
```

funciona correctamente.

---

### 4️⃣ Probar tolerancia a fallos (DLQ)

1. Detené el legacy:

```bash
docker stop legacy
```

2. Volvé a publicar un mensaje MQTT.

3. El bridge va a:

* reintentar con backoff
* registrar errores
* guardar el mensaje en el DLQ

El archivo DLQ queda en:

```
docker/data/failed.jsonl
```

Cada línea corresponde a un mensaje que no pudo ser entregado.

---

### 5️⃣ Volver a levantar el legacy

```bash
docker start legacy
```

---

## 🧹 Apagar todo

Para detener los servicios:

```bash
docker compose down
```

---


