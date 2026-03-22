# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# Proprietary Software -- Internal Use Only
# =============================================================================
"""SLR Wizard core analysis logic.

All projection math is performed by :mod:`slr_wizard.engine`
(NOAA TR-083, Sweet et al. 2022) — **no dependency on storm_surge_wizard**.

This module adds:

- ``run_slr_analysis()`` — adjust a set of baseline water levels by SLR
- ``project_slr()`` — single-station/scenario/year lookup with full metadata
- ``run_sensitivity()`` — all 6 scenarios at once for tabular reporting
- ``SLRResult`` — structured result dataclass with provenance fields

Scientific Notes
----------------
* All SLR projections are expressed above the **2000 baseline** (the NOAA
  TR-083 reference epoch), not relative to current average conditions.
* Station-specific **relative sea level rise (RSLR)** accounts for local
  vertical land motion (VLM) — subsiding coasts have substantially higher
  RSLR than the global mean.
* The NOAA TR-083 Intermediate scenario is the FEMA/NOAA recommended
  baseline for planning-level coastal flood hazard analyses.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class SLRResult:
    """Result of a completed SLR analysis run.

    Attributes
    ----------
    project_name : str
        Run identifier from ``SLRWizardConfig.project_name``.
    station_id : str
        NOAA CO-OPS station used for the projection.
    station_name : str
        Human-readable station name (e.g. ``"Key West, FL"``).
    scenario : str
        Canonical SLR scenario name.
    target_year : int
        Planning horizon year.
    slr_m : float
        Projected relative sea level rise in **metres** above the 2000 baseline.
    slr_ft : float
        Same value in **feet**.
    method : str
        How the SLR value was resolved: ``"noaa_tr083_table"`` or ``"override"``.
    baseline_water_levels : dict
        Input baseline water levels in output_unit.
    adjusted_water_levels : dict
        SLR-adjusted water levels in output_unit.
    output_unit : str
        Unit for water level fields (``"ft"`` or ``"m"``).
    sensitivity : dict
        SLR projections across all 6 scenarios for this station/year
        (``{scenario_name: {"slr_m": float, "slr_ft": float}}``).
    notes : str
        Free-text notes from the config.
    noaa_reference : str
        Full bibliographic citation for the projection source.
    """
    project_name: str = ""
    station_id: str = ""
    station_name: str = ""
    scenario: str = ""
    target_year: int = 2100
    slr_m: float = 0.0
    slr_ft: float = 0.0
    method: str = ""
    baseline_water_levels: Dict[str, float] = field(default_factory=dict)
    adjusted_water_levels: Dict[str, float] = field(default_factory=dict)
    output_unit: str = "ft"
    sensitivity: Dict[str, Dict[str, float]] = field(default_factory=dict)
    notes: str = ""
    noaa_reference: str = (
        "Sweet, W.V., B.D. Hamlington, R.E. Kopp, C.P. Weaver et al. (2022). "
        "Global and Regional Sea Level Rise Scenarios for the United States. "
        "NOAA Technical Report NOS CO-OPS 083. NOAA/NOS Center for Operational "
        "Oceanographic Products and Services. Silver Spring, MD."
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def project_slr(
    station_id: str,
    *,
    scenario: str = "intermediate",
    target_year: int = 2100,
    override_slr_m: Optional[float] = None,
) -> Tuple[float, Dict]:
    """Return projected RSLR (metres) and provenance metadata for a station.

    Thin wrapper around :func:`slr_wizard.engine.resolve_slr_offset`
    that accepts plain arguments instead of requiring a config object.

    Parameters
    ----------
    station_id : str
        NOAA CO-OPS station ID.
    scenario : str
        SLR scenario name or alias (default ``"intermediate"``).
    target_year : int
        Projection year (default 2100).
    override_slr_m : float | None
        When set, bypass the table and use this value directly (metres).

    Returns
    -------
    tuple[float, dict]
        ``(slr_m, metadata)`` where ``slr_m`` is the RSLR in metres.

    Examples
    --------
    >>> slr_m, meta = project_slr("8724580", scenario="high", target_year=2070)
    >>> print(f"SLR at Key West (High, 2070): {slr_m:.3f} m  ({slr_m*3.28084:.2f} ft)")
    """
    from slr_wizard.engine import SLRConfig, resolve_slr_offset

    cfg = SLRConfig(
        enabled=True,
        station_id=station_id,
        scenario=scenario,
        target_year=target_year,
        override_slr_m=override_slr_m,
    )
    return resolve_slr_offset(cfg)


def run_slr_analysis(config) -> SLRResult:
    """Run a complete SLR analysis against a set of baseline water levels.

    Takes an :class:`~slr_wizard.config.SLRWizardConfig` and:

    1. Resolves the NOAA TR-083 SLR projection for the specified station,
       scenario, and target year.
    2. Converts the SLR offset from metres to ``config.output_unit``.
    3. Adds the SLR offset to every baseline water level in
       ``config.baseline_water_levels_ft``.
    4. Computes a full cross-scenario sensitivity table.
    5. Returns an :class:`SLRResult` with all provenance metadata.

    Parameters
    ----------
    config : SLRWizardConfig
        Populated configuration object.

    Returns
    -------
    SLRResult
        Structured result with adjusted water levels and full provenance.

    Examples
    --------
    >>> from slr_wizard import SLRWizardConfig, run_slr_analysis
    >>> cfg = SLRWizardConfig(
    ...     station_id="8724580",
    ...     scenario="intermediate",
    ...     target_year=2070,
    ...     baseline_water_levels_ft={"10yr": 5.2, "100yr": 8.5, "500yr": 10.2},
    ... )
    >>> result = run_slr_analysis(cfg)
    >>> for label, wl in result.adjusted_water_levels.items():
    ...     print(f"{label}: {wl:.2f} {result.output_unit}")
    """
    from slr_wizard.engine import (
        SLRConfig,
        resolve_slr_offset,
        get_slr_sensitivity,
        SLR_STATION_METADATA,
    )

    # ── Resolve SLR offset ────────────────────────────────────────────────────
    slr_cfg = SLRConfig(
        enabled=True,
        station_id=config.station_id,
        scenario=config.scenario,
        target_year=config.target_year,
        override_slr_m=config.override_slr_m,
    )
    slr_m, meta = resolve_slr_offset(slr_cfg)

    # ── Convert to output unit ────────────────────────────────────────────────
    out_unit = (config.output_unit or "ft").strip().lower()
    if out_unit in ("ft", "feet", "foot"):
        slr_out = slr_m * 3.28084
    else:
        slr_out = slr_m

    # ── Apply to baseline water levels ───────────────────────────────────────
    baseline = config.baseline_water_levels_ft  # may be empty dict
    baseline_unit = (config.baseline_unit or "ft").strip().lower()

    def _to_out_unit(val: float, src_unit: str) -> float:
        """Convert a scalar value from src_unit to output unit."""
        s = src_unit.strip().lower()
        o = out_unit.strip().lower()
        if s == o:
            return float(val)
        if s in ("ft", "feet", "foot") and o in ("m", "meter", "metre", "metres"):
            return float(val) * 0.3048
        if s in ("m", "meter", "metre", "metres") and o in ("ft", "feet", "foot"):
            return float(val) * 3.28084
        return float(val)

    adjusted: Dict[str, float] = {}
    baseline_out: Dict[str, float] = {}
    for label, wl in baseline.items():
        wl_out = _to_out_unit(wl, baseline_unit)
        baseline_out[label] = round(wl_out, 4)
        adjusted[label] = round(wl_out + slr_out, 4)

    if baseline_out:
        _log.info(
            "SLR adjusted %d scenario(s) by %.4f %s (%s, %d).",
            len(adjusted), slr_out, out_unit, config.scenario, config.target_year,
        )

    # ── Sensitivity table ─────────────────────────────────────────────────────
    try:
        raw = get_slr_sensitivity(config.station_id, target_year=config.target_year)
        sensitivity = {
            sc: {"slr_m": round(v, 6), "slr_ft": round(v * 3.28084, 6)}
            for sc, v in raw.items()
        }
    except Exception as exc:
        _log.warning("Sensitivity table failed: %s", exc)
        sensitivity = {}

    station_info = SLR_STATION_METADATA.get(config.station_id, {})

    return SLRResult(
        project_name=config.project_name,
        station_id=config.station_id,
        station_name=station_info.get("name", config.station_id),
        scenario=meta.get("scenario", config.scenario),
        target_year=config.target_year,
        slr_m=round(slr_m, 6),
        slr_ft=round(slr_m * 3.28084, 6),
        method=meta.get("method", "unknown"),
        baseline_water_levels=baseline_out,
        adjusted_water_levels=adjusted,
        output_unit=out_unit,
        sensitivity=sensitivity,
        notes=config.notes,
    )


def run_sensitivity(station_id: str, *, target_year: int = 2100) -> Dict[str, Dict[str, float]]:
    """Return SLR projections across all 6 NOAA TR-083 scenarios.

    Convenience wrapper around :func:`slr_wizard.engine.get_slr_sensitivity`.

    Parameters
    ----------
    station_id : str
        NOAA CO-OPS station identifier.
    target_year : int
        Projection year (default 2100).

    Returns
    -------
    dict
        ``{scenario_name: {"slr_m": float, "slr_ft": float}}``

    Examples
    --------
    >>> sens = run_sensitivity("8724580", target_year=2070)
    >>> for sc, vals in sens.items():
    ...     print(f"{sc:20s}  {vals['slr_m']:.3f} m  {vals['slr_ft']:.2f} ft")
    """
    from slr_wizard.engine import get_slr_sensitivity
    raw = get_slr_sensitivity(station_id, target_year=target_year)
    return {
        sc: {"slr_m": round(v, 6), "slr_ft": round(v * 3.28084, 6)}
        for sc, v in raw.items()
    }
