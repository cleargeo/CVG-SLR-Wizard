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
#               contact@clearviewgeographic.com (org)
# GitHub      : azelenski_cvg | clearview-geographic (Enterprise) | cleargeo (Public)
# Website     : https://www.clearviewgeographic.com
# License     : Proprietary -- CVG-ADF | See Software-Disclaimer-License-Header.md
# =============================================================================
from __future__ import annotations
import json
import pytest
from pathlib import Path
from slr_wizard.recovery import Stage, STAGE_ORDER, CheckpointManager, RecoveryManager, build_cache_key


class TestStageEnum:
    def test_stage_values_are_strings(self):
        for s in Stage:
            assert isinstance(s.value, str)

    def test_stage_order_starts_with_init(self):
        assert STAGE_ORDER[0] == Stage.INIT

    def test_stage_order_ends_with_done(self):
        assert STAGE_ORDER[-1] == Stage.DONE

    def test_all_stages_in_order(self):
        assert set(STAGE_ORDER) == set(Stage)


class TestCheckpointManager:
    def test_load_returns_false_when_no_file(self, tmp_path):
        cp = CheckpointManager(tmp_path / 'missing.json')
        assert cp.load() is False

    def test_save_and_load_round_trip(self, tmp_path):
        cp = CheckpointManager(tmp_path / 'cp.json')
        cp.set('key', 'value')
        cp2 = CheckpointManager(tmp_path / 'cp.json')
        assert cp2.load() is True
        assert cp2.get('key') == 'value'

    def test_load_returns_true_when_file_exists(self, tmp_path):
        p = tmp_path / 'cp.json'
        p.write_text('{}', encoding='utf-8')
        cp = CheckpointManager(p)
        assert cp.load() is True

    def test_get_returns_default_when_key_missing(self, tmp_path):
        cp = CheckpointManager(tmp_path / 'cp.json')
        assert cp.get('nonexistent', 42) == 42

    def test_set_persists_to_disk(self, tmp_path):
        p = tmp_path / 'cp.json'
        cp = CheckpointManager(p)
        cp.set('foo', 123)
        assert p.exists()
        data = json.loads(p.read_text(encoding='utf-8'))
        assert data['foo'] == 123

    def test_completed_stages_empty_initially(self, tmp_path):
        cp = CheckpointManager(tmp_path / 'cp.json')
        assert cp.completed_stages == []

    def test_mark_stage_complete_adds_to_list(self, tmp_path):
        cp = CheckpointManager(tmp_path / 'cp.json')
        cp.mark_stage_complete(Stage.INIT)
        assert Stage.INIT.value in cp.completed_stages

    def test_is_stage_complete_true_after_mark(self, tmp_path):
        cp = CheckpointManager(tmp_path / 'cp.json')
        cp.mark_stage_complete(Stage.LOAD_DEM)
        assert cp.is_stage_complete(Stage.LOAD_DEM) is True

    def test_is_stage_complete_false_for_unset(self, tmp_path):
        cp = CheckpointManager(tmp_path / 'cp.json')
        assert cp.is_stage_complete(Stage.REPORT) is False

    def test_mark_stage_complete_with_metadata(self, tmp_path):
        cp = CheckpointManager(tmp_path / 'cp.json')
        cp.mark_stage_complete(Stage.SLR_OFFSET, {'slr_ft': 2.5})
        meta = cp.get('stage_slr_offset_meta')
        assert meta['slr_ft'] == 2.5

    def test_mark_stage_complete_idempotent(self, tmp_path):
        cp = CheckpointManager(tmp_path / 'cp.json')
        cp.mark_stage_complete(Stage.INIT)
        cp.mark_stage_complete(Stage.INIT)
        assert cp.completed_stages.count(Stage.INIT.value) == 1

    def test_clear_removes_file(self, tmp_path):
        cp = CheckpointManager(tmp_path / 'cp.json')
        cp.set('x', 1)
        assert (tmp_path / 'cp.json').exists()
        cp.clear()
        assert not (tmp_path / 'cp.json').exists()

    def test_clear_resets_data(self, tmp_path):
        cp = CheckpointManager(tmp_path / 'cp.json')
        cp.set('x', 1)
        cp.clear()
        assert cp.get('x') is None

    def test_load_graceful_on_corrupt_file(self, tmp_path):
        p = tmp_path / 'bad.json'
        p.write_text('NOT JSON!!!', encoding='utf-8')
        cp = CheckpointManager(p)
        assert cp.load() is False


class TestBuildCacheKey:
    def test_returns_16_char_hex(self):
        key = build_cache_key({'scenario': 'intermediate', 'year': 2050})
        assert len(key) == 16
        assert all(c in '0123456789abcdef' for c in key)

    def test_same_dict_same_key(self):
        d = {'a': 1, 'b': 2}
        assert build_cache_key(d) == build_cache_key(d)

    def test_different_dicts_different_keys(self):
        k1 = build_cache_key({'a': 1})
        k2 = build_cache_key({'a': 2})
        assert k1 != k2

    def test_key_order_independent(self):
        k1 = build_cache_key({'a': 1, 'b': 2})
        k2 = build_cache_key({'b': 2, 'a': 1})
        assert k1 == k2
