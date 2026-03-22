# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# Proprietary Software -- Internal Use Only
# Protected under US and International copyright, trade secret,
# trademark, cybersecurity, and intellectual property law.
# This Product is developed under CVG's Agentic Development Framework (ADF).
# Unauthorized use, replication, or modification is strictly prohibited.
# -----------------------------------------------------------------------------
# Author      : Alex Zelenski, GISP
# Organization: Clearview Geographic, LLC
# Contact     : azelenski@clearviewgeographic.com  |  386-957-2314
# License     : Proprietary -- CVG-ADF
# =============================================================================
"""SLR Wizard configuration dataclasses.

Two config families are provided:

1. **Simple / projection-only** — :class:`SLRWizardConfig` (flat dataclass).
   Used by :mod:`slr_wizard.core` for scenario projection and water-level
   adjustment.  No DEM required.

2. **Full inundation engine** — :class:`SLRInundationConfig` (nested dataclasses).
   Used by :mod:`slr_wizard.processing` for bathtub inundation grid analysis.
   Requires a DEM GeoTIFF.

Sub-configs for the inundation engine:
   :class:`InputsConfig`, :class:`SLRProjectionConfig`,
   :class:`ProcessingConfig`, :class:`OutputConfig`, :class:`RunMetadata`.
"""
from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# NOAA TR-083 scenario constants
# ---------------------------------------------------------------------------

#: Valid decade target years from NOAA TR-083 Table (Appendix C).
VALID_YEARS: List[int] = [2030, 2040, 2050, 2060, 2070, 2080, 2090, 2100]

#: Canonical NOAA TR-083 scenario names in ascending order.
VALID_SCENARIOS: List[str] = [
    "low",
    "intermediate_low",
    "intermediate",
    "intermediate_high",
    "high",
    "extreme",
]

#: Short-form aliases accepted by :func:`resolve_scenario`.
SCENARIO_ALIASES: Dict[str, str] = {
    "l":        "low",
    "il":       "intermediate_low",
    "int_low":  "intermediate_low",
    "i":        "intermediate",
    "int":      "intermediate",
    "ih":       "intermediate_high",
    "int_high": "intermediate_high",
    "h":        "high",
    "e":        "extreme",
}


def resolve_scenario(name: str) -> str:
    """Convert an alias or full scenario name to the canonical form.

    Parameters
    ----------
    name : str
        Scenario name or alias (case-insensitive, spaces/hyphens tolerated).

    Returns
    -------
    str
        Canonical scenario name from :data:`VALID_SCENARIOS`.

    Raises
    ------
    ValueError
        When *name* does not match any known scenario or alias.
    """
    n = name.lower().strip().replace("-", "_").replace(" ", "_")
    if n in VALID_SCENARIOS:
        return n
    if n in SCENARIO_ALIASES:
        return SCENARIO_ALIASES[n]
    raise ValueError(
        f"Unknown SLR scenario '{name}'. "
        f"Valid scenarios: {VALID_SCENARIOS}  "
        f"Aliases: {list(SCENARIO_ALIASES)}"
    )


# ---------------------------------------------------------------------------
# Simple / flat config  —  used by slr_wizard.core (projection-only API)
# ---------------------------------------------------------------------------

@dataclass
class SLRWizardConfig:
    """Configuration for a standalone SLR projection and water-level adjustment.

    Use this when you want to project sea level rise at a tide gauge station
    and optionally adjust a set of baseline (current-conditions) water surface
    elevations — without computing a raster depth grid.

    For full bathtub inundation grid analysis, use :class:`SLRInundationConfig`.

    Parameters
    ----------
    station_id : str
        NOAA CO-OPS tide gauge station ID (e.g. ``"8724580"`` for Key West, FL).
        Use ``slr-wizard list-stations`` to see all built-in stations.
    scenario : str
        NOAA TR-083 SLR scenario (default ``"intermediate"``).
        Accepted: ``"low"`` | ``"intermediate_low"`` | ``"intermediate"`` |
        ``"intermediate_high"`` | ``"high"`` | ``"extreme"``.
        Short aliases ``"l"``, ``"il"``, ``"i"``, ``"ih"``, ``"h"``, ``"e"`` also work.
    target_year : int
        Planning horizon year, 2020–2100 (default 2100).
    baseline_water_levels_ft : dict
        Mapping of return-period label → baseline still-water elevation in
        *baseline_unit*.  Example: ``{"10yr": 5.2, "100yr": 8.5, "500yr": 10.2}``.
        Leave empty to compute a projection-only report.
    baseline_unit : str
        Unit of *baseline_water_levels_ft* values: ``"ft"`` or ``"m"``
        (default ``"ft"``).
    output_unit : str
        Unit for adjusted water levels in the result: ``"ft"`` or ``"m"``
        (default ``"ft"``).
    override_slr_m : float | None
        When set, bypass the NOAA TR-083 table and use this value (metres).
    notes : str
        Free-text notes.
    project_name : str
        Run identifier.
    """
    station_id: str = "8724580"
    scenario: str = "intermediate"
    target_year: int = 2100
    baseline_water_levels_ft: Dict[str, float] = field(default_factory=dict)
    baseline_unit: str = "ft"
    output_unit: str = "ft"
    override_slr_m: Optional[float] = None
    notes: str = ""
    project_name: str = "slr_analysis"


@dataclass
class SLRSensitivityConfig:
    """Configuration for a cross-scenario sensitivity table.

    Generates projections across all 6 NOAA TR-083 scenarios for a given
    station and target year.  Useful for planning sensitivity reports.
    """
    station_id: str = "8724580"
    target_year: int = 2100
    project_name: str = "slr_sensitivity"


# ---------------------------------------------------------------------------
# Nested sub-configs  —  used by SLRInundationConfig / processing engine
# ---------------------------------------------------------------------------

@dataclass
class InputsConfig:
    """Input data paths and station information for the inundation engine.

    Parameters
    ----------
    dem_path : str
        Path to the bare-earth DEM GeoTIFF (NAVD88 datum recommended).
    noaa_station_id : str
        NOAA CO-OPS station ID for RSLR lookup and optional datum shift.
    aoi_path : str
        Optional polygon boundary (shapefile / GeoJSON) to clip the DEM.
    custom_slr_offset_ft : float | None
        When set, overrides the NOAA table with this SLR value in feet.
    """
    dem_path: str = ""
    noaa_station_id: str = ""
    aoi_path: str = ""
    custom_slr_offset_ft: Optional[float] = None

    def validate(self) -> List[str]:
        """Return a list of validation error strings (empty = valid)."""
        errors: List[str] = []
        if not self.dem_path:
            errors.append("dem_path is required but was not set.")
        elif not Path(self.dem_path).exists():
            errors.append(f"dem_path '{self.dem_path}' does not exist on disk.")
        return errors


@dataclass
class SLRProjectionConfig:
    """SLR scenario and datum parameters for the inundation engine.

    Parameters
    ----------
    scenario : str
        NOAA TR-083 scenario name (default ``"intermediate"``).
    target_year : int
        Planning horizon decade year (default 2050).
    apply_tidal_datum_shift : bool
        Apply MSL → NAVD88 datum separation from NOAA VDatum
        (requires *noaa_station_id* in :class:`InputsConfig`).
    baseline_datum : str
        Datum of the DEM (``"NAVD88"`` or ``"MSL"``; default ``"NAVD88"``).
    use_vdatum : bool
        Try NOAA VDatum API/JAR for datum shift (default False).
    """
    scenario: str = "intermediate"
    target_year: int = 2050
    apply_tidal_datum_shift: bool = False
    baseline_datum: str = "NAVD88"
    use_vdatum: bool = False

    def validate(self) -> List[str]:
        """Return a list of validation error strings (empty = valid)."""
        errors: List[str] = []
        if self.scenario not in VALID_SCENARIOS:
            errors.append(
                f"scenario '{self.scenario}' is not valid. "
                f"Choose from: {VALID_SCENARIOS}"
            )
        if self.target_year not in VALID_YEARS:
            errors.append(
                f"target_year {self.target_year} is not a valid decade year. "
                f"Choose from: {VALID_YEARS}"
            )
        return errors


@dataclass
class ProcessingConfig:
    """Inundation analysis processing options.

    Parameters
    ----------
    connected_inundation : bool
        Apply connectivity filter to keep only cells hydraulically connected
        to the coast (recommended; default True).
    connectivity_method : str
        ``"queen"`` (8-connected) or ``"rook"`` (4-connected).
    min_depth_ft : float
        Minimum inundation depth threshold in feet.  Cells shallower than this
        are excluded from the output (default 0.0 = include all wet cells).
    clip_to_aoi : bool
        Clip analysis to *aoi_path* in :class:`InputsConfig` (default False).
    run_all_scenarios : bool
        If True, :func:`~slr_wizard.processing.run_batch` iterates over all
        6 NOAA TR-083 scenarios.
    batch_years : list[int] | None
        List of target years for batch runs.  None = use single target_year.
    """
    connected_inundation: bool = True
    connectivity_method: str = "queen"
    min_depth_ft: float = 0.0
    clip_to_aoi: bool = False
    run_all_scenarios: bool = False
    batch_years: Optional[List[int]] = None


@dataclass
class OutputConfig:
    """Output file settings for the inundation engine.

    Parameters
    ----------
    output_dir : str
        Directory for output GeoTIFFs and reports.
    output_prefix : str
        Filename prefix applied to all output files.
    write_depth_grid : bool
        Write the flood depth GeoTIFF (default True).
    write_extent_raster : bool
        Write a binary inundation extent raster (default True).
    write_extent_vector : bool
        Vectorise the inundation extent to Shapefile (default False).
    compress_outputs : bool
        Apply LZW compression to output GeoTIFFs (default True).
    """
    output_dir: str = "output"
    output_prefix: str = "slr_inundation"
    write_depth_grid: bool = True
    write_extent_raster: bool = True
    write_extent_vector: bool = False
    compress_outputs: bool = True


@dataclass
class RunMetadata:
    """Run identification and audit metadata.

    Parameters
    ----------
    run_id : str
        Unique run identifier.  Auto-generated when empty.
    project_name : str
        Human-readable project name recorded in reports.
    analyst : str
        Name of the analyst running the tool.
    notes : str
        Free-text notes.
    """
    run_id: str = ""
    project_name: str = ""
    analyst: str = ""
    notes: str = ""


# ---------------------------------------------------------------------------
# Rich nested config  —  used by slr_wizard.processing (inundation engine)
# ---------------------------------------------------------------------------

@dataclass
class SLRInundationConfig:
    """Full nested configuration for the SLR bathtub inundation analysis engine.

    This config is accepted by :func:`~slr_wizard.processing.run_inundation`
    and the ``POST /api/run`` web API endpoint.

    For simple sea level rise projection without DEM analysis, use the
    lightweight :class:`SLRWizardConfig` instead.

    Parameters
    ----------
    inputs : InputsConfig
        DEM path, NOAA station, AOI, and optional SLR override.
    projection : SLRProjectionConfig
        Scenario, target year, and datum settings.
    processing : ProcessingConfig
        Connectivity filter, depth threshold, and batch options.
    output : OutputConfig
        Output directory, filename prefix, and compression settings.
    metadata : RunMetadata
        Run ID, project name, and analyst.

    Examples
    --------
    >>> from slr_wizard.config import (
    ...     SLRInundationConfig, InputsConfig, SLRProjectionConfig,
    ...     ProcessingConfig, OutputConfig, RunMetadata,
    ... )
    >>> cfg = SLRInundationConfig(
    ...     inputs=InputsConfig(dem_path="/data/dem.tif", noaa_station_id="8724580"),
    ...     projection=SLRProjectionConfig(scenario="intermediate", target_year=2070),
    ...     output=OutputConfig(output_dir="/data/slr_output"),
    ...     metadata=RunMetadata(project_name="Monroe County SLR 2070"),
    ... )
    """
    inputs: InputsConfig = field(default_factory=InputsConfig)
    projection: SLRProjectionConfig = field(default_factory=SLRProjectionConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    metadata: RunMetadata = field(default_factory=RunMetadata)

    def to_dict(self) -> Dict[str, Any]:
        """Return a fully serialisable dict representation."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "SLRInundationConfig":
        """Reconstruct an :class:`SLRInundationConfig` from a plain dict.

        Parameters
        ----------
        d : dict
            Dict as produced by :meth:`to_dict` or loaded from a JSON file.
        """
        return cls(
            inputs=InputsConfig(**d.get("inputs", {})),
            projection=SLRProjectionConfig(**d.get("projection", {})),
            processing=ProcessingConfig(**d.get("processing", {})),
            output=OutputConfig(**d.get("output", {})),
            metadata=RunMetadata(**d.get("metadata", {})),
        )


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def save_config(config: SLRInundationConfig, path: Union[str, Path]) -> None:
    """Serialise *config* to a JSON file at *path*.

    Parameters
    ----------
    config : SLRInundationConfig
        Configuration to save.
    path : str or Path
        Destination file path.  Parent directories are created if absent.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(config.to_dict(), fh, indent=2)


def load_config(path: Union[str, Path]) -> SLRInundationConfig:
    """Load an :class:`SLRInundationConfig` from a JSON file.

    Parameters
    ----------
    path : str or Path
        Path to a JSON file previously written by :func:`save_config`.

    Returns
    -------
    SLRInundationConfig
    """
    with Path(path).open("r", encoding="utf-8") as fh:
        d = json.load(fh)
    return SLRInundationConfig.from_dict(d)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_config(config: SLRInundationConfig) -> None:
    """Validate an :class:`SLRInundationConfig` and raise on any issue.

    Parameters
    ----------
    config : SLRInundationConfig
        Populated configuration to validate.

    Raises
    ------
    ValueError
        When required fields are missing or values are out of range.
    """
    if not config.inputs.dem_path:
        raise ValueError(
            "inputs.dem_path must be set to the path of the DEM GeoTIFF."
        )

    try:
        resolve_scenario(config.projection.scenario)
    except ValueError as exc:
        raise ValueError(f"projection.scenario: {exc}") from exc

    year = config.projection.target_year
    if not (2020 <= year <= 2150):
        raise ValueError(
            f"projection.target_year must be between 2020 and 2150, got {year}."
        )

    if config.processing.min_depth_ft < 0:
        raise ValueError(
            f"processing.min_depth_ft must be ≥ 0, got {config.processing.min_depth_ft}."
        )

    if config.processing.connectivity_method not in ("queen", "rook"):
        raise ValueError(
            f"processing.connectivity_method must be 'queen' or 'rook', "
            f"got '{config.processing.connectivity_method}'."
        )
