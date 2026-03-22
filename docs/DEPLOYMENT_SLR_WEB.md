# CVG SLR Wizard — Web Deployment Guide

> © Clearview Geographic LLC | Internal Use Only | CVG-ADF

---

## Overview

This document covers deploying the CVG SLR Wizard API (`slr-wizard`) as a production
web service on a CVG Ubuntu 22.04 LXC container or VM.

- **Service port:** 8010 (API) | 8030 (Portal dashboard)
- **Target domain:** `slr.cleargeo.tech`
- **Reverse proxy:** Caddy 2 (automatic TLS via Let's Encrypt)
- **Process manager:** systemd (`cvg-slr-wizard.service`)

---

## Prerequisites

| Requirement | Version |
|---|---|
| Ubuntu | 22.04 LTS |
| Python | 3.10+ |
| pip | 23+ |
| Docker (optional) | 24+ |
| Caddy | 2.7+ |

CGPS share mounted at `/mnt/cgps` with the project files.

---

## 1. Bootstrap Script

Run the automated bootstrap from the project root:

```bash
bash scripts/bootstrap_slr_vm.sh
```

This will:
1. Install system dependencies (python3, pip, caddy, git)
2. Mount the CGPS SMB share
3. rsync the project files
4. Create Python virtual environment at `/opt/slr-wizard/venv`
5. Install `slr-wizard` package
6. Install and enable the `cvg-slr-wizard.service` systemd unit
7. Start Caddy with the `caddy/Caddyfile` config

---

## 2. Manual Deployment Steps

### 2.1 Create service user

```bash
sudo useradd -r -s /bin/false -d /opt/slr-wizard slrwiz
sudo mkdir -p /opt/slr-wizard
sudo chown slrwiz:slrwiz /opt/slr-wizard
```

### 2.2 Install package

```bash
sudo -u slrwiz python3 -m venv /opt/slr-wizard/venv
sudo -u slrwiz /opt/slr-wizard/venv/bin/pip install --upgrade pip
sudo -u slrwiz /opt/slr-wizard/venv/bin/pip install \
    "slr-wizard>=1.0.0" "fastapi>=0.110" "uvicorn[standard]>=0.29"
```

### 2.3 Create systemd service

`/etc/systemd/system/cvg-slr-wizard.service`:

```ini
[Unit]
Description=CVG SLR Wizard API
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=slrwiz
Group=slrwiz
WorkingDirectory=/opt/slr-wizard
ExecStart=/opt/slr-wizard/venv/bin/uvicorn slr_wizard.web_api:app \
    --host 0.0.0.0 --port 8010 --workers 2 --log-level info
Restart=always
RestartSec=5
Environment=SLR_WIZARD_ENV=production
Environment=SLR_WIZARD_CACHE_DIR=/opt/slr-wizard/cache
StandardOutput=journal
StandardError=journal
SyslogIdentifier=cvg-slr-wizard

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable cvg-slr-wizard
sudo systemctl start cvg-slr-wizard
sudo systemctl status cvg-slr-wizard
```

### 2.4 Caddy reverse proxy

`/etc/caddy/Caddyfile` (or use `caddy/Caddyfile` from the project):

```caddy
slr.cleargeo.tech {
    reverse_proxy localhost:8010

    encode gzip

    header {
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }

    log {
        output file /var/log/caddy/slr-access.log
    }
}
```

```bash
sudo systemctl reload caddy
```

---

## 3. Docker Deployment

### 3.1 Build and run

```bash
# Build the image
docker build -t cvg-slr-wizard:latest .

# Run production container
docker compose -f docker-compose.prod.yml up -d
```

### 3.2 `docker-compose.prod.yml` key settings

```yaml
services:
  slr-api:
    image: cvg-slr-wizard:latest
    ports:
      - "8010:8010"
    environment:
      - SLR_WIZARD_ENV=production
      - SLR_WIZARD_CACHE_DIR=/cache
    volumes:
      - slr-cache:/cache
      - /data/dem:/data/dem:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8010/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 4. Operations

### Health check

```bash
curl http://localhost:8010/health
# {"status": "ok", "uptime_s": 1234.5}
```

### View logs

```bash
journalctl -u cvg-slr-wizard -f
# or Docker:
docker compose logs -f slr-api
```

### Restart service

```bash
sudo systemctl restart cvg-slr-wizard
```

### Test a projection

```bash
curl -s -X POST http://localhost:8010/slr \
  -H "Content-Type: application/json" \
  -d '{"station_id":"8724580","scenario":"Intermediate","target_year":2070}' | python3 -m json.tool
```

---

## 5. Monitoring

The API exposes a `/metrics` endpoint (Prometheus format) for optional integration
with Grafana. Key metrics:

| Metric | Description |
|---|---|
| `slrw_requests_total` | Total API requests |
| `slrw_request_duration_seconds` | Request latency histogram |
| `slrw_noaa_fetch_errors_total` | NOAA CO-OPS fetch failures |
| `slrw_inundation_runs_total` | Inundation analysis runs |
| `slrw_cache_hits_total` | NOAA data cache hits |

---

## 6. Security Notes

- Run as unprivileged user (`slrwiz`, UID 1001) — never as root
- DEM data volumes mounted **read-only** in Docker (`ro`)
- No external database — all state is in-process or file-based cache
- Caddy handles TLS; do not expose port 8010 directly to the public internet
- Rotate deployments via blue/green with `docker compose pull && docker compose up -d`

---

## 7. File Paths (Production)

| Path | Purpose |
|---|---|
| `/opt/slr-wizard/venv/` | Python virtual environment |
| `/opt/slr-wizard/cache/` | NOAA CO-OPS response cache |
| `/data/dem/` | DEM raster inputs (read-only mount) |
| `/output/` | Analysis output files |
| `/var/log/caddy/slr-access.log` | Request access log |
| `/etc/systemd/system/cvg-slr-wizard.service` | systemd unit |

---

*See also: `scripts/bootstrap_slr_vm.sh`, `Dockerfile`, `docker-compose.prod.yml`*
