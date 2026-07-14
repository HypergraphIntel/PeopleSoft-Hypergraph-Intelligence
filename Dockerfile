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
    PHI_LOG_DIR=/app/logs

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

EXPOSE 8088

VOLUME ["/config", "/app/data", "/app/logs"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8088/api/health \
        || curl --fail --silent http://127.0.0.1:8088/ \
        || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8088"]