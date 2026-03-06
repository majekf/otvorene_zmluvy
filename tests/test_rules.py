"""
Unit tests for Phase 4 — Rule Builder (Pattern Engine).

Tests cover:
  - RuleEngine preset rules (threshold proximity, vendor concentration,
    fragmentation, overnight turnaround, new-vendor-large-contract,
    round-number clustering)
  - Severity scoring accumulation
  - Condition builder (AND/OR chaining, serialization)
  - API endpoints (/api/rules/presets, /api/rules/evaluate, /api/rules/custom)
"""

import json

import pytest

from src.models import Contract
from src.rules.engine import (
    RuleEngine,
    RuleResult,
    PRESET_RULES,
    _eval_threshold_proximity,
    _eval_vendor_concentration,
    _eval_fragmentation,
    _eval_overnight_turnaround,
    _eval_new_vendor_large_contract,
    _eval_round_number_clustering,
)
from src.rules.builder import Condition, ConditionGroup


# ── Fixtures ────────────────────────────────────────────────────────


def _c(**kw) -> Contract:
    """Shortcut to create a Contract with defaults."""
    defaults = {
        "contract_title": "Test",
        "buyer": "Institution A",
        "supplier": "Vendor X",
        "price_numeric_eur": 50_000.0,
        "published_date": "2026-01-15",
        "category": "IT",
        "award_type": "unknown",
    }
    defaults.update(kw)
    return Contract(**defaults)


# ── Threshold Proximity ──────────────────────────────────────────────


class TestThresholdProximity:
    """Contracts near a legal threshold should be flagged."""

    def test_flags_correctly(self):
        """Contract at 95% of limit is flagged."""
        contracts = [_c(contract_id="c1", price_numeric_eur=95_000)]  # 95% of 100k
        flags = _eval_threshold_proximity(contracts, threshold_eur=100_000, proximity_pct=10)
        assert len(flags) == 1
        assert flags[0].contract_id == "c1"
        assert flags[0].rule_id == "threshold_proximity"
        assert flags[0].severity > 0

    def test_ignores_low_value(self):
        """Contract at 50% of limit should NOT be flagged."""
        contracts = [_c(contract_id="c2", price_numeric_eur=50_000)]
        flags = _eval_threshold_proximity(contracts, threshold_eur=100_000, proximity_pct=10)
        assert len(flags) == 0

    def test_ignores_above_threshold(self):
        """Contract above threshold is not flagged."""
        contracts = [_c(contract_id="c3", price_numeric_eur=120_000)]
        flags = _eval_threshold_proximity(contracts, threshold_eur=100_000, proximity_pct=10)
        assert len(flags) == 0

    def test_ignores_none_price(self):
        """Contracts with no price are silently skipped."""
        contracts = [_c(contract_id="c4", price_numeric_eur=None)]
        flags = _eval_threshold_proximity(contracts, threshold_eur=100_000, proximity_pct=10)
        assert len(flags) == 0


# ── Vendor Concentration ─────────────────────────────────────────────


class TestVendorConcentration:
    """Flag when top-N vendors hold > X% of institution spend."""

    def test_flags_high_concentration(self):
        """Top vendor > 60% is flagged."""
        contracts = [
            _c(buyer="Inst", supplier="BigCo", price_numeric_eur=700_000),
            _c(buyer="Inst", supplier="SmallCo", price_numeric_eur=300_000),
        ]
        flags = _eval_vendor_concentration(contracts, top_n=1, max_share_pct=60)
        assert len(flags) == 1
        assert flags[0].vendor == "BigCo"
        assert flags[0].details["share_pct"] == 70.0

    def test_no_flag_below_threshold(self):
        """Evenly split spend should not be flagged at 60%."""
        contracts = [
            _c(buyer="Inst", supplier="A", price_numeric_eur=500_000),
            _c(buyer="Inst", supplier="B", price_numeric_eur=500_000),
        ]
        flags = _eval_vendor_concentration(contracts, top_n=1, max_share_pct=60)
        assert len(flags) == 0

    def test_multiple_institutions(self):
        """Flags are per-institution."""
        contracts = [
            _c(buyer="Inst1", supplier="BigCo", price_numeric_eur=900_000),
            _c(buyer="Inst1", supplier="SmallCo", price_numeric_eur=100_000),
            _c(buyer="Inst2", supplier="A", price_numeric_eur=500_000),
            _c(buyer="Inst2", supplier="B", price_numeric_eur=500_000),
        ]
        flags = _eval_vendor_concentration(contracts, top_n=1, max_share_pct=60)
        flagged_institutions = {f.institution for f in flags}
        assert "Inst1" in flagged_institutions
        assert "Inst2" not in flagged_institutions


# ── Fragmentation ────────────────────────────────────────────────────


class TestFragmentation:
    """Detect split procurement via many small contracts."""

    def test_detection(self):
        """10 contracts < 5k to same vendor flagged."""
        contracts = [
            _c(contract_id=f"f{i}", buyer="Inst", supplier="Vendor",
               price_numeric_eur=4_000)
            for i in range(10)
        ]
        flags = _eval_fragmentation(contracts, min_contracts=3, max_value_eur=5_000)
        assert len(flags) == 10  # one flag per contract

    def test_no_flag_few_contracts(self):
        """Only 2 small contracts — not enough for fragmentation."""
        contracts = [
            _c(contract_id=f"f{i}", buyer="Inst", supplier="Vendor",
               price_numeric_eur=4_000)
            for i in range(2)
        ]
        flags = _eval_fragmentation(contracts, min_contracts=3, max_value_eur=5_000)
        assert len(flags) == 0

    def test_no_flag_large_values(self):
        """Contracts above max_value_eur are not considered small."""
        contracts = [
            _c(contract_id=f"f{i}", buyer="Inst", supplier="Vendor",
               price_numeric_eur=100_000)
            for i in range(5)
        ]
        flags = _eval_fragmentation(contracts, min_contracts=3, max_value_eur=50_000)
        assert len(flags) == 0


# ── Overnight Turnaround ─────────────────────────────────────────────


class TestOvernightTurnaround:
    """Contracts signed and published very quickly."""

    def test_flags_fast_turnaround(self):
        """Concluded-to-published < 24h flagged."""
        contracts = [
            _c(contract_id="ot1",
               date_concluded="2026-01-15",
               date_published="2026-01-15"),
        ]
        flags = _eval_overnight_turnaround(contracts, max_hours=24)
        assert len(flags) == 1
        assert flags[0].details["hours"] == 0.0

    def test_no_flag_slow_turnaround(self):
        """Multi-day gap should not be flagged."""
        contracts = [
            _c(contract_id="ot2",
               date_concluded="2026-01-10",
               date_published="2026-01-15"),
        ]
        flags = _eval_overnight_turnaround(contracts, max_hours=24)
        assert len(flags) == 0

    def test_missing_dates_skipped(self):
        """Contracts without both dates are silently skipped."""
        contracts = [_c(contract_id="ot3", date_concluded=None, date_published=None)]
        flags = _eval_overnight_turnaround(contracts, max_hours=24)
        assert len(flags) == 0


# ── New Vendor Large Contract ────────────────────────────────────────


class TestNewVendorLargeContract:
    """First-time vendor with a large contract."""

    def test_flags_new_vendor(self):
        """First-time vendor + value > threshold flagged."""
        contracts = [
            _c(contract_id="nv1", supplier="NewCo",
               price_numeric_eur=150_000, published_date="2026-01-01"),
        ]
        flags = _eval_new_vendor_large_contract(contracts, min_value_eur=100_000)
        assert len(flags) == 1
        assert flags[0].vendor == "NewCo"

    def test_no_flag_small_first_contract(self):
        """Vendor with a small first contract should not be flagged."""
        contracts = [
            _c(contract_id="nv2", supplier="NewCo",
               price_numeric_eur=10_000, published_date="2026-01-01"),
        ]
        flags = _eval_new_vendor_large_contract(contracts, min_value_eur=100_000)
        assert len(flags) == 0

    def test_only_first_contract_checked(self):
        """Only the earliest (by date) contract is checked."""
        contracts = [
            _c(contract_id="nv3", supplier="VendorA",
               price_numeric_eur=10_000, published_date="2025-06-01"),
            _c(contract_id="nv4", supplier="VendorA",
               price_numeric_eur=500_000, published_date="2026-01-01"),
        ]
        flags = _eval_new_vendor_large_contract(contracts, min_value_eur=100_000)
        assert len(flags) == 0  # first contract is small


# ── Round Number Clustering ──────────────────────────────────────────


class TestRoundNumberClustering:
    """Statistical anomaly of round-number values."""

    def test_flags_round_values(self):
        """Distribution with many round values is flagged."""
        contracts = [
            _c(contract_id=f"rn{i}", price_numeric_eur=float(i * 1000))
            for i in range(1, 6)  # all round
        ]
        flags = _eval_round_number_clustering(
            contracts, round_modulus=1000, min_round_pct=60, min_contracts=5,
        )
        assert len(flags) == 5

    def test_no_flag_mixed_values(self):
        """Mix of round and non-round below threshold."""
        contracts = [
            _c(contract_id="rn1", price_numeric_eur=1000),
            _c(contract_id="rn2", price_numeric_eur=1234),
            _c(contract_id="rn3", price_numeric_eur=5678),
            _c(contract_id="rn4", price_numeric_eur=9999),
            _c(contract_id="rn5", price_numeric_eur=2000),
        ]
        flags = _eval_round_number_clustering(
            contracts, round_modulus=1000, min_round_pct=60, min_contracts=5,
        )
        assert len(flags) == 0  # only 2/5 = 40% are round

    def test_too_few_contracts(self):
        """Below min_contracts, no flags."""
        contracts = [
            _c(contract_id="rn1", price_numeric_eur=1000),
            _c(contract_id="rn2", price_numeric_eur=2000),
        ]
        flags = _eval_round_number_clustering(
            contracts, round_modulus=1000, min_round_pct=60, min_contracts=5,
        )
        assert len(flags) == 0


# ── Severity Scoring ─────────────────────────────────────────────────


class TestSeverityScoring:
    """Severity accumulates from multiple rules."""

    def test_accumulates(self):
        """Multiple rules → higher severity (capped at 1.0)."""
        engine = RuleEngine()
        contracts = [
            _c(contract_id="sev1",
               buyer="Inst", supplier="BigCo",
               price_numeric_eur=95_000,  # near 100k threshold
               date_concluded="2026-01-15",
               date_published="2026-01-15"),  # same day
        ]
        result = engine.evaluate(contracts, rules=[
            {"id": "threshold_proximity", "params": {"threshold_eur": 100_000, "proximity_pct": 10}},
            {"id": "overnight_turnaround", "params": {"max_hours": 24}},
        ])
        sev = result.severity_for_contract("sev1")
        assert sev > 0.3  # at least one rule fired
        assert sev <= 1.0

    def test_severity_capped_at_one(self):
        """Severity never exceeds 1.0."""
        result = RuleResult()
        from src.rules.engine import RuleFlag
        for i in range(10):
            result.add(RuleFlag(
                rule_id=f"r{i}", rule_name=f"R{i}",
                severity=0.5, description="test",
                contract_id="c1",
            ))
        assert result.severity_for_contract("c1") == 1.0


# ── Condition Builder ────────────────────────────────────────────────


class TestConditionBuilder:
    """Test the no-code condition builder."""

    def test_and_chain(self):
        """Two conditions with AND: both must match."""
        group = ConditionGroup(logic="AND", conditions=[
            Condition(field="price_numeric_eur", operator="gt", value=50_000),
            Condition(field="award_type", operator="eq", value="direct_award"),
        ])
        contracts = [
            _c(price_numeric_eur=100_000, award_type="direct_award"),
            _c(price_numeric_eur=100_000, award_type="open_tender"),
            _c(price_numeric_eur=10_000, award_type="direct_award"),
        ]
        matched = group.filter_contracts(contracts)
        assert len(matched) == 1
        assert matched[0].price_numeric_eur == 100_000
        assert matched[0].award_type == "direct_award"

    def test_or_chain(self):
        """Two conditions with OR: either matches."""
        group = ConditionGroup(logic="OR", conditions=[
            Condition(field="category", operator="eq", value="IT"),
            Condition(field="category", operator="eq", value="construction"),
        ])
        contracts = [
            _c(category="IT"),
            _c(category="construction"),
            _c(category="services"),
        ]
        matched = group.filter_contracts(contracts)
        assert len(matched) == 2

    def test_serialization_round_trip(self):
        """to/from JSON round-trip preserves structure."""
        original = ConditionGroup(logic="AND", conditions=[
            Condition(field="price_numeric_eur", operator="gt", value=1000),
            Condition(field="buyer", operator="contains", value="Mesto"),
        ])
        json_str = original.to_json()
        restored = ConditionGroup.from_json(json_str)
        assert restored.logic == "AND"
        assert len(restored.conditions) == 2
        assert restored.conditions[0].field == "price_numeric_eur"
        assert restored.conditions[0].operator == "gt"
        assert restored.conditions[0].value == 1000
        assert restored.conditions[1].value == "Mesto"

    def test_from_dict(self):
        """ConditionGroup.from_dict works."""
        data = {
            "logic": "OR",
            "conditions": [
                {"field": "supplier", "operator": "eq", "value": "STRABAG"},
            ],
        }
        group = ConditionGroup.from_dict(data)
        assert group.logic == "OR"
        assert len(group.conditions) == 1

    def test_empty_group_matches_all(self):
        """Empty condition group matches everything."""
        group = ConditionGroup(logic="AND", conditions=[])
        contracts = [_c(), _c()]
        matched = group.filter_contracts(contracts)
        assert len(matched) == 2

    def test_contains_operator(self):
        """The 'contains' operator does substring match."""
        group = ConditionGroup(logic="AND", conditions=[
            Condition(field="contract_title", operator="contains", value="ciest"),
        ])
        contracts = [
            _c(contract_title="Oprava ciest"),
            _c(contract_title="IT systém"),
        ]
        matched = group.filter_contracts(contracts)
        assert len(matched) == 1


# ── RuleEngine Integration ──────────────────────────────────────────


class TestRuleEngine:
    """Integration tests for the RuleEngine class."""

    def test_evaluate_all_defaults(self):
        """Running with default rules doesn't crash on varied data."""
        engine = RuleEngine()
        contracts = [
            _c(contract_id=f"int{i}", price_numeric_eur=float(i * 10_000),
               buyer="Inst", supplier="VendorA",
               date_concluded="2026-01-14", date_published="2026-01-15")
            for i in range(1, 11)
        ]
        result = engine.evaluate(contracts)
        assert isinstance(result, RuleResult)
        assert result.to_dict()["total_flags"] >= 0

    def test_preset_rules_list(self):
        """preset_rules() returns the expected rule IDs."""
        presets = RuleEngine.preset_rules()
        ids = {r["id"] for r in presets}
        assert "threshold_proximity" in ids
        assert "vendor_concentration" in ids
        assert "fragmentation" in ids
        assert "overnight_turnaround" in ids
        assert "new_vendor_large_contract" in ids
        assert "round_number_clustering" in ids

    def test_unknown_rule_id_ignored(self):
        """Unknown rule IDs are silently skipped."""
        engine = RuleEngine()
        result = engine.evaluate([_c()], rules=[{"id": "nonexistent", "params": {}}])
        assert len(result.flags) == 0

    def test_result_to_dict(self):
        """RuleResult.to_dict() produces well-structured output."""
        engine = RuleEngine()
        result = engine.evaluate(
            [_c(contract_id="d1", price_numeric_eur=95_000)],
            rules=[{"id": "threshold_proximity", "params": {"threshold_eur": 100_000, "proximity_pct": 10}}],
        )
        d = result.to_dict()
        assert "total_flags" in d
        assert "flags" in d
        assert d["total_flags"] == len(d["flags"])


# ── API Tests ────────────────────────────────────────────────────────


class TestRulesAPI:
    """Tests for rule-related API endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from src.api import app, get_store
        from src.engine import DataStore

        records = [
            {
                "contract_id": "r1",
                "contract_title": "Road Repair",
                "buyer": "Inst A",
                "supplier": "BigCo",
                "price_numeric_eur": 95_000.0,
                "published_date": "2026-01-15",
                "date_concluded": "2026-01-15",
                "date_published": "2026-01-15",
                "category": "construction",
                "award_type": "direct_award",
            },
            {
                "contract_id": "r2",
                "contract_title": "IT System",
                "buyer": "Inst A",
                "supplier": "SmallCo",
                "price_numeric_eur": 5_000.0,
                "published_date": "2026-01-20",
                "date_concluded": "2026-01-10",
                "date_published": "2026-01-20",
                "category": "IT",
                "award_type": "open_tender",
            },
        ]
        ds = DataStore()
        ds.load_from_list(records)
        app.dependency_overrides[get_store] = lambda: ds
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()

    def test_get_presets(self, client):
        """GET /api/rules/presets returns preset list."""
        r = client.get("/api/rules/presets")
        assert r.status_code == 200
        data = r.json()
        assert "presets" in data
        assert len(data["presets"]) == 6
        ids = {p["id"] for p in data["presets"]}
        assert "threshold_proximity" in ids

    def test_evaluate_defaults(self, client):
        """POST /api/rules/evaluate with all defaults."""
        r = client.post("/api/rules/evaluate", json={})
        assert r.status_code == 200
        data = r.json()
        assert "total_flags" in data
        assert "flags" in data
        assert "contract_severities" in data

    def test_evaluate_specific_rule(self, client):
        """POST /api/rules/evaluate with one specific rule."""
        r = client.post("/api/rules/evaluate", json={
            "rules": [
                {"id": "threshold_proximity", "params": {"threshold_eur": 100_000, "proximity_pct": 10}},
            ],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["total_flags"] >= 1
        # r1 is at 95k → should be flagged
        assert any(f["contract_id"] == "r1" for f in data["flags"])

    def test_evaluate_with_filter(self, client):
        """POST /api/rules/evaluate respects query-string filters."""
        r = client.post(
            "/api/rules/evaluate?categories=IT",
            json={"rules": [{"id": "threshold_proximity", "params": {"threshold_eur": 100_000, "proximity_pct": 10}}]},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["total_flags"] == 0  # IT contract is only 5k

    def test_custom_conditions(self, client):
        """POST /api/rules/custom evaluates condition group."""
        r = client.post("/api/rules/custom", json={
            "logic": "AND",
            "conditions": [
                {"field": "price_numeric_eur", "operator": "gt", "value": 10_000},
                {"field": "award_type", "operator": "eq", "value": "direct_award"},
            ],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["total_matched"] == 1
        assert data["contracts"][0]["contract_id"] == "r1"

    def test_custom_conditions_or(self, client):
        """POST /api/rules/custom with OR logic."""
        r = client.post("/api/rules/custom", json={
            "logic": "OR",
            "conditions": [
                {"field": "category", "operator": "eq", "value": "construction"},
                {"field": "category", "operator": "eq", "value": "IT"},
            ],
        })
        assert r.status_code == 200
        data = r.json()
        assert data["total_matched"] == 2
