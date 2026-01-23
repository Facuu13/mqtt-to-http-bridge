FROM python:3.12-slim

WORKDIR /app

# Dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY bridge.py .

# (Opcional) si tenés core.py u otros, los copiás también
# COPY core.py .

ENV PYTHONUNBUFFERED=1

CMD ["python", "bridge.py"]
