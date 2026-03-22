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
import time
import pytest
from slr_wizard.monitoring import ResourceSnapshot, PerformanceTracker, take_snapshot, timed_stage


class TestResourceSnapshot:
    def test_default_fields_zero(self):
        s = ResourceSnapshot()
        assert s.cpu_pct == 0.0
        assert s.ram_used_mb == 0.0
        assert s.ram_total_mb == 0.0
        assert s.disk_free_gb == 0.0
        assert s.elapsed_sec == 0.0

    def test_timestamp_recent(self):
        b = time.time()
        s = ResourceSnapshot()
        a = time.time()
        assert b <= s.timestamp <= a

    def test_ram_pct_zero_total_zero(self):
        assert ResourceSnapshot(ram_used_mb=0, ram_total_mb=0).ram_used_pct == 0.0

    def test_ram_pct_fifty(self):
        r = ResourceSnapshot(ram_used_mb=512, ram_total_mb=1024)
        assert abs(r.ram_used_pct - 50) < 0.01

    def test_ram_pct_hundred(self):
        r = ResourceSnapshot(ram_used_mb=1024, ram_total_mb=1024)
        assert abs(r.ram_used_pct - 100) < 0.01

    def test_to_dict_keys(self):
        d = ResourceSnapshot(cpu_pct=25, ram_used_mb=500, ram_total_mb=1000).to_dict()
        expected_keys = {'timestamp', 'cpu_pct', 'ram_used_mb', 'ram_total_mb', 'ram_used_pct', 'disk_free_gb', 'elapsed_sec'}
        assert expected_keys == set(d)

    def test_to_dict_rounds_cpu(self):
        v = ResourceSnapshot(cpu_pct=25.123456).to_dict()['cpu_pct']
        assert v == round(25.123456, 1)

    def test_to_dict_rounds_elapsed(self):
        v = ResourceSnapshot(elapsed_sec=1.2345678).to_dict()['elapsed_sec']
        assert v == round(1.2345678, 3)

    def test_to_dict_ram_pct_derived(self):
        d = ResourceSnapshot(ram_used_mb=256, ram_total_mb=512).to_dict()
        assert abs(d['ram_used_pct'] - 50.0) < 0.1


class TestTakeSnapshot:
    def test_returns_instance(self):
        assert isinstance(take_snapshot(), ResourceSnapshot)

    def test_elapsed_zero_no_start(self):
        assert take_snapshot(start_time=None).elapsed_sec == 0.0

    def test_elapsed_positive_with_start(self):
        assert take_snapshot(start_time=time.time() - 1.0).elapsed_sec >= 1.0

    def test_timestamp_current(self):
        b = time.time()
        s = take_snapshot()
        a = time.time()
        assert b <= s.timestamp <= a


class TestPerformanceTracker:
    def test_label_stored(self):
        assert PerformanceTracker('my_op').label == 'my_op'

    def test_default_label(self):
        assert PerformanceTracker().label == 'operation'

    def test_start_snap_none_before_enter(self):
        assert PerformanceTracker('t').start_snap is None

    def test_end_snap_none_before_enter(self):
        assert PerformanceTracker('t').end_snap is None

    def test_start_snap_set_in_ctx(self):
        with PerformanceTracker('c') as t:
            assert t.start_snap is not None

    def test_end_snap_set_after_exit(self):
        with PerformanceTracker('c') as t:
            pass
        assert t.end_snap is not None

    def test_elapsed_non_negative(self):
        with PerformanceTracker('e') as t:
            time.sleep(0.01)
        assert t.elapsed_sec >= 0.0

    def test_elapsed_measures_time(self):
        with PerformanceTracker('sl') as t:
            time.sleep(0.05)
        assert t.elapsed_sec >= 0.04

    def test_elapsed_live_before_exit(self):
        tr = PerformanceTracker('lv')
        tr.__enter__()
        assert tr.elapsed_sec >= 0.0
        tr.__exit__(None, None, None)

    def test_to_dict_keys(self):
        with PerformanceTracker('d') as t:
            pass
        d = t.to_dict()
        for k in ('label', 'elapsed_sec', 'start', 'end'):
            assert k in d

    def test_to_dict_label_matches(self):
        with PerformanceTracker('lb') as t:
            pass
        assert t.to_dict()['label'] == 'lb'

    def test_to_dict_elapsed_non_negative(self):
        with PerformanceTracker('ev') as t:
            pass
        assert t.to_dict()['elapsed_sec'] >= 0.0

    def test_to_dict_start_is_dict(self):
        with PerformanceTracker('sd') as t:
            pass
        assert isinstance(t.to_dict()['start'], dict)

    def test_to_dict_end_is_dict(self):
        with PerformanceTracker('ed') as t:
            pass
        assert isinstance(t.to_dict()['end'], dict)


class TestTimedStage:
    def test_yields_tracker(self):
        with timed_stage('s') as tr:
            assert isinstance(tr, PerformanceTracker)

    def test_label_propagated(self):
        with timed_stage('lbl') as t:
            assert t.label == 'lbl'

    def test_elapsed_after_sleep(self):
        with timed_stage('slp') as t:
            time.sleep(0.03)
        assert t.elapsed_sec >= 0.02

    def test_nested_independent(self):
        with timed_stage('o') as o:
            with timed_stage('i') as i:
                time.sleep(0.01)
        assert i.elapsed_sec <= o.elapsed_sec + 0.1

    def test_start_snap_populated(self):
        with timed_stage('sc') as t:
            pass
        assert t.start_snap is not None

    def test_end_snap_populated(self):
        with timed_stage('ec') as t:
            pass
        assert t.end_snap is not None
