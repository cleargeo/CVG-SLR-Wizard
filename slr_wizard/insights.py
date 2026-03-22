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
insights.py — Knowledge base and guidance lookup for the SLR Wizard.

Provides plain-language guidance, regulatory context, and planning
recommendations based on NOAA TR-083, FEMA guidelines, and CVG best
practices.  Supports both keyword search and structured topic lookup.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Knowledge base entries
# ---------------------------------------------------------------------------

@dataclass
class InsightEntry:
    """A single guidance entry in the SLR knowledge base."""
    topic: str
    title: str
    body: str
    tags: List[str] = field(default_factory=list)
    source: str = ""
    url: str = ""

    def matches(self, query: str) -> bool:
        q = query.lower()
        return (
            q in self.topic.lower()
            or q in self.title.lower()
            or q in self.body.lower()
            or any(q in t for t in self.tags)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "title": self.title,
            "body": self.body,
            "tags": self.tags,
            "source": self.source,
            "url": self.url,
        }


# ---------------------------------------------------------------------------
# Built-in knowledge base
# ---------------------------------------------------------------------------

_KB: List[InsightEntry] = [
    InsightEntry(
        topic="scenarios",
        title="NOAA TR-083 SLR Scenarios Overview",
        body=(
            "NOAA (2022) defines six relative sea level rise scenarios for CONUS:\n"
            "  • Low        — thermostatic expansion only (~0.3 m by 2100 globally)\n"
            "  • Intermediate-Low — moderate acceleration (~0.5 m by 2100)\n"
            "  • Intermediate — NOAA/FEMA recommended planning baseline (~1.0 m by 2100)\n"
            "  • Intermediate-High — accelerated ice melt (~1.5 m by 2100)\n"
            "  • High       — significant West Antarctic Ice Sheet contribution (~2.0 m by 2100)\n"
            "  • Extreme    — IPCC high-end scenario, low probability/high consequence (~2.5+ m)\n\n"
            "For general coastal planning, NOAA recommends the Intermediate scenario as "
            "the central estimate and High as the risk-informed upper bound.  FEMA's "
            "Hazard Mitigation Plan guidance suggests using Intermediate-High for "
            "long-horizon (50–100 yr) infrastructure decisions."
        ),
        tags=["scenarios", "noaa", "tr083", "planning", "intermediate", "high"],
        source="NOAA TR-083 (Sweet et al. 2022)",
        url="https://oceanservice.noaa.gov/hazards/sealevelrise/sealevelrise-tech-report.html",
    ),
    InsightEntry(
        topic="datum",
        title="Tidal Datum Considerations for SLR Analysis",
        body=(
            "SLR projections from NOAA TR-083 are expressed relative to the 2000 mean "
            "sea level (LMSL) baseline, not to NAVD88.  To map inundation on a DEM "
            "referenced to NAVD88, you must:\n"
            "  1. Determine the MLLW or MSL to NAVD88 datum separation at the study site\n"
            "     using NOAA VDatum (https://vdatum.noaa.gov).\n"
            "  2. Add the SLR offset (in ft, relative to 2000 MSL) to the datum-adjusted\n"
            "     water surface elevation.\n\n"
            "The SLR Wizard automates this via the vdatum module when a NOAA CO-OPS "
            "station ID is provided.  For areas without VDatum coverage, a manual "
            "datum offset may be entered."
        ),
        tags=["datum", "navd88", "mllw", "msl", "vdatum", "offset"],
        source="NOAA VDatum; NOAA TR-083",
        url="https://vdatum.noaa.gov",
    ),
    InsightEntry(
        topic="bathtub_model",
        title="Bathtub Inundation Model Limitations",
        body=(
            "The bathtub model (simple fill below a water surface elevation) is a "
            "commonly used screening-level tool for SLR inundation mapping.  Key "
            "limitations to communicate to stakeholders:\n"
            "  1. Static, not dynamic — does not model wave action, tidal fluctuations,\n"
            "     storm surge, or hydrodynamic conveyance.\n"
            "  2. Connectivity — without a connectivity filter, all low-lying cells are\n"
            "     flagged regardless of hydrologic connection to the coast.  The SLR\n"
            "     Wizard applies a queen-connectivity filter by default.\n"
            "  3. DEM accuracy — results are highly sensitive to DEM vertical accuracy.\n"
            "     Use bare-earth lidar (≤0.5 ft RMSE) where available.\n"
            "  4. Subsidence not captured — for high-subsidence areas (Gulf Coast, "
            "     Hampton Roads), local relative SLR rates may be substantially higher "
            "     than the NOAA station-average RSLR."
        ),
        tags=["bathtub", "model", "limitations", "connectivity", "dem", "accuracy"],
        source="NOAA Digital Coast; FEMA HMGP guidance",
    ),
    InsightEntry(
        topic="fema",
        title="FEMA Flood Map Modernization and SLR",
        body=(
            "FEMA's current FIRMs do not incorporate SLR projections.  FEMA's "
            "Hazard Mitigation Planning guidance (FEMA P-1058) recommends that "
            "communities consider future conditions, including SLR, when conducting "
            "risk assessments for long-lived infrastructure.\n\n"
            "Several states (FL, CA, NY, VA) have enacted SLR guidance or requirements "
            "for state-funded projects.  Florida Statute §380.093 (2023) requires "
            "local comprehensive plans to incorporate SLR projections from the NOAA "
            "Intermediate-High scenario as a minimum planning horizon."
        ),
        tags=["fema", "firm", "floodmap", "regulation", "florida", "statute", "planning"],
        source="FEMA P-1058; FL Stat. §380.093",
    ),
    InsightEntry(
        topic="uncertainty",
        title="Uncertainty in SLR Projections",
        body=(
            "The primary sources of uncertainty in NOAA TR-083 RSLR projections are:\n"
            "  1. Ice sheet dynamics — the marine ice sheet instability of the West\n"
            "     Antarctic Ice Sheet (WAIS) is the largest source of high-end uncertainty.\n"
            "  2. Vertical land motion (VLM) — subsidence (sediment compaction, groundwater\n"
            "     extraction, hydrocarbon production) can double or triple the global mean\n"
            "     SLR rate at specific coastal locations.\n"
            "  3. Ocean circulation — Changes in the Atlantic Meridional Overturning\n"
            "     Circulation (AMOC) can cause regional departures of ±0.1–0.3 m from\n"
            "     the global mean.\n"
            "  4. Decadal variability — short-term sea level variability (ENSO, PDO)\n"
            "     can temporarily mask or amplify long-term trends.\n\n"
            "Best practice: present inundation maps for at least three scenarios "
            "(Intermediate-Low, Intermediate, High) to bracket uncertainty."
        ),
        tags=["uncertainty", "wais", "vlm", "subsidence", "amoc", "ice", "range"],
        source="NOAA TR-083; IPCC AR6 Chapter 9",
    ),
    InsightEntry(
        topic="compound_flood",
        title="Compound Flooding: SLR + Storm Surge + Rainfall",
        body=(
            "Compound flooding occurs when multiple hazards co-occur or interact, "
            "amplifying impacts beyond what any single hazard would produce alone.  "
            "Common compound flood combinations:\n"
            "  • Storm surge + SLR — elevated baseline allows surge to penetrate further inland\n"
            "  • Storm surge + heavy rainfall — blocked drainage outlets prevent runoff\n"
            "    from escaping; urban flooding worsens\n"
            "  • High tides + heavy rain + SLR — nuisance/ 'sunny day' flooding\n\n"
            "When combining SLR with storm surge, add the SLR offset to the still-water "
            "elevation (SWE) used in the surge model, not to the peak depth.  Do NOT "
            "simply add independent return-period depths — this overstates the combined "
            "hazard.  Use a joint probability / multivariate analysis or the FEMA "
            "Coastal Flood Hazard Analysis (CFA) approach for rigorous compound estimates."
        ),
        tags=["compound", "storm_surge", "rainfall", "joint_probability", "nuisance", "tides"],
        source="NOAA; FEMA CFA; Moftakhari et al. (2017)",
    ),
    InsightEntry(
        topic="adaptation",
        title="Coastal Adaptation Strategies",
        body=(
            "Common adaptation strategies for communities facing SLR:\n"
            "  PROTECT: seawalls, revetments, living shorelines, natural-based solutions\n"
            "  ACCOMMODATE: elevate structures, update building codes, improve drainage\n"
            "  RETREAT: managed retreat / planned relocation from high-risk coastal areas\n"
            "  AVOID: update local land use regulations; discourage new development in\n"
            "         future inundation zones\n\n"
            "Planning horizon guidance (NOAA, FEMA):\n"
            "  • Short-term capital investments (≤20 yr): Intermediate-Low scenario\n"
            "  • Critical infrastructure (50 yr): Intermediate to Intermediate-High\n"
            "  • Long-lived assets / legacy infrastructure (100 yr): High to Extreme"
        ),
        tags=["adaptation", "protect", "accommodate", "retreat", "avoid", "strategy"],
        source="NOAA Coastal Adaptation; FEMA P-1058",
    ),
]


# ---------------------------------------------------------------------------
# Search / lookup API
# ---------------------------------------------------------------------------

def search_insights(query: str, max_results: int = 5) -> List[InsightEntry]:
    """Return up to *max_results* knowledge base entries matching *query*."""
    if not query.strip():
        return _KB[:max_results]
    results = [e for e in _KB if e.matches(query)]
    return results[:max_results]


def get_guidance(topic: str) -> Optional[InsightEntry]:
    """Return the first knowledge base entry for *topic*."""
    for e in _KB:
        if topic.lower() in e.topic.lower() or topic.lower() in [t.lower() for t in e.tags]:
            return e
    return None


def list_topics() -> List[str]:
    """Return all available knowledge base topics."""
    return [e.topic for e in _KB]


def get_scenario_description(scenario: str) -> str:
    """Return a short description for a NOAA TR-083 scenario name."""
    _descriptions = {
        "low":              "Low — thermostatic expansion only; lowest plausible trajectory",
        "intermediate_low": "Intermediate-Low — moderate acceleration; below-median outcome",
        "intermediate":     "Intermediate — NOAA/FEMA recommended planning baseline",
        "intermediate_high":"Intermediate-High — accelerated ice melt; risk-informed upper bound",
        "high":             "High — significant WAIS contribution; low-probability / high-consequence",
        "extreme":          "Extreme — IPCC high-end scenario; precautionary planning only",
    }
    return _descriptions.get(scenario.lower(), f"Unknown scenario: {scenario}")
