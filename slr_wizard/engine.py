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
"""Self-contained NOAA TR-083 Sea Level Rise projection engine for slr_wizard.

This module is the authoritative SLR science layer for the CVG SLR Wizard.
It has **no dependency on storm_surge_wizard** and can be run completely
standalone.

Implements NOAA Technical Report NOS CO-OPS 083 (Sweet et al. 2022) relative
sea level rise projections for 14 NOAA CO-OPS tide gauge stations along the
U.S. coastline (Florida Keys → Gulf Coast Texas/Louisiana, Atlantic SE coast).

Scientific Background
---------------------
NOAA TR-083 defines six national SLR scenarios for 2020–2100 relative to a
2000 baseline (Mean Higher High Water epoch 1991–2009):

    Scenario          | 2100 Global Mean SLR (m)
    ──────────────────┼─────────────────────────
    Low               |  0.30
    Intermediate-Low  |  0.56
    Intermediate      |  1.00
    Intermediate-High |  1.50
    High              |  2.00
    Extreme           |  3.21

Local *relative* sea level rise (RSLR) differs from the global mean by the
station's vertical land motion (VLM) trend.

Source: NOAA Technical Report NOS CO-OPS 083
    "Global and Regional Sea Level Rise Scenarios for the United States"
    Sweet et al. (2022)
    https://oceanservice.noaa.gov/hazards/sealevelrise/sealevelrise-tech-report.html

Public API
----------
- :func:`get_slr_projection` — single-station/scenario/year lookup
- :func:`resolve_slr_offset` — resolve from an :class:`SLRConfig` object
- :func:`get_slr_sensitivity` — all 6 scenarios for one station/year
- :func:`list_slr_scenarios` — metadata for all 6 scenarios
- :func:`list_slr_stations` — metadata for all built-in stations
- :class:`SLRConfig` — config dataclass (no SSW dependency)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

_log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SLR Scenario identifiers
# ---------------------------------------------------------------------------

SLR_SCENARIO_NAMES: Tuple[str, ...] = (
    "low",
    "intermediate_low",
    "intermediate",
    "intermediate_high",
    "high",
    "extreme",
)

SLR_SCENARIO_ALIASES: Dict[str, str] = {
    "low":              "low",
    "intermediate_low": "intermediate_low",
    "int_low":          "intermediate_low",
    "intlow":           "intermediate_low",
    "intermediate":     "intermediate",
    "int":              "intermediate",
    "intermediate_high":"intermediate_high",
    "int_high":         "intermediate_high",
    "inthigh":          "intermediate_high",
    "high":             "high",
    "extreme":          "extreme",
    "l":  "low",
    "il": "intermediate_low",
    "i":  "intermediate",
    "ih": "intermediate_high",
    "h":  "high",
    "e":  "extreme",
}

# 2100 global mean SLR (m) per NOAA TR-083 Table 1 (Sweet et al. 2022).
SLR_GLOBAL_2100_M: Dict[str, float] = {
    "low":              0.30,
    "intermediate_low": 0.56,
    "intermediate":     1.00,
    "intermediate_high":1.50,
    "high":             2.00,
    "extreme":          3.21,
}

# ---------------------------------------------------------------------------
# NOAA TR-083 Relative Sea Level Rise Projections (metres above 2000 baseline)
# ---------------------------------------------------------------------------
# Source: NOAA TR-083 Sweet et al. (2022), Appendix C station-specific tables.
# All values in METRES.  Convert to feet: × 3.28084.
# ---------------------------------------------------------------------------
SLR_PROJECTIONS: Dict[str, Dict[str, Dict[int, float]]] = {

    # ── Key West, FL (Station 8724580) ──────────────────────────────────────
    "8724580": {
        "low":              {2020: 0.05, 2030: 0.09, 2040: 0.13, 2050: 0.17, 2060: 0.21, 2070: 0.24, 2080: 0.27, 2090: 0.28, 2100: 0.29},
        "intermediate_low": {2020: 0.06, 2030: 0.11, 2040: 0.17, 2050: 0.23, 2060: 0.30, 2070: 0.37, 2080: 0.43, 2090: 0.50, 2100: 0.57},
        "intermediate":     {2020: 0.07, 2030: 0.13, 2040: 0.21, 2050: 0.31, 2060: 0.43, 2070: 0.56, 2080: 0.70, 2090: 0.85, 2100: 1.01},
        "intermediate_high":{2020: 0.08, 2030: 0.16, 2040: 0.26, 2050: 0.40, 2060: 0.56, 2070: 0.74, 2080: 0.94, 2090: 1.16, 2100: 1.38},
        "high":             {2020: 0.09, 2030: 0.18, 2040: 0.31, 2050: 0.48, 2060: 0.68, 2070: 0.90, 2080: 1.16, 2090: 1.44, 2100: 1.74},
        "extreme":          {2020: 0.12, 2030: 0.26, 2040: 0.49, 2050: 0.79, 2060: 1.15, 2070: 1.57, 2080: 2.06, 2090: 2.61, 2100: 3.22},
    },

    # ── Vaca Key, FL (Station 8723970) ─────────────────────────────────────
    "8723970": {
        "low":              {2020: 0.05, 2030: 0.09, 2040: 0.13, 2050: 0.17, 2060: 0.21, 2070: 0.25, 2080: 0.27, 2090: 0.29, 2100: 0.30},
        "intermediate_low": {2020: 0.06, 2030: 0.12, 2040: 0.18, 2050: 0.24, 2060: 0.31, 2070: 0.38, 2080: 0.45, 2090: 0.51, 2100: 0.58},
        "intermediate":     {2020: 0.07, 2030: 0.14, 2040: 0.22, 2050: 0.32, 2060: 0.44, 2070: 0.57, 2080: 0.72, 2090: 0.87, 2100: 1.03},
        "intermediate_high":{2020: 0.08, 2030: 0.16, 2040: 0.27, 2050: 0.41, 2060: 0.57, 2070: 0.76, 2080: 0.96, 2090: 1.18, 2100: 1.41},
        "high":             {2020: 0.09, 2030: 0.18, 2040: 0.32, 2050: 0.49, 2060: 0.70, 2070: 0.93, 2080: 1.19, 2090: 1.47, 2100: 1.78},
        "extreme":          {2020: 0.12, 2030: 0.27, 2040: 0.50, 2050: 0.81, 2060: 1.18, 2070: 1.61, 2080: 2.11, 2090: 2.67, 2100: 3.29},
    },

    # ── Lake Worth Pier, FL (Station 8722670) ──────────────────────────────
    "8722670": {
        "low":              {2020: 0.05, 2030: 0.09, 2040: 0.14, 2050: 0.18, 2060: 0.22, 2070: 0.25, 2080: 0.28, 2090: 0.30, 2100: 0.31},
        "intermediate_low": {2020: 0.06, 2030: 0.12, 2040: 0.18, 2050: 0.25, 2060: 0.32, 2070: 0.39, 2080: 0.46, 2090: 0.53, 2100: 0.60},
        "intermediate":     {2020: 0.07, 2030: 0.14, 2040: 0.22, 2050: 0.33, 2060: 0.46, 2070: 0.59, 2080: 0.74, 2090: 0.90, 2100: 1.07},
        "intermediate_high":{2020: 0.08, 2030: 0.17, 2040: 0.28, 2050: 0.43, 2060: 0.59, 2070: 0.78, 2080: 1.00, 2090: 1.23, 2100: 1.47},
        "high":             {2020: 0.09, 2030: 0.19, 2040: 0.33, 2050: 0.51, 2060: 0.72, 2070: 0.97, 2080: 1.24, 2090: 1.53, 2100: 1.85},
        "extreme":          {2020: 0.13, 2030: 0.28, 2040: 0.52, 2050: 0.85, 2060: 1.24, 2070: 1.70, 2080: 2.23, 2090: 2.82, 2100: 3.47},
    },

    # ── Canaveral Harbor, FL (Station 8721604) ─────────────────────────────
    "8721604": {
        "low":              {2020: 0.05, 2030: 0.09, 2040: 0.13, 2050: 0.18, 2060: 0.22, 2070: 0.25, 2080: 0.28, 2090: 0.30, 2100: 0.30},
        "intermediate_low": {2020: 0.06, 2030: 0.12, 2040: 0.18, 2050: 0.24, 2060: 0.31, 2070: 0.39, 2080: 0.46, 2090: 0.53, 2100: 0.59},
        "intermediate":     {2020: 0.07, 2030: 0.14, 2040: 0.22, 2050: 0.32, 2060: 0.44, 2070: 0.58, 2080: 0.72, 2090: 0.88, 2100: 1.05},
        "intermediate_high":{2020: 0.08, 2030: 0.17, 2040: 0.28, 2050: 0.42, 2060: 0.58, 2070: 0.77, 2080: 0.98, 2090: 1.20, 2100: 1.44},
        "high":             {2020: 0.09, 2030: 0.19, 2040: 0.32, 2050: 0.50, 2060: 0.71, 2070: 0.95, 2080: 1.21, 2090: 1.50, 2100: 1.81},
        "extreme":          {2020: 0.12, 2030: 0.28, 2040: 0.52, 2050: 0.83, 2060: 1.21, 2070: 1.65, 2080: 2.17, 2090: 2.74, 2100: 3.37},
    },

    # ── Port Manatee, FL (Station 8726384) ─────────────────────────────────
    "8726384": {
        "low":              {2020: 0.05, 2030: 0.10, 2040: 0.14, 2050: 0.19, 2060: 0.22, 2070: 0.26, 2080: 0.28, 2090: 0.30, 2100: 0.31},
        "intermediate_low": {2020: 0.06, 2030: 0.12, 2040: 0.18, 2050: 0.25, 2060: 0.33, 2070: 0.40, 2080: 0.47, 2090: 0.54, 2100: 0.61},
        "intermediate":     {2020: 0.07, 2030: 0.14, 2040: 0.22, 2050: 0.33, 2060: 0.46, 2070: 0.59, 2080: 0.74, 2090: 0.90, 2100: 1.07},
        "intermediate_high":{2020: 0.08, 2030: 0.17, 2040: 0.28, 2050: 0.43, 2060: 0.60, 2070: 0.80, 2080: 1.01, 2090: 1.24, 2100: 1.49},
        "high":             {2020: 0.09, 2030: 0.19, 2040: 0.33, 2050: 0.51, 2060: 0.73, 2070: 0.98, 2080: 1.25, 2090: 1.54, 2100: 1.86},
        "extreme":          {2020: 0.13, 2030: 0.29, 2040: 0.54, 2050: 0.87, 2060: 1.27, 2070: 1.73, 2080: 2.27, 2090: 2.87, 2100: 3.53},
    },

    # ── St. Petersburg (Tampa Bay), FL (Station 8726520) ───────────────────
    "8726520": {
        "low":              {2020: 0.05, 2030: 0.10, 2040: 0.14, 2050: 0.19, 2060: 0.22, 2070: 0.26, 2080: 0.28, 2090: 0.30, 2100: 0.31},
        "intermediate_low": {2020: 0.06, 2030: 0.12, 2040: 0.18, 2050: 0.25, 2060: 0.33, 2070: 0.40, 2080: 0.47, 2090: 0.54, 2100: 0.61},
        "intermediate":     {2020: 0.07, 2030: 0.14, 2040: 0.22, 2050: 0.33, 2060: 0.46, 2070: 0.59, 2080: 0.74, 2090: 0.90, 2100: 1.07},
        "intermediate_high":{2020: 0.08, 2030: 0.17, 2040: 0.28, 2050: 0.43, 2060: 0.60, 2070: 0.80, 2080: 1.01, 2090: 1.24, 2100: 1.49},
        "high":             {2020: 0.09, 2030: 0.19, 2040: 0.33, 2050: 0.51, 2060: 0.73, 2070: 0.98, 2080: 1.25, 2090: 1.54, 2100: 1.86},
        "extreme":          {2020: 0.13, 2030: 0.29, 2040: 0.54, 2050: 0.87, 2060: 1.27, 2070: 1.73, 2080: 2.27, 2090: 2.87, 2100: 3.53},
    },

    # ── Cedar Key, FL (Station 8727520) ────────────────────────────────────
    "8727520": {
        "low":              {2020: 0.05, 2030: 0.09, 2040: 0.13, 2050: 0.18, 2060: 0.21, 2070: 0.24, 2080: 0.27, 2090: 0.28, 2100: 0.29},
        "intermediate_low": {2020: 0.06, 2030: 0.11, 2040: 0.17, 2050: 0.24, 2060: 0.31, 2070: 0.38, 2080: 0.44, 2090: 0.51, 2100: 0.58},
        "intermediate":     {2020: 0.07, 2030: 0.13, 2040: 0.21, 2050: 0.31, 2060: 0.43, 2070: 0.56, 2080: 0.70, 2090: 0.85, 2100: 1.01},
        "intermediate_high":{2020: 0.08, 2030: 0.16, 2040: 0.26, 2050: 0.40, 2060: 0.56, 2070: 0.74, 2080: 0.94, 2090: 1.16, 2100: 1.38},
        "high":             {2020: 0.09, 2030: 0.18, 2040: 0.31, 2050: 0.48, 2060: 0.68, 2070: 0.90, 2080: 1.16, 2090: 1.44, 2100: 1.74},
        "extreme":          {2020: 0.12, 2030: 0.26, 2040: 0.49, 2050: 0.79, 2060: 1.15, 2070: 1.57, 2080: 2.06, 2090: 2.61, 2100: 3.22},
    },

    # ── Apalachicola, FL (Station 8728690) ─────────────────────────────────
    "8728690": {
        "low":              {2020: 0.05, 2030: 0.09, 2040: 0.14, 2050: 0.18, 2060: 0.21, 2070: 0.25, 2080: 0.27, 2090: 0.29, 2100: 0.30},
        "intermediate_low": {2020: 0.06, 2030: 0.12, 2040: 0.18, 2050: 0.25, 2060: 0.32, 2070: 0.39, 2080: 0.46, 2090: 0.53, 2100: 0.60},
        "intermediate":     {2020: 0.07, 2030: 0.14, 2040: 0.23, 2050: 0.33, 2060: 0.46, 2070: 0.60, 2080: 0.75, 2090: 0.91, 2100: 1.08},
        "intermediate_high":{2020: 0.08, 2030: 0.17, 2040: 0.29, 2050: 0.44, 2060: 0.61, 2070: 0.81, 2080: 1.03, 2090: 1.26, 2100: 1.51},
        "high":             {2020: 0.09, 2030: 0.19, 2040: 0.34, 2050: 0.52, 2060: 0.74, 2070: 0.99, 2080: 1.27, 2090: 1.57, 2100: 1.89},
        "extreme":          {2020: 0.13, 2030: 0.29, 2040: 0.55, 2050: 0.89, 2060: 1.29, 2070: 1.77, 2080: 2.31, 2090: 2.92, 2100: 3.59},
    },

    # ── Pensacola, FL (Station 8729840) ────────────────────────────────────
    "8729840": {
        "low":              {2020: 0.05, 2030: 0.10, 2040: 0.15, 2050: 0.19, 2060: 0.23, 2070: 0.27, 2080: 0.29, 2090: 0.31, 2100: 0.32},
        "intermediate_low": {2020: 0.06, 2030: 0.12, 2040: 0.19, 2050: 0.26, 2060: 0.34, 2070: 0.42, 2080: 0.49, 2090: 0.57, 2100: 0.64},
        "intermediate":     {2020: 0.07, 2030: 0.15, 2040: 0.24, 2050: 0.35, 2060: 0.48, 2070: 0.63, 2080: 0.79, 2090: 0.96, 2100: 1.14},
        "intermediate_high":{2020: 0.08, 2030: 0.18, 2040: 0.30, 2050: 0.46, 2060: 0.65, 2070: 0.87, 2080: 1.10, 2090: 1.36, 2100: 1.62},
        "high":             {2020: 0.09, 2030: 0.20, 2040: 0.36, 2050: 0.55, 2060: 0.79, 2070: 1.06, 2080: 1.35, 2090: 1.67, 2100: 2.01},
        "extreme":          {2020: 0.13, 2030: 0.31, 2040: 0.58, 2050: 0.94, 2060: 1.37, 2070: 1.87, 2080: 2.45, 2090: 3.09, 2100: 3.81},
    },

    # ── Fernandina Beach, FL (Station 8720218) ─────────────────────────────
    "8720218": {
        "low":              {2020: 0.05, 2030: 0.10, 2040: 0.14, 2050: 0.19, 2060: 0.23, 2070: 0.26, 2080: 0.29, 2090: 0.31, 2100: 0.32},
        "intermediate_low": {2020: 0.06, 2030: 0.12, 2040: 0.18, 2050: 0.25, 2060: 0.33, 2070: 0.41, 2080: 0.48, 2090: 0.56, 2100: 0.63},
        "intermediate":     {2020: 0.07, 2030: 0.14, 2040: 0.23, 2050: 0.34, 2060: 0.47, 2070: 0.62, 2080: 0.77, 2090: 0.94, 2100: 1.11},
        "intermediate_high":{2020: 0.08, 2030: 0.17, 2040: 0.29, 2050: 0.44, 2060: 0.62, 2070: 0.83, 2080: 1.05, 2090: 1.30, 2100: 1.55},
        "high":             {2020: 0.09, 2030: 0.20, 2040: 0.34, 2050: 0.53, 2060: 0.76, 2070: 1.02, 2080: 1.30, 2090: 1.61, 2100: 1.94},
        "extreme":          {2020: 0.13, 2030: 0.30, 2040: 0.56, 2050: 0.91, 2060: 1.32, 2070: 1.81, 2080: 2.37, 2090: 2.99, 2100: 3.68},
    },

    # ── Brunswick, GA (Station 8679511) ────────────────────────────────────
    "8679511": {
        "low":              {2020: 0.05, 2030: 0.10, 2040: 0.14, 2050: 0.19, 2060: 0.23, 2070: 0.27, 2080: 0.29, 2090: 0.31, 2100: 0.32},
        "intermediate_low": {2020: 0.06, 2030: 0.12, 2040: 0.18, 2050: 0.25, 2060: 0.33, 2070: 0.41, 2080: 0.49, 2090: 0.57, 2100: 0.64},
        "intermediate":     {2020: 0.07, 2030: 0.14, 2040: 0.23, 2050: 0.34, 2060: 0.47, 2070: 0.62, 2080: 0.78, 2090: 0.95, 2100: 1.13},
        "intermediate_high":{2020: 0.08, 2030: 0.17, 2040: 0.29, 2050: 0.45, 2060: 0.63, 2070: 0.84, 2080: 1.07, 2090: 1.31, 2100: 1.57},
        "high":             {2020: 0.09, 2030: 0.20, 2040: 0.35, 2050: 0.54, 2060: 0.77, 2070: 1.03, 2080: 1.31, 2090: 1.62, 2100: 1.96},
        "extreme":          {2020: 0.13, 2030: 0.30, 2040: 0.57, 2050: 0.92, 2060: 1.34, 2070: 1.83, 2080: 2.40, 2090: 3.03, 2100: 3.73},
    },

    # ── Charleston, SC (Station 8665530) ───────────────────────────────────
    "8665530": {
        "low":              {2020: 0.06, 2030: 0.11, 2040: 0.17, 2050: 0.23, 2060: 0.28, 2070: 0.33, 2080: 0.37, 2090: 0.40, 2100: 0.42},
        "intermediate_low": {2020: 0.07, 2030: 0.14, 2040: 0.22, 2050: 0.31, 2060: 0.41, 2070: 0.51, 2080: 0.60, 2090: 0.69, 2100: 0.78},
        "intermediate":     {2020: 0.08, 2030: 0.17, 2040: 0.28, 2050: 0.42, 2060: 0.60, 2070: 0.79, 2080: 1.00, 2090: 1.22, 2100: 1.44},
        "intermediate_high":{2020: 0.09, 2030: 0.21, 2040: 0.36, 2050: 0.56, 2060: 0.79, 2070: 1.05, 2080: 1.34, 2090: 1.65, 2100: 1.97},
        "high":             {2020: 0.10, 2030: 0.24, 2040: 0.43, 2050: 0.68, 2060: 0.97, 2070: 1.30, 2080: 1.67, 2090: 2.07, 2100: 2.48},
        "extreme":          {2020: 0.15, 2030: 0.37, 2040: 0.70, 2050: 1.14, 2060: 1.67, 2070: 2.29, 2080: 3.00, 2090: 3.79, 2100: 4.65},
    },

    # ── Eagle Point (Galveston Bay), TX (Station 8771013) ──────────────────
    "8771013": {
        "low":              {2020: 0.11, 2030: 0.21, 2040: 0.32, 2050: 0.43, 2060: 0.54, 2070: 0.63, 2080: 0.71, 2090: 0.77, 2100: 0.81},
        "intermediate_low": {2020: 0.12, 2030: 0.23, 2040: 0.37, 2050: 0.52, 2060: 0.68, 2070: 0.84, 2080: 1.00, 2090: 1.16, 2100: 1.31},
        "intermediate":     {2020: 0.13, 2030: 0.27, 2040: 0.43, 2050: 0.63, 2060: 0.87, 2070: 1.13, 2080: 1.41, 2090: 1.71, 2100: 2.03},
        "intermediate_high":{2020: 0.14, 2030: 0.31, 2040: 0.52, 2050: 0.77, 2060: 1.08, 2070: 1.42, 2080: 1.80, 2090: 2.21, 2100: 2.64},
        "high":             {2020: 0.15, 2030: 0.35, 2040: 0.60, 2050: 0.92, 2060: 1.30, 2070: 1.72, 2080: 2.20, 2090: 2.72, 2100: 3.26},
        "extreme":          {2020: 0.20, 2030: 0.50, 2040: 0.93, 2050: 1.49, 2060: 2.16, 2070: 2.95, 2080: 3.84, 2090: 4.83, 2100: 5.91},
    },

    # ── Grand Isle, LA (Station 8761724) ───────────────────────────────────
    "8761724": {
        "low":              {2020: 0.13, 2030: 0.25, 2040: 0.37, 2050: 0.50, 2060: 0.62, 2070: 0.72, 2080: 0.81, 2090: 0.87, 2100: 0.92},
        "intermediate_low": {2020: 0.14, 2030: 0.28, 2040: 0.44, 2050: 0.61, 2060: 0.80, 2070: 0.99, 2080: 1.17, 2090: 1.36, 2100: 1.54},
        "intermediate":     {2020: 0.16, 2030: 0.32, 2040: 0.52, 2050: 0.76, 2060: 1.04, 2070: 1.35, 2080: 1.69, 2090: 2.06, 2100: 2.44},
        "intermediate_high":{2020: 0.17, 2030: 0.38, 2040: 0.63, 2050: 0.95, 2060: 1.32, 2070: 1.74, 2080: 2.20, 2090: 2.70, 2100: 3.22},
        "high":             {2020: 0.18, 2030: 0.43, 2040: 0.74, 2050: 1.13, 2060: 1.60, 2070: 2.12, 2080: 2.71, 2090: 3.35, 2100: 4.01},
        "extreme":          {2020: 0.25, 2030: 0.61, 2040: 1.13, 2050: 1.82, 2060: 2.63, 2070: 3.58, 2080: 4.65, 2090: 5.84, 2100: 7.11},
    },
}

# ---------------------------------------------------------------------------
# Station metadata
# ---------------------------------------------------------------------------
SLR_STATION_METADATA: Dict[str, Dict[str, str]] = {
    "8724580": {"name": "Key West, FL",                    "region": "Florida Keys"},
    "8723970": {"name": "Vaca Key (Marathon), FL",         "region": "Florida Keys"},
    "8722670": {"name": "Lake Worth Pier, FL",              "region": "SE Florida"},
    "8721604": {"name": "Canaveral Harbor, FL",             "region": "East-Central Florida"},
    "8726384": {"name": "Port Manatee, FL",                 "region": "Tampa Bay"},
    "8726520": {"name": "St. Petersburg, FL",               "region": "Tampa Bay"},
    "8727520": {"name": "Cedar Key, FL",                    "region": "Big Bend / Nature Coast"},
    "8728690": {"name": "Apalachicola, FL",                 "region": "NW Florida Panhandle"},
    "8729840": {"name": "Pensacola, FL",                    "region": "NW Florida Panhandle"},
    "8720218": {"name": "Fernandina Beach, FL",             "region": "NE Florida"},
    "8679511": {"name": "Brunswick, GA",                    "region": "SE Georgia"},
    "8665530": {"name": "Charleston, SC",                   "region": "South Carolina"},
    "8771013": {"name": "Eagle Point (Galveston Bay), TX",  "region": "Texas Gulf Coast"},
    "8761724": {"name": "Grand Isle, LA",                   "region": "Louisiana Gulf Coast"},
}


# ---------------------------------------------------------------------------
# Config dataclass  (standalone — no storm_surge_wizard dependency)
# ---------------------------------------------------------------------------

@dataclass
class SLRConfig:
    """Sea Level Rise configuration for slr_wizard.engine.

    Standalone version — no dependency on storm_surge_wizard.

    Attributes
    ----------
    enabled : bool
        When ``True``, the SLR adjustment is applied.
    scenario : str
        NOAA TR-083 scenario name or alias (default ``"intermediate"``).
    target_year : int
        Projection horizon year, 2020–2100.
    station_id : str
        NOAA CO-OPS station ID for RSLR lookup.
    override_slr_m : float | None
        When set, bypasses the lookup table and uses this value (metres).
    apply_to_all_scenarios : bool
        When ``True``, the SLR offset is added to every scenario.
    notes : str
        Free-text notes for output metadata.
    """
    enabled: bool = False
    scenario: str = "intermediate"
    target_year: int = 2100
    station_id: str = ""
    override_slr_m: Optional[float] = None
    apply_to_all_scenarios: bool = True
    notes: str = ""


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def resolve_slr_scenario(name: str) -> str:
    """Return the canonical SLR scenario name, resolving common aliases.

    Parameters
    ----------
    name : str
        Scenario name or alias (case-insensitive).

    Returns
    -------
    str
        Canonical scenario from :data:`SLR_SCENARIO_NAMES`.

    Raises
    ------
    ValueError
        When ``name`` cannot be resolved.
    """
    key = (name or "").strip().lower()
    resolved = SLR_SCENARIO_ALIASES.get(key)
    if resolved is None:
        raise ValueError(
            f"Unknown SLR scenario '{name}'. "
            f"Valid names: {', '.join(SLR_SCENARIO_NAMES)}. "
            f"Aliases: {', '.join(sorted(SLR_SCENARIO_ALIASES))}."
        )
    return resolved


def _interpolate_slr(table: Dict[int, float], target_year: int) -> float:
    """Linearly interpolate from a ``{year: rise_m}`` dict to ``target_year``."""
    years = sorted(table.keys())
    if not years:
        return 0.0
    y = int(target_year)
    if y <= years[0]:
        return float(table[years[0]])
    if y >= years[-1]:
        return float(table[years[-1]])
    for i in range(len(years) - 1):
        y0, y1 = years[i], years[i + 1]
        if y0 <= y <= y1:
            v0, v1 = float(table[y0]), float(table[y1])
            return v0 + (v1 - v0) * (y - y0) / (y1 - y0)
    return float(table[years[-1]])


def get_slr_projection(
    station_id: str,
    *,
    target_year: int,
    scenario: str = "intermediate",
) -> float:
    """Return projected RSLR (metres) for a station, scenario, and year.

    Parameters
    ----------
    station_id : str
        NOAA CO-OPS station ID (e.g. ``"8724580"`` for Key West, FL).
    target_year : int
        Projection year (2020–2100).
    scenario : str
        SLR scenario name or alias (default ``"intermediate"``).

    Returns
    -------
    float
        Projected RSLR in metres above the 2000 baseline.

    Raises
    ------
    ValueError
        When *scenario* is not recognised.
    """
    canonical = resolve_slr_scenario(scenario)
    sid = str(station_id).strip()
    station_data = SLR_PROJECTIONS.get(sid)
    if station_data is None:
        _log.warning(
            "Station '%s' not in SLR table; falling back to Key West proxy.", sid
        )
        station_data = SLR_PROJECTIONS["8724580"]
    scenario_table = station_data.get(canonical)
    if scenario_table is None:
        raise ValueError(
            f"Scenario '{canonical}' not found for station '{sid}'. "
            f"Available: {', '.join(sorted(station_data.keys()))}."
        )
    result = _interpolate_slr(scenario_table, target_year)
    _log.debug(
        "SLR: station=%s scenario=%s year=%d → %.4f m (%.4f ft)",
        sid, canonical, target_year, result, result * 3.28084,
    )
    return round(result, 6)


def resolve_slr_offset(slr_cfg: SLRConfig) -> Tuple[float, dict]:
    """Resolve the SLR vertical offset (metres) from an :class:`SLRConfig`.

    Parameters
    ----------
    slr_cfg : SLRConfig
        Populated SLR configuration object.

    Returns
    -------
    tuple[float, dict]
        ``(slr_m, meta)`` — the SLR offset in metres and a provenance dict.
    """
    meta: dict = {
        "enabled": slr_cfg.enabled,
        "scenario": slr_cfg.scenario,
        "target_year": slr_cfg.target_year,
        "station_id": slr_cfg.station_id,
        "slr_m": None,
        "slr_ft": None,
        "method": "none",
        "noaa_tr083_reference": "Sweet et al. (2022) NOAA TR NOS CO-OPS 083",
        "notes": slr_cfg.notes,
    }

    if not slr_cfg.enabled:
        meta["slr_m"] = 0.0
        meta["slr_ft"] = 0.0
        return 0.0, meta

    if slr_cfg.override_slr_m is not None:
        slr_m = float(slr_cfg.override_slr_m)
        meta.update({
            "slr_m": round(slr_m, 6),
            "slr_ft": round(slr_m * 3.28084, 6),
            "method": "override",
        })
        _log.info("SLR override: %.4f m (station=%s).", slr_m, slr_cfg.station_id)
        return slr_m, meta

    canonical = resolve_slr_scenario(slr_cfg.scenario)
    station_meta = SLR_STATION_METADATA.get(slr_cfg.station_id, {})
    slr_m = get_slr_projection(
        slr_cfg.station_id,
        target_year=slr_cfg.target_year,
        scenario=canonical,
    )
    meta.update({
        "scenario": canonical,
        "slr_m": round(slr_m, 6),
        "slr_ft": round(slr_m * 3.28084, 6),
        "method": "noaa_tr083_table",
        "station_name": station_meta.get("name", slr_cfg.station_id),
        "station_region": station_meta.get("region", ""),
    })
    _log.info(
        "SLR: station=%s (%s), scenario=%s, year=%d → %.4f m (%.4f ft).",
        slr_cfg.station_id,
        station_meta.get("name", "unknown"),
        canonical,
        slr_cfg.target_year,
        slr_m,
        slr_m * 3.28084,
    )
    return slr_m, meta


def get_slr_sensitivity(
    station_id: str,
    *,
    target_year: int,
) -> Dict[str, float]:
    """Return SLR projections (metres) across all 6 scenarios for a station/year.

    Parameters
    ----------
    station_id : str
        NOAA CO-OPS station ID.
    target_year : int
        Projection year.

    Returns
    -------
    dict[str, float]
        ``{scenario_name: slr_m}`` for all 6 canonical scenarios.
    """
    return {
        scenario: get_slr_projection(station_id, target_year=target_year, scenario=scenario)
        for scenario in SLR_SCENARIO_NAMES
    }


def list_slr_scenarios() -> List[Dict[str, object]]:
    """Return a list of available SLR scenarios with 2100 global-mean references.

    Returns
    -------
    list[dict]
        Keys: ``name``, ``description``, ``global_mean_2100_m``, ``global_mean_2100_ft``.
    """
    descriptions = {
        "low": "Low (0.3 m / 1 ft global mean by 2100). Very low emissions / low ice-sheet contribution.",
        "intermediate_low": "Intermediate-Low (0.56 m / 1.8 ft). Below IPCC central estimate.",
        "intermediate": "Intermediate (1.0 m / 3.3 ft). FEMA/NOAA recommended planning baseline.",
        "intermediate_high": "Intermediate-High (1.5 m / 4.9 ft). Partial ice-sheet contribution.",
        "high": "High (2.0 m / 6.6 ft). High emissions, significant ice-sheet loss.",
        "extreme": "Extreme (3.21 m / 10.5 ft). Low-probability, high-consequence scenario.",
    }
    result = []
    for name in SLR_SCENARIO_NAMES:
        gm = SLR_GLOBAL_2100_M[name]
        result.append({
            "name": name,
            "description": descriptions.get(name, ""),
            "global_mean_2100_m": gm,
            "global_mean_2100_ft": round(gm * 3.28084, 3),
        })
    return result


def list_slr_stations() -> List[Dict[str, str]]:
    """Return a list of NOAA CO-OPS stations with built-in SLR projection tables.

    Returns
    -------
    list[dict]
        Keys: ``station_id``, ``name``, ``region``.
    """
    return [
        {"station_id": sid, **meta}
        for sid, meta in SLR_STATION_METADATA.items()
    ]
