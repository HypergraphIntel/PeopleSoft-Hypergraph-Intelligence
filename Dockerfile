FROM python:3.12-slim-bookworm

ARG VERSION=dev
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="PeopleSoft Hypergraph Intelligence"
LABEL org.opencontainers.image.description="Read-only observability and exploration platform for PeopleSoft environments"
LABEL org.opencontainers.image.source="https://github.com/NoodleSploder/PeopleSoft-Hypergraph-Intelligence"
LABEL org.opencontainers.image.licenses="Apache-2.0"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PHI_CONFIG_FILE=/config/config.json \
    PHI_DATA_DIR=/app/data \
    PHI_LOG_DIR=/app/logs \
    PHI_PORT=8088

WORKDIR /app

# Runtime libraries needed by common Python packages and health checks.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --upgrade pip \
    && pip install --requirement requirements.txt

COPY . .

# Ensure runtime mount points exist before dropping privileges.
RUN mkdir -p /config /app/data /app/logs \
    && groupadd --system --gid 10001 phi \
    && useradd \
        --system \
        --uid 10001 \
        --gid phi \
        --home-dir /app \
        --shell /usr/sbin/nologin \
        phi \
    && chown -R phi:phi /app /config

USER phi

EXPOSE $PHI_PORT

VOLUME ["/config", "/app/data", "/app/logs"]

# Shell form (not the JSON array CMD below) so $PHI_PORT is available for
# substitution — HEALTHCHECK CMD written as a plain string always runs
# through /bin/sh -c already, so this needs no extra wrapping.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:${PHI_PORT}/api/health \
        || curl --fail --silent http://127.0.0.1:${PHI_PORT}/ \
        || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]

# CMD needs shell form here (unlike the rest of this file, which prefers
# exec/JSON-array form) specifically so $PHI_PORT gets substituted at
# container start — a JSON-array CMD is passed to exec() literally, with
# no shell involved to expand env vars. `exec` inside the shell string
# still replaces the shell process with uvicorn, so tini (PID 1) supervises
# uvicorn directly, not an intermediate shell — signal handling is
# unaffected.
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PHI_PORT}"]