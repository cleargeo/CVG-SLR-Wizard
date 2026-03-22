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
"""
processing.py — SLR inundation grid processing engine.

Implements the bathtub inundation model:
  1. Load DEM → apply datum shift → add SLR offset
  2. Identify cells where DEM elevation < water surface
  3. Optionally filter to hydrologically connected cells
  4. Compute per-cell depth = water_surface − DEM

The engine is designed to be deterministic and checkpoint-resumable.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .config import SLRInundationConfig
from .io import RasterData, read_raster, write_raster, clip_to_aoi, raster_to_vector
from .monitoring import PerformanceTracker, timed_stage
from .noaa import get_slr_projection
from .recovery import RecoveryManager, Stage, build_cache_key
from .vdatum import get_datum_separation

log = logging.getLogger(__name__)

FEET_PER_METER = 3.28084


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class InundationResult:
    """Output of a completed SLR inundation run."""
    run_id: str = ""
    scenario: str = ""
    target_year: int = 2050
    slr_offset_ft: float = 0.0
    datum_shift_ft: float = 0.0
    water_surface_navd88_ft: float = 0.0
    inundated_cells: int = 0
    total_cells: int = 0
    inundated_area_m2: float = 0.0
    max_depth_ft: float = 0.0
    mean_depth_ft: float = 0.0
    depth_grid_path: str = ""
    extent_raster_path: str = ""
    extent_vector_path: str = ""
    elapsed_sec: float = 0.0
    qa_flags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def inundated_pct(self) -> float:
        if self.total_cells == 0:
            return 0.0
        return self.inundated_cells / self.total_cells * 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario": self.scenario,
            "target_year": self.target_year,
            "slr_offset_ft": round(self.slr_offset_ft, 4),
            "datum_shift_ft": round(self.datum_shift_ft, 4),
            "water_surface_navd88_ft": round(self.water_surface_navd88_ft, 4),
            "inundated_cells": self.inundated_cells,
            "total_cells": self.total_cells,
            "inundated_pct": round(self.inundated_pct, 2),
            "inundated_area_m2": round(self.inundated_area_m2, 1),
            "max_depth_ft": round(self.max_depth_ft, 3),
            "mean_depth_ft": round(self.mean_depth_ft, 3),
            "depth_grid_path": self.depth_grid_path,
            "extent_raster_path": self.extent_raster_path,
            "extent_vector_path": self.extent_vector_path,
            "elapsed_sec": round(self.elapsed_sec, 2),
            "qa_flags": self.qa_flags,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Main processing entry point
# ---------------------------------------------------------------------------

def run_inundation(
    config: SLRInundationConfig,
    resume: bool = True,
) -> InundationResult:
    """Run the SLR bathtub inundation model for a single scenario/year.

    Parameters
    ----------
    config:
        Fully populated and validated :class:`~slr_wizard.config.SLRInundationConfig`.
    resume:
        If True, attempt to resume from an existing checkpoint.

    Returns
    -------
    InundationResult
        Complete result object with output paths and statistics.
    """
    t0 = time.time()
    run_id = config.metadata.run_id or _generate_run_id(config)
    log.info(
        "SLR Inundation run %s | scenario=%s | year=%d",
        run_id, config.projection.scenario, config.projection.target_year,
    )

    recovery = RecoveryManager(run_id, config.output.output_dir)
    if resume:
        recovery.try_resume()

    result = InundationResult(
        run_id=run_id,
        scenario=config.projection.scenario,
        target_year=config.projection.target_year,
    )

    # ── Stage 1: Load DEM ────────────────────────────────────────────────────
    if not recovery.should_skip(Stage.LOAD_DEM):
        with timed_stage("load_dem") as t:
            dem = read_raster(config.inputs.dem_path)
            log.info("DEM loaded: %dx%d  nodata=%.1f", dem.width, dem.height, dem.nodata)
        recovery.complete(Stage.LOAD_DEM, {"width": dem.width, "height": dem.height})
    else:
        log.info("Skipping load_dem (resumed).")
        dem = read_raster(config.inputs.dem_path)

    # ── Stage 2: Clip to AOI ─────────────────────────────────────────────────
    if config.processing.clip_to_aoi and config.inputs.aoi_path:
        if not recovery.should_skip(Stage.CLIP_AOI):
            with timed_stage("clip_aoi"):
                dem = clip_to_aoi(dem, config.inputs.aoi_path)
                log.info("DEM clipped to AOI: %dx%d", dem.width, dem.height)
            recovery.complete(Stage.CLIP_AOI)
        else:
            dem = clip_to_aoi(dem, config.inputs.aoi_path)

    # ── Convert DEM to feet if needed ────────────────────────────────────────
    dem_ft = _ensure_feet(dem)
    result.total_cells = int((dem_ft.data != dem_ft.nodata).sum())

    # ── Stage 3: Datum shift ─────────────────────────────────────────────────
    datum_shift_ft = 0.0
    if config.projection.apply_tidal_datum_shift and config.inputs.noaa_station_id:
        if not recovery.should_skip(Stage.DATUM_SHIFT):
            with timed_stage("datum_shift"):
                station_lat, station_lon = _station_center(config.inputs.noaa_station_id)
                shift_result = get_datum_separation(
                    station_lat, station_lon,
                    from_datum=config.projection.baseline_datum,
                    to_datum="NAVD88",
                )
                datum_shift_ft = shift_result.shift_ft
                log.info(
                    "Datum shift %s→NAVD88: %.4f ft (source=%s)",
                    config.projection.baseline_datum, datum_shift_ft, shift_result.source,
                )
            recovery.complete(Stage.DATUM_SHIFT, {"datum_shift_ft": datum_shift_ft})
        else:
            datum_shift_ft = recovery.checkpoint.get("stage_datum_shift_meta", {}).get(
                "datum_shift_ft", 0.0
            )
    result.datum_shift_ft = datum_shift_ft

    # ── Stage 4: Resolve SLR offset ──────────────────────────────────────────
    if not recovery.should_skip(Stage.SLR_OFFSET):
        with timed_stage("slr_offset"):
            if config.inputs.custom_slr_offset_ft is not None:
                slr_ft = float(config.inputs.custom_slr_offset_ft)
                log.info("Using custom SLR override: %.4f ft", slr_ft)
            else:
                slr_ft = get_slr_projection(
                    scenario=config.projection.scenario,
                    target_year=config.projection.target_year,
                    station_id=config.inputs.noaa_station_id or None,
                )
                log.info(
                    "NOAA TR-083 SLR offset: %.4f ft (%s, %d, station=%s)",
                    slr_ft,
                    config.projection.scenario,
                    config.projection.target_year,
                    config.inputs.noaa_station_id or "national_avg",
                )
        recovery.complete(Stage.SLR_OFFSET, {"slr_ft": slr_ft})
    else:
        slr_ft = recovery.checkpoint.get("stage_slr_offset_meta", {}).get("slr_ft", 0.0)

    result.slr_offset_ft = slr_ft
    water_surface_ft = datum_shift_ft + slr_ft
    result.water_surface_navd88_ft = water_surface_ft

    # ── Stage 5: Inundation ──────────────────────────────────────────────────
    if not recovery.should_skip(Stage.INUNDATION):
        with timed_stage("inundation") as perf:
            depth_grid, extent_grid = _compute_bathtub(
                dem_ft=dem_ft,
                water_surface_ft=water_surface_ft,
                connected=config.processing.connected_inundation,
                connectivity=config.processing.connectivity_method,
                min_depth=config.processing.min_depth_ft,
            )

        # Compute stats
        valid = depth_grid.data[depth_grid.data != depth_grid.nodata]
        result.inundated_cells = int((extent_grid.data == 1).sum())
        result.max_depth_ft = float(valid.max()) if valid.size > 0 else 0.0
        result.mean_depth_ft = float(valid.mean()) if valid.size > 0 else 0.0

        # Cell area in m²
        res_x, res_y = dem_ft.resolution_m
        cell_area_m2 = res_x * res_y
        result.inundated_area_m2 = result.inundated_cells * cell_area_m2

        recovery.complete(Stage.INUNDATION, {
            "inundated_cells": result.inundated_cells,
            "max_depth_ft": result.max_depth_ft,
        })
    else:
        log.info("Skipping inundation stage (resumed).")
        depth_grid, extent_grid = _compute_bathtub(
            dem_ft=dem_ft,
            water_surface_ft=water_surface_ft,
            connected=config.processing.connected_inundation,
            connectivity=config.processing.connectivity_method,
            min_depth=config.processing.min_depth_ft,
        )

    # ── Stage 6: Write outputs ───────────────────────────────────────────────
    from .paths import get_raster_path, get_output_dir
    out_dir = get_output_dir(config.output.output_dir)
    prefix = config.output.output_prefix
    scenario = config.projection.scenario
    year = config.projection.target_year

    if config.output.write_depth_grid:
        depth_path = get_raster_path(prefix, scenario, year, "depth", out_dir)
        write_raster(depth_grid, depth_path, compress=config.output.compress_outputs)
        result.depth_grid_path = str(depth_path)

    if config.output.write_extent_raster:
        ext_path = get_raster_path(prefix, scenario, year, "extent", out_dir)
        write_raster(extent_grid, ext_path, compress=config.output.compress_outputs)
        result.extent_raster_path = str(ext_path)

    # ── Stage 7: Vectorise ───────────────────────────────────────────────────
    if config.output.write_extent_vector and not recovery.should_skip(Stage.VECTORISE):
        with timed_stage("vectorise"):
            vec_path = out_dir / f"{prefix}_{scenario}_{year}_extent.shp"
            try:
                raster_to_vector(extent_grid, vec_path)
                result.extent_vector_path = str(vec_path)
            except Exception as exc:
                log.warning("Vectorise failed: %s", exc)
                result.qa_flags.append(f"vectorise_failed: {exc}")
        recovery.complete(Stage.VECTORISE)

    result.elapsed_sec = time.time() - t0
    recovery.finish()

    log.info(
        "Run %s complete | %.1f%% inundated | max=%.2f ft | elapsed=%.1f s",
        run_id, result.inundated_pct, result.max_depth_ft, result.elapsed_sec,
    )
    return result


# ---------------------------------------------------------------------------
# Batch (multi-scenario or multi-year)
# ---------------------------------------------------------------------------

def run_batch(config: SLRInundationConfig) -> List[InundationResult]:
    """Run inundation for all scenarios × batch years specified in *config*."""
    from .config import VALID_SCENARIOS
    results: List[InundationResult] = []
    scenarios = VALID_SCENARIOS if config.processing.run_all_scenarios else [config.projection.scenario]
    years = config.processing.batch_years or [config.projection.target_year]

    for scenario in scenarios:
        for year in years:
            run_cfg = _clone_config(config, scenario, year)
            try:
                results.append(run_inundation(run_cfg, resume=False))
            except Exception as exc:
                log.error("Batch run failed scenario=%s year=%d: %s", scenario, year, exc)
    return results


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _generate_run_id(config: SLRInundationConfig) -> str:
    key = build_cache_key(config.to_dict())
    return f"slr_{config.projection.scenario}_{config.projection.target_year}_{key}"


def _ensure_feet(raster: RasterData) -> RasterData:
    """Return a copy of *raster* with data expressed in feet."""
    # Heuristic: if mean valid elevation < 50, assume it's in metres
    valid = raster.data[raster.data != raster.nodata]
    if valid.size == 0:
        return raster
    if valid.mean() < 50.0:
        log.debug("DEM appears to be in metres — converting to feet.")
        new_data = np.where(
            raster.data != raster.nodata,
            raster.data * FEET_PER_METER,
            raster.nodata,
        ).astype("float32")
        import dataclasses
        return dataclasses.replace(raster, data=new_data)
    return raster


def _compute_bathtub(
    dem_ft: RasterData,
    water_surface_ft: float,
    connected: bool,
    connectivity: str,
    min_depth: float,
) -> Tuple[RasterData, RasterData]:
    """Core bathtub inundation kernel.

    Returns (depth_grid, extent_grid) where extent_grid is binary (1=wet, 0=dry).
    """
    import dataclasses

    nodata = dem_ft.nodata
    dem = dem_ft.data

    # Identify potentially inundated cells
    wet_mask = (dem != nodata) & (dem < water_surface_ft)

    if connected:
        wet_mask = _connectivity_filter(wet_mask, method=connectivity)

    # Compute depth
    depth = np.where(
        wet_mask,
        (water_surface_ft - dem).clip(min=0.0),
        nodata,
    ).astype("float32")

    # Apply minimum depth threshold
    if min_depth > 0:
        too_shallow = wet_mask & (depth < min_depth) & (depth != nodata)
        depth = np.where(too_shallow, nodata, depth)
        wet_mask = depth != nodata

    extent = np.where(wet_mask, 1.0, 0.0).astype("float32")

    depth_grid = dataclasses.replace(dem_ft, data=depth)
    extent_grid = dataclasses.replace(dem_ft, data=extent, nodata=0.0)
    return depth_grid, extent_grid


def _connectivity_filter(wet_mask: np.ndarray, method: str = "queen") -> np.ndarray:
    """Filter *wet_mask* to keep only cells connected to the coastal boundary."""
    try:
        from scipy.ndimage import label
    except ImportError:
        log.warning("scipy not available — skipping connectivity filter.")
        return wet_mask

    struct = np.ones((3, 3), dtype=int) if method == "queen" else np.array(
        [[0, 1, 0], [1, 1, 1], [0, 1, 0]], dtype=int
    )
    labeled, _ = label(wet_mask, structure=struct)

    # Keep all connected components that touch the border
    border_labels = set()
    border_labels.update(labeled[0, :])
    border_labels.update(labeled[-1, :])
    border_labels.update(labeled[:, 0])
    border_labels.update(labeled[:, -1])
    border_labels.discard(0)

    if not border_labels:
        # No border connection found — return original mask
        return wet_mask

    connected = np.isin(labeled, list(border_labels))
    return connected & wet_mask


def _station_center(station_id: str) -> Tuple[float, float]:
    """Return approximate (lat, lon) for a NOAA station."""
    from .noaa import list_supported_stations
    for st in list_supported_stations():
        if st.station_id == station_id:
            return st.lat, st.lon
    # Try live fetch
    from .noaa import fetch_station_info
    info = fetch_station_info(station_id)
    if info:
        return info.lat, info.lon
    log.warning("Unknown station %s; using (0, 0) for datum query.", station_id)
    return 0.0, 0.0


def _clone_config(config: SLRInundationConfig, scenario: str, year: int) -> SLRInundationConfig:
    """Return a shallow copy of *config* with scenario/year overridden."""
    import copy
    cfg = copy.deepcopy(config)
    cfg.projection.scenario = scenario
    cfg.projection.target_year = year
    return cfg
