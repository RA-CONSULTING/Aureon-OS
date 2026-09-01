# Aureon production image: isolated terminal protection preflight.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8

RUN groupadd -r aureon && useradd -r -g aureon aureon
WORKDIR /aureon/app
COPY --chown=aureon:aureon scripts/bootstrap/protected_bootstrap_v05.py /aureon/app/scripts/bootstrap/protected_bootstrap_v05.py
USER aureon

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=1 \
    CMD /usr/local/bin/python -I -S -B /aureon/app/scripts/bootstrap/protected_bootstrap_v05.py --target-id production-supervisor

ENTRYPOINT ["/usr/local/bin/python", "-I", "-S", "-B", "/aureon/app/scripts/bootstrap/protected_bootstrap_v05.py", "--target-id", "production-supervisor"]
CMD []
