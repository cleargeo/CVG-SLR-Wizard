<!--
  © Clearview Geographic LLC -- All Rights Reserved | Est. 2018
  CVG SLR Wizard — CONTRIBUTING
-->

# Contributing to CVG SLR Wizard

> **Proprietary / Internal Use** — This is not an open-source project.
> All contributions must be authorized by Clearview Geographic LLC.

---

## Development Setup

```bash
# Clone the repository
git clone https://github.com/clearview-geographic/cvg-slr-wizard.git
cd cvg-slr-wizard

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS / Linux

# Install with dev extras
pip install -e ".[web]"
pip install pytest pytest-cov pytest-mock

# Verify installation
slr-wizard --help
```

---

## Code Standards

- **Python 3.10+** — use `from __future__ import annotations`, type hints everywhere
- **Style**: follow existing code style; no external formatter required
- **CVG Header**: every `.py` file must carry the full CVG copyright header block
- **Docstrings**: all public functions/classes need Google-style docstrings
- **Logging**: use `log = logging.getLogger(__name__)` — no `print()` in library code
- **No hardcoded paths**: use `paths.py` for all file resolution

---

## Testing

```bash
# Run all unit tests
pytest

# With coverage
pytest --cov=slr_wizard --cov-report=html

# Run only fast unit tests (no network)
pytest -m unit
```

All new code **must** include unit tests. Tests live in `tests/`.

---

## ChangeLog Format

Every PR must include an entry in `05_ChangeLogs/master_changelog.md`:

```
## [Unreleased]
### Added
- Brief description of new feature

### Fixed
- Brief description of bug fix

### Changed
- Brief description of modification
```

---

## Branch Naming

| Prefix | Use case |
|---|---|
| `feature/` | New features |
| `fix/` | Bug fixes |
| `refactor/` | Code restructuring |
| `docs/` | Documentation only |
| `test/` | Test additions |
| `chore/` | Build / CI / tooling |

---

*© Clearview Geographic LLC — All Rights Reserved*
