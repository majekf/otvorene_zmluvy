"""
Unit tests for CRZ scraper.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scraper import (
    RequestThrottler,
    parse_date_from_text,
    parse_price,
    parse_slovak_date,
)


class TestParsePrice:
    """Test price parsing function."""

    def test_parse_price_with_thousands_separator(self):
        """Test parsing price with thousands separator."""
        assert parse_price("28 978,27 \u20ac") == 28978.27

    def test_parse_price_zero(self):
        """Test parsing zero price."""
        assert parse_price("0,00 \u20ac") == 0.0

    def test_parse_price_large(self):
        """Test parsing large price."""
        assert parse_price("330 624,00 \u20ac") == 330624.0

    def test_parse_price_with_nbsp(self):
        """Test parsing price with non-breaking space."""
        assert parse_price("28\u00a0978,27 \u20ac") == 28978.27

    def test_parse_price_invalid(self):
        """Test parsing invalid price."""
        assert parse_price("invalid") is None

    def test_parse_price_empty(self):
        """Test parsing empty price."""
        assert parse_price("") is None
        assert parse_price(None) is None


class TestParseSlovakDate:
    """Test Slovak date parsing."""

    def test_parse_date_march_2026(self):
        """Test parsing March 1, 2026."""
        result = parse_slovak_date("1", "Marec", "2026")
        assert result == "2026-03-01"

    def test_parse_date_february_2026(self):
        """Test parsing February 28, 2026."""
        result = parse_slovak_date("28", "Februar", "2026")
        assert result == "2026-02-28"

    def test_parse_date_december_2025(self):
        """Test parsing December 31, 2025."""
        result = parse_slovak_date("31", "December", "2025")
        assert result == "2025-12-31"

    def test_parse_date_invalid_month(self):
        """Test parsing with invalid month."""
        result = parse_slovak_date("1", "InvalidMonth", "2026")
        assert result is None

    def test_parse_date_invalid_day(self):
        """Test parsing with invalid day."""
        result = parse_slovak_date("invalid", "Marec", "2026")
        assert result is None


class TestParseDateFromText:
    """Test date parsing from text format."""

    def test_parse_iso_date_format(self):
        """Test parsing date in DD.MM.YYYY format."""
        result = parse_date_from_text("01.03.2026")
        assert result == "2026-03-01"

    def test_parse_iso_date_february(self):
        """Test parsing February date."""
        result = parse_date_from_text("28.02.2026")
        assert result == "2026-02-28"

    def test_parse_date_with_spaces(self):
        """Test parsing date with spaces."""
        result = parse_date_from_text("  01.03.2026  ")
        assert result == "2026-03-01"

    def test_parse_date_not_specified(self):
        """Test parsing 'neuvedeny' (not specified)."""
        result = parse_date_from_text("neuvedeny")
        assert result is None

    def test_parse_date_empty(self):
        """Test parsing empty date."""
        result = parse_date_from_text("")
        assert result is None

    def test_parse_date_invalid_format(self):
        """Test parsing invalid format."""
        result = parse_date_from_text("01-03-2026")
        assert result is None


class TestRequestThrottler:
    """Test request throttling helper."""

    @patch("scraper.time.sleep")
    @patch("scraper.time.monotonic")
    def test_enforces_delay_between_requests(self, mock_monotonic, mock_sleep):
        throttler = RequestThrottler(3.0)

        # First wait: no sleep, second wait: sleep for 2 seconds (3 - 1 elapsed).
        mock_monotonic.side_effect = [0.0, 0.0, 1.0, 1.0]

        throttler.wait_for_slot()
        throttler.wait_for_slot()

        mock_sleep.assert_called_once_with(2.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
