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

# CPU-first by default so the public console, HNC evidence, and the repository
# tree are served on free cpu-basic hardware with no GPU dependency. The GPU
# image remains available for inference: build with
#   docker build -f deploy/huggingface/Dockerfile.gpu .
# or set AUREON_SPACE_TORCH to a CUDA wheel index and install torch afterwards.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      bash nginx redis-server supervisor postgresql postgresql-client git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# NGC already provides an unprivileged user at UID 1000.
RUN useradd --create-home --uid 10001 aureon
WORKDIR /app/aureon-os
COPY --chown=aureon:aureon . /app/aureon-os
COPY --from=frontend-build --chown=aureon:aureon /build/frontend/dist /app/aureon-os/frontend/dist

# The CPU wheel index keeps this image small: no CUDA runtime is pulled for a
# Space that serves the console without a GPU. The pinned model-loading versions
# match the validated Isambard container.
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel \
 && python -m pip install --no-cache-dir \
      --index-url https://download.pytorch.org/whl/cpu \
      torch==2.6.0 \
 && python -m pip install --no-cache-dir \
      -r requirements-linux.txt \
      transformers==4.57.6 \
      safetensors==0.8.0 \
      tokenizers==0.22.2 \
      huggingface_hub==0.36.2 \
      httpx jsonschema waitress

# python:3.12-slim already provides /usr/local/bin/python, which supervisord and
# the model launcher both call by absolute path. Proving the interpreter works is
# still required, so a broken image fails at build time rather than at boot.
RUN test -x /usr/local/bin/python \
 && /usr/local/bin/python -c "import sys; print('python', sys.version.split()[0])"

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
