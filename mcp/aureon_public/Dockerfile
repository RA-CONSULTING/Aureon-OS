# Hugging Face Space scaffold for aureon-public. This image is not deployed
# and this file does not create a Hugging Face repository.
#
# Build from this directory:
#   docker build -f Dockerfile -t aureon-public .
#
# The runtime install matches measured/aureon_public_stage1_run.sh:
# requirements.txt (mcp==1.30.0,<2 and the aureon pin), then the mcp package
# with --no-deps. test-requirements.txt is not installed.
#
# No API key is baked in. AUREON_PUBLIC_API_KEY is a runtime secret. The image
# sets AUREON_PUBLIC_OPEN=1 so the read-only surface can bind on the Space port
# when that secret is absent. AUREON_PUBLIC_SWEEP is not set.

FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Full history of main so git rev-parse of the aureon pin still resolves.
# A shallow clone would omit that commit.
# AUREON_REF is required. It will be set to the merge commit of #225 after
# that pull request merges. That sha is not known yet. The pull-request
# workflow passes the pull request base instead, so the clone contains the
# aureon pin. Do not set cf43882e as a standing default.
ARG AUREON_REPO=https://github.com/RA-CONSULTING/Aureon-OS.git
ARG AUREON_REF
RUN test -n "$AUREON_REF" \
    && git clone --branch main --single-branch "$AUREON_REPO" /opt/aureon-os \
    && git -C /opt/aureon-os checkout "$AUREON_REF" \
    && git config --system --add safe.directory /opt/aureon-os

# Overlay this directory so the image runs the scaffold beside the Dockerfile,
# including files that are not on AUREON_REF yet. The overlay is the public
# package only. It does not replace aureon/ and it does not add a key.
COPY . /opt/aureon-os/mcp/aureon_public/

WORKDIR /opt/aureon-os
RUN python -m pip install --no-cache-dir -U pip \
    && python -m pip install --no-cache-dir -r mcp/aureon_public/requirements.txt \
    && python -m pip install --no-cache-dir -e mcp --no-deps \
    && rm -rf /root/.cache/pip

RUN useradd --create-home --uid 1000 aureon \
    && mkdir -p /tmp/aureon-public-space \
    && chown -R aureon:aureon /tmp/aureon-public-space
USER aureon
WORKDIR /tmp/aureon-public-space

# Listen on 0.0.0.0. The MCP SDK turns DNS-rebinding protection on when the
# process binds 127.0.0.1, and then answers 421 to Host: *.hf.space.
# Open mode and keyed mode on the Space stay on 0.0.0.0. A process with
# neither AUREON_PUBLIC_OPEN=1 nor AUREON_PUBLIC_API_KEY still refuses that bind.
ENV AUREON_PUBLIC_REQUIRE_PIN=1 \
    AUREON_OBSERVER_MODE=dry_run \
    AUREON_PUBLIC_OPEN=1 \
    AUREON_PUBLIC_HOST=0.0.0.0 \
    AUREON_PUBLIC_MAX_INFLIGHT=4 \
    PORT=7860 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 7860
CMD ["python", "-m", "aureon_public.space"]
