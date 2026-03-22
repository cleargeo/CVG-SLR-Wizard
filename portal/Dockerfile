# =============================================================================
# CVG SLR Wizard — Portal Container
# Clearview Geographic LLC — Proprietary and Confidential
# =============================================================================
FROM python:3.11-slim

LABEL org.opencontainers.image.title="CVG SLR Wizard Portal"
LABEL org.opencontainers.image.vendor="Clearview Geographic LLC"
LABEL org.opencontainers.image.licenses="Proprietary"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV SLRW_API_URL=http://slr-wizard:8010
ENV PORT=8030

EXPOSE 8030

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8030"]
