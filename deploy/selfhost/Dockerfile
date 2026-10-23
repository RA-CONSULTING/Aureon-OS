FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    AUREON_LIVE_TRADING=0 \
    AUREON_FUSION_ARM_LIVE=

WORKDIR /app
RUN pip install --no-cache-dir redis \
    && mkdir -p /var/log/aureon
COPY aureon_fusion /app/aureon_fusion
COPY aureon /app/aureon
COPY organism /app/organism
COPY error_sink.py /app/error_sink.py

EXPOSE 8765
CMD ["python", "-m", "aureon_fusion.http_service"]
