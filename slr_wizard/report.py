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
report.py — JSON and PDF report generation for the SLR Wizard.

Produces:
  - Structured JSON run report (always)
  - Human-readable PDF summary (when reportlab is available)
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import __version__

log = logging.getLogger(__name__)

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
    )
    _REPORTLAB_OK = True
except ImportError:
    _REPORTLAB_OK = False
    log.debug("reportlab not available — PDF reports disabled.")

# ---------------------------------------------------------------------------
# Report schema version
# ---------------------------------------------------------------------------
REPORT_SCHEMA_VERSION = "1.0.0"

CVG_HEADER = (
    "© Clearview Geographic LLC — Proprietary | "
    "Author: Alex Zelenski, GISP | "
    "azelenski@clearviewgeographic.com | 386-957-2314 | "
    "clearviewgeographic.com"
)

NOAA_REF = (
    "Sweet, W.V., B.D. Hamlington, R.E. Kopp et al. (2022). "
    "Global and Regional Sea Level Rise Scenarios for the United States. "
    "NOAA Technical Report NOS CO-OPS 083."
)


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------

def build_json_report(
    result,          # InundationResult
    config,          # SLRWizardConfig
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Build the complete JSON report dictionary."""
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "tool": "CVG SLR Wizard",
        "tool_version": __version__,
        "generated_utc": datetime.utcnow().isoformat() + "Z",
        "copyright": CVG_HEADER,
        "references": [NOAA_REF],
        "run": result.to_dict(),
        "config": config.to_dict(),
    }
    if extra:
        report.update(extra)
    return report


def write_json_report(
    result,
    config,
    output_path: str | Path,
    extra: Optional[Dict] = None,
) -> None:
    """Serialize the JSON report to *output_path*."""
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    report = build_json_report(result, config, extra)
    with p.open("w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)
    log.info("JSON report written → %s", p)


# ---------------------------------------------------------------------------
# PDF report
# ---------------------------------------------------------------------------

def write_pdf_report(
    result,
    config,
    output_path: str | Path,
) -> bool:
    """Write a PDF summary report. Returns True on success."""
    if not _REPORTLAB_OK:
        log.warning("reportlab not installed — skipping PDF generation.")
        return False

    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(p),
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("<b>CVG SLR Wizard — Inundation Analysis Report</b>", styles["Title"]))
    story.append(Paragraph(CVG_HEADER, styles["Normal"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.darkblue))
    story.append(Spacer(1, 0.1 * inch))

    # ── Run summary ──────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Run Summary</b>", styles["Heading2"]))
    proj_name = config.metadata.project_name or "—"
    analyst = config.metadata.analyst or "—"
    summary_data = [
        ["Project", proj_name],
        ["Analyst", analyst],
        ["Run ID", result.run_id],
        ["Generated (UTC)", datetime.utcnow().strftime("%Y-%m-%d %H:%M")],
        ["Tool Version", __version__],
    ]
    story.append(_make_table(summary_data))
    story.append(Spacer(1, 0.1 * inch))

    # ── Projection parameters ────────────────────────────────────────────────
    story.append(Paragraph("<b>SLR Projection Parameters</b>", styles["Heading2"]))
    proj_data = [
        ["NOAA Scenario", config.projection.scenario.replace("_", " ").title()],
        ["Target Year", str(config.projection.target_year)],
        ["Baseline Datum", config.projection.baseline_datum],
        ["NOAA Station", config.inputs.noaa_station_id or "National Average"],
        ["SLR Offset (ft)", f"{result.slr_offset_ft:.3f}"],
        ["Datum Shift (ft)", f"{result.datum_shift_ft:.3f}"],
        ["Water Surface NAVD88 (ft)", f"{result.water_surface_navd88_ft:.3f}"],
    ]
    story.append(_make_table(proj_data))
    story.append(Spacer(1, 0.1 * inch))

    # ── Inundation statistics ────────────────────────────────────────────────
    story.append(Paragraph("<b>Inundation Statistics</b>", styles["Heading2"]))
    inun_data = [
        ["Inundated Cells", f"{result.inundated_cells:,}"],
        ["Total Valid Cells", f"{result.total_cells:,}"],
        ["Inundated Area (%)", f"{result.inundated_pct:.1f}%"],
        ["Inundated Area (m²)", f"{result.inundated_area_m2:,.0f}"],
        ["Max Depth (ft)", f"{result.max_depth_ft:.2f}"],
        ["Mean Depth (ft)", f"{result.mean_depth_ft:.2f}"],
        ["Processing Time (s)", f"{result.elapsed_sec:.1f}"],
    ]
    story.append(_make_table(inun_data))
    story.append(Spacer(1, 0.1 * inch))

    # ── Output files ─────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Output Files</b>", styles["Heading2"]))
    out_data = [
        ["Depth Grid", result.depth_grid_path or "—"],
        ["Extent Raster", result.extent_raster_path or "—"],
        ["Extent Vector", result.extent_vector_path or "—"],
    ]
    story.append(_make_table(out_data))
    story.append(Spacer(1, 0.1 * inch))

    # ── QA flags ────────────────────────────────────────────────────────────
    if result.qa_flags:
        story.append(Paragraph("<b>QA Flags</b>", styles["Heading2"]))
        for flag in result.qa_flags:
            story.append(Paragraph(f"• {flag}", styles["Normal"]))
        story.append(Spacer(1, 0.1 * inch))

    # ── Reference ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Paragraph("<b>Reference</b>", styles["Heading3"]))
    story.append(Paragraph(NOAA_REF, styles["Normal"]))

    doc.build(story)
    log.info("PDF report written → %s", p)
    return True


def _make_table(data: List[List[str]]) -> "Table":
    """Build a two-column key/value table."""
    table = Table(data, colWidths=[2.5 * inch, 4.5 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8F0FE")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


# ---------------------------------------------------------------------------
# Combined write
# ---------------------------------------------------------------------------

def write_reports(result, config, output_dir: str | Path) -> Dict[str, str]:
    """Write all configured reports (JSON + optional PDF). Returns paths dict."""
    from .paths import get_report_path
    out: Dict[str, str] = {}
    scenario = config.projection.scenario
    year = config.projection.target_year
    prefix = config.output.output_prefix

    if config.output.generate_json_report:
        json_path = get_report_path(prefix, scenario, year, output_dir, "json")
        write_json_report(result, config, json_path)
        out["json"] = str(json_path)

    if config.output.generate_pdf_report:
        pdf_path = get_report_path(prefix, scenario, year, output_dir, "pdf")
        success = write_pdf_report(result, config, pdf_path)
        if success:
            out["pdf"] = str(pdf_path)

    return out
