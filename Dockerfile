FROM python:3.11-slim

WORKDIR /app

# Install dependencies first so this layer is cached between code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY personio_export/ ./personio_export/
COPY run_export.py .

# config.yaml and the output folder are provided at runtime via a volume,
# so credentials are never baked into the image.
ENTRYPOINT ["python", "run_export.py"]
