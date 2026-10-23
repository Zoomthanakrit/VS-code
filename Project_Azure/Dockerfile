# Match Story - container image for Azure Container Apps
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 HOST=0.0.0.0 PORT=8000

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code + the synthetic match + tracking data + pre-made AI cards (so the demo is instant and cheap)
COPY src/ src/
COPY data/*.jsonl data/
COPY data/cache/ data/cache/

# Run as a normal user, not root
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["python", "src/app.py"]
