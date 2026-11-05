# Optional container for the same process ./install.sh starts.
# Build context is deploy/plug/image, produced by scripts/stage_plug_image.py.
# The documented command is ./install.sh. This image is the container form.
FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/aureon

COPY requirements-plug.lock /opt/aureon/requirements-plug.lock
RUN pip install --no-cache-dir -r /opt/aureon/requirements-plug.lock

COPY . /opt/aureon
RUN cd /opt/aureon/frontend && npm ci --ignore-scripts

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/aureon:/opt/aureon/mcp \
    AUREON_PLUG_AND_PLAY=1 \
    AUREON_LLM_OFFLINE=1 \
    AUREON_SUPPRESS_IMPORT_SIDE_EFFECTS=1 \
    AUREON_LIVE_TRADING=0 \
    AUREON_DISABLE_REAL_ORDERS=1 \
    AUREON_DISABLE_EXCHANGE_MUTATIONS=1 \
    AUREON_FUSION_ARM_LIVE= \
    AUREON_AUTONOMY_MODE=guarded \
    AUREON_OPERATOR_ENV=development \
    AUREON_OPERATOR_HOST=127.0.0.1 \
    AUREON_OPERATOR_PORT=8790 \
    AUREON_PUBLIC_OPEN=1

EXPOSE 8787 8790 8077 5173

HEALTHCHECK --interval=5s --timeout=5s --start-period=40s --retries=20 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/healthz', timeout=3)"

CMD ["python", "scripts/plug_and_play.py"]
