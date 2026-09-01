# Aureon root image: isolated terminal protection preflight only.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

RUN groupadd -r aureon && useradd -r -g aureon aureon
WORKDIR /app
COPY --chown=aureon:aureon scripts/bootstrap/protected_bootstrap_v05.py /app/scripts/bootstrap/protected_bootstrap_v05.py
USER aureon

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=1 \
    CMD /usr/local/bin/python -I -S -B /app/scripts/bootstrap/protected_bootstrap_v05.py --target-id docker-runtime

ENTRYPOINT ["/usr/local/bin/python", "-I", "-S", "-B", "/app/scripts/bootstrap/protected_bootstrap_v05.py", "--target-id", "docker-runtime"]
CMD []
