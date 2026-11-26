FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN grep -v '^sentence-transformers' requirements.txt > /tmp/requirements-docker.txt && \
    pip install --no-cache-dir -r /tmp/requirements-docker.txt && \
    rm -f /tmp/requirements-docker.txt

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
