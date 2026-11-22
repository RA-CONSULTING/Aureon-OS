# Aureon OS public Hugging Face GPU Space.
# Build from the repository root:
#   docker build -f deploy/huggingface/Dockerfile .
# Space publication uploads this same file as the Space-root Dockerfile.

FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --ignore-scripts --no-audit --no-fund
COPY frontend/ ./
RUN npm run typecheck && npm run lint:shell && npm run build

# The validated Isambard runtime used the same NGC 25.05 Torch/CUDA generation.
# Transformers and the Hub client are pinned independently below.
FROM nvcr.io/nvidia/pytorch:25.05-py3

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bash nginx redis-server supervisor postgresql postgresql-client git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 aureon
WORKDIR /app/aureon-os
COPY --chown=aureon:aureon . /app/aureon-os
COPY --from=frontend-build --chown=aureon:aureon /build/frontend/dist /app/aureon-os/frontend/dist

# Do not reinstall or downgrade the NGC CUDA/Torch build. The remaining set is
# the repository's headless-Linux runtime plus the exact model-loading versions
# observed in the real Isambard validation container.
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
 && python -m pip install --no-cache-dir \
      -r requirements-linux.txt \
      transformers==4.57.6 \
      safetensors==0.8.0 \
      tokenizers==0.22.2 \
      huggingface_hub==0.36.2 \
      httpx jsonschema waitress

RUN mkdir -p /app/aureon-os/runtime /app/aureon-os/runtime/home \
 && chown -R aureon:aureon /app/aureon-os/runtime \
 && chmod +x \
      /app/aureon-os/deploy/huggingface/entrypoint.sh \
      /app/aureon-os/deploy/huggingface/model_service.sh

USER aureon
ENV HOME=/app/aureon-os/runtime/home

EXPOSE 7860
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=1800s --retries=5 \
    CMD python -c "import http.client; c=http.client.HTTPConnection('127.0.0.1', 7860, timeout=4); c.request('GET', '/healthz'); r=c.getresponse(); r.read(); assert r.status == 200" || exit 1

ENTRYPOINT ["/bin/bash", "/app/aureon-os/deploy/huggingface/entrypoint.sh"]
