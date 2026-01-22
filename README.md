### Entregable 0 — “Contrato” del dato (muy corto, pero clave)

**Output:** `docs/message_contract.md`

* Definir 1 formato de salida canónico (ej: JSON).
* Campos mínimos:

  * `device_id` (string)
  * `ts` (unix o ISO8601)
  * `metrics` (objeto: kWh, litros, voltage, etc.)
  * `raw` (payload original opcional)
  * `topic` (de dónde vino)
* Definir qué pasa si faltan campos (rechazo vs default).

> Esto te evita rehacer todo cuando cambie el payload.

---

### Entregable 1 — Proyecto base ejecutable

**Output:**

* `README.md` (cómo correrlo)
* `requirements.txt`
* `src/bridge.py` (con CLI mínima)

Funcionalidad:

* Script corre local.
* Lee config (env o yaml/json).
* Loggea “up” + config validada.

---

### Entregable 2 — Subscriber MQTT mínimo (solo recibe y loggea)

**Output:**

* `src/mqtt_client.py`
* `src/bridge.py` (conecta y subscribe)

Funcionalidad:

* Conecta a un broker (host/port/user/pass).
* Se subscribe a `topic/#` configurable.
* Por cada mensaje imprime:

  * topic, timestamp, payload raw (limitado), tamaño.

✅ Criterio de “listo”: “veo mensajes llegar de forma estable”.

---

### Entregable 3 — Parser + normalización (core del laburo)

**Output:**

* `src/parser.py`
* `tests/test_parser.py` (aunque sean 5 tests)

Funcionalidad:

* Soportar **JSON** primero (probable).
* Detectar device_id:

  * desde el payload **o** desde el topic (ej: `meters/<id>/up`).
* Produce el “canonical event” (el contrato del Entregable 0).

✅ Criterio de “listo”: “de 10 mensajes, 10 salen normalizados”.

---

### Entregable 4 — Forwarder HTTP al server legacy

**Output:**

* `src/forwarder.py`
* `src/bridge.py` (pipeline completo)

Funcionalidad:

* POST a `http://legacy-server/ingest.php` (o endpoint que sea).
* Enviar JSON normalizado.
* Timeouts + retries simples (ej: 3 reintentos, backoff).
* Si falla, **no pierde el mensaje**: lo guarda en spool local.

✅ Criterio de “listo”: si Apache está caído, el sistema sigue y reintenta.

---

### Entregable 5 — Spool persistente + modo “replay”

**Output:**

* `data/spool/` (directorio)
* `src/spool.py`
* comando: `python -m src.bridge replay`

Funcionalidad:

* Si no puede forwardear → guarda evento en disco (json lines).
* Un modo replay reenvía lo pendiente.
* Métrica simple: cuántos pendientes quedan.

---

### Entregable 6 — Operación (para que sea deployable)

**Output:**

* `systemd/mqtt-bridge.service` (si va en Linux)
* `config/config.example.json`
* logs rotativos o al menos logging consistente

Funcionalidad:

* Corre como servicio.
* Logs claros + niveles.
* Un “healthcheck” básico (endpoint local opcional o log “alive”).

---

## 3) Estructura sugerida del repo

```
mqtt-to-http-bridge/
  README.md
  requirements.txt
  config/
    config.example.json
  docs/
    message_contract.md
  src/
    bridge.py
    mqtt_client.py
    parser.py
    forwarder.py
    spool.py
    utils.py
  tests/
    test_parser.py
  systemd/
    mqtt-bridge.service
  data/
    spool/
```

---



Si querés, en el próximo paso te escribo **el README inicial + el esqueleto del proyecto (bridge.py + config.example.json)** para que ya lo puedas commitear y correr en local en 5 minutos.
