from flask import Flask, request, jsonify
import time

app = Flask(__name__)

@app.post("/ingest")
def ingest():
    data = request.get_json(force=True, silent=False)
    print(f"[LEGACY] {int(time.time())} received: {data}", flush=True)
    return jsonify({"ok": True})

@app.get("/health")
def health():
    return jsonify({"status": "up"})

if __name__ == "__main__":
    # Escucha en todas las interfaces dentro del container
    app.run(host="0.0.0.0", port=8080)
