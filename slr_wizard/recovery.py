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
recovery.py — Checkpoint / restart system for the SLR Wizard.

Long-running batch jobs can be interrupted and resumed without reprocessing
already-completed stages.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Processing stages
# ---------------------------------------------------------------------------

class Stage(str, Enum):
    """SLR Wizard pipeline stages (in order)."""
    INIT          = "init"
    LOAD_DEM      = "load_dem"
    CLIP_AOI      = "clip_aoi"
    DATUM_SHIFT   = "datum_shift"
    SLR_OFFSET    = "slr_offset"
    INUNDATION    = "inundation"
    VECTORISE     = "vectorise"
    REPORT        = "report"
    DONE          = "done"

STAGE_ORDER: List[Stage] = [
    Stage.INIT, Stage.LOAD_DEM, Stage.CLIP_AOI,
    Stage.DATUM_SHIFT, Stage.SLR_OFFSET,
    Stage.INUNDATION, Stage.VECTORISE, Stage.REPORT, Stage.DONE,
]


# ---------------------------------------------------------------------------
# Checkpoint manager
# ---------------------------------------------------------------------------

class CheckpointManager:
    """Persist and load checkpoint data to/from JSON."""

    def __init__(self, checkpoint_path: str | Path) -> None:
        self.path = Path(checkpoint_path)
        self._data: Dict[str, Any] = {}

    def load(self) -> bool:
        """Load checkpoint from disk. Returns True if found."""
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as fh:
                    self._data = json.load(fh)
                log.info("Checkpoint loaded: %s", self.path)
                return True
            except Exception as exc:
                log.warning("Could not load checkpoint %s: %s", self.path, exc)
        return False

    def save(self) -> None:
        """Persist current checkpoint data to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def clear(self) -> None:
        """Delete the checkpoint file."""
        if self.path.exists():
            self.path.unlink()
        self._data = {}

    @property
    def completed_stages(self) -> List[str]:
        return self._data.get("completed_stages", [])

    def mark_stage_complete(self, stage: Stage, metadata: Optional[Dict] = None) -> None:
        completed = self.completed_stages
        if stage.value not in completed:
            completed.append(stage.value)
        self._data["completed_stages"] = completed
        self._data[f"stage_{stage.value}_ts"] = time.time()
        if metadata:
            self._data[f"stage_{stage.value}_meta"] = metadata
        self.save()
        log.info("Stage complete: %s", stage.value)

    def is_stage_complete(self, stage: Stage) -> bool:
        return stage.value in self.completed_stages


# ---------------------------------------------------------------------------
# Recovery manager
# ---------------------------------------------------------------------------

class RecoveryManager:
    """High-level resume logic wrapping :class:`CheckpointManager`."""

    def __init__(self, run_id: str, output_dir: str | Path) -> None:
        self.run_id = run_id
        from .paths import get_checkpoint_path
        cp_path = get_checkpoint_path(run_id, output_dir)
        self.checkpoint = CheckpointManager(cp_path)
        self._resumed = False

    def try_resume(self) -> bool:
        """Attempt to resume from an existing checkpoint."""
        found = self.checkpoint.load()
        if found and self.checkpoint.completed_stages:
            self._resumed = True
            log.info(
                "Resuming run '%s' from stage after: %s",
                self.run_id,
                self.checkpoint.completed_stages[-1],
            )
        return self._resumed

    def should_skip(self, stage: Stage) -> bool:
        """Return True if *stage* was already completed in a previous run."""
        return self._resumed and self.checkpoint.is_stage_complete(stage)

    def complete(self, stage: Stage, metadata: Optional[Dict] = None) -> None:
        self.checkpoint.mark_stage_complete(stage, metadata)

    def finish(self) -> None:
        """Mark the run as fully done and clean up the checkpoint file."""
        self.checkpoint.mark_stage_complete(Stage.DONE)
        self.checkpoint.clear()
        log.info("Run '%s' complete — checkpoint cleared.", self.run_id)


# ---------------------------------------------------------------------------
# Build a cache key for deduplication
# ---------------------------------------------------------------------------

def build_cache_key(config_dict: Dict) -> str:
    """Return a short hash of the config dict for caching purposes."""
    blob = json.dumps(config_dict, sort_keys=True).encode()
    return hashlib.sha256(blob).hexdigest()[:16]
