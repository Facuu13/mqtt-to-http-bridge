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

## Roadmap (incremental)

### Etapa 1 — Setup reproducible (Docker + scripts)
- [ ] Broker Mosquitto en Docker
- [ ] Legacy receiver (Flask)
- [ ] Bridge subscriber (paho-mqtt + requests)
- [ ] Device simulator (publisher)

### Etapa 2 — Robustez “de producción”
- [ ] Retries con backoff en forward HTTP
- [ ] Dead-letter queue (DLQ) a archivo `failed.jsonl`
- [ ] Logs estructurados (niveles, contexto)
- [ ] Validación estricta de esquema (opcional)

### Etapa 3 — Calidad y testing
- [ ] Tests unitarios de parsing (pytest)
- [ ] Tests de integración (publicar MQTT y validar recepción legacy)
- [ ] Lint/format (ruff/black)

### Etapa 4 — Variantes de salida legacy
- [ ] Forward por HTTP a script PHP real
- [ ] Escritura a archivo CSV/JSONL para consumo batch
- [ ] Ejecución de script externo (subprocess) para integraciones puntuales

---

