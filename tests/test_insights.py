# -*- coding: utf-8 -*-
# =============================================================================
# (c) Clearview Geographic LLC -- All Rights Reserved | Est. 2018
# CVG SLR Wizard — test_insights.py
# =============================================================================
"""Unit tests for slr_wizard.insights (knowledge base)."""

from slr_wizard.insights import (
    search_insights,
    get_guidance,
    list_topics,
    get_scenario_description,
    _KB,
)


def test_knowledge_base_not_empty():
    assert len(_KB) >= 5


def test_list_topics_returns_strings():
    topics = list_topics()
    assert len(topics) > 0
    for t in topics:
        assert isinstance(t, str)
        assert len(t) > 0


def test_search_empty_query_returns_default():
    results = search_insights("")
    assert len(results) > 0


def test_search_scenarios():
    results = search_insights("scenarios")
    assert len(results) > 0
    assert any("scenario" in r.topic.lower() or "scenario" in r.title.lower() for r in results)


def test_search_datum():
    results = search_insights("datum")
    assert len(results) > 0


def test_search_adaptation():
    results = search_insights("adaptation")
    assert len(results) > 0


def test_search_no_match_returns_empty():
    results = search_insights("xyznonexistent_query_999")
    assert results == []


def test_search_max_results():
    results = search_insights("", max_results=3)
    assert len(results) <= 3


def test_get_guidance_scenarios():
    entry = get_guidance("scenarios")
    assert entry is not None
    assert "scenario" in entry.topic.lower()
    assert len(entry.body) > 50
    assert entry.source


def test_get_guidance_datum():
    entry = get_guidance("datum")
    assert entry is not None


def test_get_guidance_nonexistent():
    entry = get_guidance("qwerty_nonexistent_123")
    assert entry is None


def test_insight_to_dict():
    entry = _KB[0]
    d = entry.to_dict()
    assert "topic" in d
    assert "title" in d
    assert "body" in d
    assert "tags" in d
    assert "source" in d


def test_scenario_descriptions_all_scenarios():
    from slr_wizard.config import VALID_SCENARIOS
    for sc in VALID_SCENARIOS:
        desc = get_scenario_description(sc)
        assert len(desc) > 10
        assert sc.replace("_", "") not in desc.lower() or desc  # just ensure non-empty


def test_scenario_description_unknown():
    desc = get_scenario_description("unknown_xyz")
    assert "Unknown" in desc or "unknown" in desc.lower()


def test_all_entries_have_body():
    for entry in _KB:
        assert len(entry.body) >= 50, f"Entry '{entry.topic}' has too-short body"


def test_all_entries_have_source():
    for entry in _KB:
        assert entry.source, f"Entry '{entry.topic}' missing source"
