"""
Unit tests for Phase 7 — URL-state serialization.

Tests cover: full state encode/decode and partial defaults.
"""

import pytest

from src.api import encode_filter_state
from src.models import FilterState


class TestUrlStateFull:
    """Tests for finalized URL-state encoding (Phase 7)."""

    def test_full_state_encode_decode(self):
        """All fields survive round-trip through encode_filter_state."""
        fs = FilterState(
            institutions=["Mesto Bratislava", "Mesto Košice"],
            date_from="2025-01-01",
            date_to="2025-12-31",
            categories=["construction", "IT"],
            vendors=["STRABAG s.r.o."],
            value_min=10_000.0,
            value_max=500_000.0,
            award_types=["direct_award"],
            text_search="cesty",
        )
        sort_spec = [("price_numeric_eur", "desc"), ("published_date", "asc")]

        encoded = encode_filter_state(
            fs,
            sort_spec=sort_spec,
            group_by="supplier",
            mode="dashboard",
            page=3,
        )

        assert encoded["institutions"] == "Mesto Bratislava,Mesto Košice"
        assert encoded["date_from"] == "2025-01-01"
        assert encoded["date_to"] == "2025-12-31"
        assert encoded["categories"] == "construction,IT"
        assert encoded["vendors"] == "STRABAG s.r.o."
        assert encoded["value_min"] == "10000.0"
        assert encoded["value_max"] == "500000.0"
        assert encoded["award_types"] == "direct_award"
        assert encoded["text_search"] == "cesty"
        assert encoded["sort"] == "price_numeric_eur:desc,published_date:asc"
        assert encoded["group_by"] == "supplier"
        assert encoded["mode"] == "dashboard"
        assert encoded["page"] == "3"

    def test_partial_state_defaults(self):
        """Empty FilterState with no extra params returns empty dict."""
        fs = FilterState()
        encoded = encode_filter_state(fs)
        assert encoded == {}

    def test_page_one_omitted(self):
        """page=1 is not included in the encoded dict."""
        fs = FilterState()
        encoded = encode_filter_state(fs, page=1)
        assert "page" not in encoded

    def test_mode_included_when_set(self):
        """mode is included in the encoded dict."""
        fs = FilterState()
        encoded = encode_filter_state(fs, mode="benchmark")
        assert encoded["mode"] == "benchmark"

    def test_group_by_included(self):
        """group_by is included in the encoded dict."""
        fs = FilterState()
        encoded = encode_filter_state(fs, group_by="supplier")
        assert encoded["group_by"] == "supplier"
