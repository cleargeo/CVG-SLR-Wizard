# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# CVG SLR Wizard — Docker Image
# Author: Alex Zelenski, GISP | azelenski@clearviewgeographic.com
# Updated: 2026-03-21 — Pinned to python:3.13-slim-bookworm (stable Debian 12)
#          Added libexpat1 system package for fiona C extension compatibility
# =============================================================================
FROM python:3.13-slim-bookworm AS base

LABEL maintainer="Alex Zelenski, GISP <azelenski@clearviewgeographic.com>"
LABEL org.opencontainers.image.title="CVG SLR Wizard"
LABEL org.opencontainers.image.description="Sea Level Rise Inundation Grid Wizard"
LABEL org.opencontainers.image.vendor="Clearview Geographic LLC"
LABEL org.opencontainers.image.licenses="Proprietary"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Runtime dependencies (curl for healthcheck, libexpat1 for fiona C extension)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (web-only — no rasterio/GDAL needed for API)
COPY requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt

# Install package
COPY . .
RUN pip install --no-cache-dir -e ".[web]"

# Create non-root user
RUN useradd -m -u 1001 slrwiz && chown -R slrwiz:slrwiz /app
USER slrwiz

# Output directory
RUN mkdir -p /app/output

EXPOSE 8010

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
  CMD curl -fsS http://localhost:8010/health | grep -q '"ok"' || exit 1

CMD ["uvicorn", "slr_wizard.web_api:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8010", \
     "--workers", "2", "--log-level", "info"]
