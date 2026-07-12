# ═══════════════════════════════════════════════════════════════════════════
# 🎮👑 AUREON TRADING SYSTEM - PRODUCTION DOCKER IMAGE 👑🎮
# ═══════════════════════════════════════════════════════════════════════════
# Sandboxed, isolated trading environment
# Build: docker build -t aureon-trading:latest -f production/Dockerfile .
# Run:   docker run -it --name aureon -p 8888:8888 aureon-trading:latest
# ═══════════════════════════════════════════════════════════════════════════

FROM python:3.12-slim AS builder

# Build args
ARG BUILD_DATE
ARG VERSION=1.0.0

# Labels
LABEL org.opencontainers.image.title="AUREON Trading System"
LABEL org.opencontainers.image.description="Quantum Trading System - Production Build"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.authors="RA-CONSULTING"

# Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    AUREON_HOME=/aureon \
    AUREON_DATA=/aureon/data \
    AUREON_LOGS=/aureon/logs \
    AUREON_CONFIG=/aureon/config

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    git \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy requirements first for caching
COPY requirements.txt ./
COPY production/requirements-prod.txt ./

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install -r requirements-prod.txt

# ═══════════════════════════════════════════════════════════════════════════
# Production image
# ═══════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    AUREON_HOME=/aureon \
    AUREON_DATA=/aureon/data \
    AUREON_LOGS=/aureon/logs \
    AUREON_CONFIG=/aureon/config \
    AUREON_MODE=production

# Install curl for healthcheck and supervisor for process management
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Create aureon user (non-root for security)
RUN groupadd -r aureon && useradd -r -g aureon aureon

# Create directories
RUN mkdir -p /aureon /aureon/data /aureon/logs /aureon/config && \
    chown -R aureon:aureon /aureon

WORKDIR /aureon

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=aureon:aureon . /aureon/app/

# Copy production entrypoint and supervisor config
COPY --chown=aureon:aureon production/entrypoint.sh /aureon/entrypoint.sh
COPY --chown=aureon:aureon production/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
RUN chmod +x /aureon/entrypoint.sh && \
    mkdir -p /aureon/config/supervisor.d

# Health check - test the new health check server on port 8080
# Initial delay of 120s to allow supervisor and all services to start
# Interval of 30s, timeout 5s, retries 5 (fail after 5 consecutive failures)
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose ports
# 8888 - Command Center UI
# 8889 - API Gateway
# 9090 - Metrics/Prometheus
EXPOSE 8888 8889 9090

# Switch to non-root user
USER aureon

# Volumes for persistent data
VOLUME ["/aureon/data", "/aureon/logs", "/aureon/config"]

# Entrypoint
ENTRYPOINT ["/aureon/entrypoint.sh"]
CMD ["--mode", "game"]
