<!--
  © Clearview Geographic LLC -- All Rights Reserved | Est. 2018
  CVG SLR Wizard — SECURITY
-->

# Security Policy — CVG SLR Wizard

> Proprietary Software | © Clearview Geographic LLC

---

## Supported Versions

| Version | Supported |
|---|---|
| 1.0.x | ✅ Active |
| < 1.0 | ❌ Not supported |

---

## Reporting a Vulnerability

**Do not open public GitHub issues for security vulnerabilities.**

Report security issues directly to:

- **Email**: azelenski@clearviewgeographic.com
- **Subject**: `[SECURITY] CVG SLR Wizard — <Brief Description>`
- **Response time**: 48–72 business hours

Please include:
1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact assessment
4. Any suggested remediation

---

## Security Practices

- No API keys, credentials, or secrets are committed to this repository
- All NOAA API calls use HTTPS
- VDatum JAR path is resolved via environment variable or safe fallback paths only
- Docker containers run as non-root user (`slrwiz`, UID 1001)
- No user-supplied input is executed as shell commands

---

## Dependency Scanning

We use `pip-audit` for dependency vulnerability scanning. Run:

```bash
pip install pip-audit
pip-audit --requirement requirements-lock.txt
```

---

*© Clearview Geographic LLC — All Rights Reserved*
