# Aureon root image: guarded non-live preflight.
# The entrypoint is the isolated bootstrap. It returns HOLD and does not import
# the docker-runtime target. No listener is declared. This image is not a
# supported cloud go-live, is not production ready, and is not a validation.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    AUREON_AUTONOMY_MODE=guarded \
    AUREON_LIVE_TRADING=0 \
    AUREON_LLM_OFFLINE=1 \
    AUREON_DISABLE_LLM_HTTP=1 \
    AUREON_DISABLE_REAL_ORDERS=1 \
    AUREON_DISABLE_EXCHANGE_MUTATIONS=1

LABEL org.opencontainers.image.title="Aureon guarded preflight" \
      org.opencontainers.image.description="Isolated HOLD preflight. Not production ready. Not a supported cloud go-live. No listener." \
      org.opencontainers.image.source="https://github.com/RA-CONSULTING/Aureon-OS" \
      aureon.release-boundary="HOLD" \
      aureon.go-live="HOLD" \
      aureon.production-ready="false" \
      aureon.validation-claim="none"

RUN groupadd -r aureon && useradd -r -g aureon aureon
WORKDIR /app
COPY --chown=aureon:aureon scripts/bootstrap/protected_bootstrap_v05.py /app/scripts/bootstrap/protected_bootstrap_v05.py
USER aureon

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=1 \
    CMD /usr/local/bin/python -I -S -B /app/scripts/bootstrap/protected_bootstrap_v05.py --target-id docker-runtime

ENTRYPOINT ["/usr/local/bin/python", "-I", "-S", "-B", "/app/scripts/bootstrap/protected_bootstrap_v05.py", "--target-id", "docker-runtime"]
CMD []
