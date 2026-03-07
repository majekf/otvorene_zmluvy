"""
Integration tests for CRZ scraper.
Tests scraper on actual website or with mocked responses.
"""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scraper import extract_contract_details, extract_listing_rows, scrape_contracts


# Sample HTML from the contract listing page
SAMPLE_LISTING_HTML = """
<table class="table_list">
    <thead class="table-light">
        <tr>
            <th class="cell1">Zverejnene</th>
            <th class="cell2">Nazov zmluvy / C. zmluvy</th>
            <th class="cell3">Cena</th>
            <th class="cell4">Dodavatel</th>
            <th class="cell5">Objednavatel</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td class="cell1">
                <div class="text-center">
                    <span class="d-block fs-6 lh-sm mt-1">1.</span>
                    <span class="d-block">Marec</span>
                    <span class="d-block">2026</span>
                </div>
            </td>
            <td class="cell2">
                <a href="/zmluva/12048046/">ramcova dohoda</a><br />
                <span>2026/22/E/CI</span><br />
            </td>
            <td class="cell3 text-nowrap text-end">28 978,27&nbsp;\u20ac</td>
            <td class="cell4">Liptovske pekarne a cukrarne VCELA - Lippek k.s.</td>
            <td class="cell5">Liptovska nemocnica s poliklinikou MUDr. Ivana Stodolu Liptovsky Mikulas</td>
        </tr>
        <tr>
            <td class="cell1">
                <div class="text-center">
                    <span class="d-block fs-6 lh-sm mt-1">1.</span>
                    <span class="d-block">Marec</span>
                    <span class="d-block">2026</span>
                </div>
            </td>
            <td class="cell2">
                <a href="/zmluva/12048044/">Zmluva o spolupraci</a><br />
                <span>08/BAB/2026</span><br />
            </td>
            <td class="cell3 text-nowrap text-end">0,00&nbsp;\u20ac</td>
            <td class="cell4">Polnohospodarske Druzstvo Hrusov</td>
            <td class="cell5">Obec Bab</td>
        </tr>
    </tbody>
</table>
"""

# Sample HTML from contract detail page
SAMPLE_DETAIL_HTML = """
<header class="page__heading">
    <h1 class="page__title">ramcova dohoda</h1>
</header>

<div class="row gutters-small">
    <div class="col-md-7 col-lg-8 order-md-2 mb-3">
        <div class="card h-100">
            <h2 class="card-header">Identifikacia a zmluvy</h2>
            <div class="card-body bg-gray-200">
                <ul class="list-unstyled mb-0">
                    <li class="py-2">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">Typ:</strong>
                            <span class="col-sm-9">Zmluva</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">Rezort:</strong>
                            <span class="col-sm-9">Ministerstvo zdravotnictva Slovenskej republiky</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">C. zmluvy:</strong>
                            <span class="col-sm-9">2026/22/E/CI</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">ID zmluvy:</strong>
                            <span class="col-sm-9">12048046</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">Objednavatel:</strong>
                            <span class="col-sm-9">Liptovska nemocnica s poliklinikou MUDr. Ivana Stodolu Liptovsky Mikulas</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">ICO:</strong>
                            <span class="col-sm-9">17336163</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">Dodavatel:</strong>
                            <span class="col-sm-9">Liptovske pekarne a cukrarne VCELA - Lippek k.s.</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">ICO:</strong>
                            <span class="col-sm-9">36394556</span>
                        </div>
                    </li>
                </ul>
            </div>
        </div>
    </div>

    <div class="col-md-5 col-lg-4 order-md-1">
        <div class="card mb-3">
            <h2 class="card-header">Datum</h2>
            <div class="card-body">
                <ul class="list-unstyled mb-0">
                    <li class="py-2">
                        <div class="row gx-3">
                            <strong class="col">Datum zverejnenia:</strong>
                            <span class="col-auto">01.03.2026</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col">Datum uzavretia:</strong>
                            <span class="col-auto">28.02.2026</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col">Datum ucinnosti:</strong>
                            <span class="col-auto">02.03.2026</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col">Datum platnosti do:</strong>
                            <span class="col-auto">neuvedeny</span>
                        </div>
                    </li>
                </ul>
            </div>
        </div>

        <div class="card mb-3">
            <h2 class="card-header">Priloha</h2>
            <div class="card-body">
                <ul class="list-unstyled mb-0">
                    <li class="row gx-2 py-2">
                        <div class="col-auto text-nowrap" style="width: 3.5em;" aria-hidden="true">
                            <i class="fa fa-file-pdf-o me-1" aria-hidden="true"></i><span class="fs-9 text-uppercase">text</span>
                        </div>
                        <div class="col">
                            <a href="/data/att/6568046.pdf" target="_blank" aria-label="PDF subor">ramcova dohoda</a>
                            <small class="text-muted fs-7">(.pdf, 402.87 kB)</small>
                        </div>
                    </li>
                </ul>
            </div>
        </div>
    </div>
</div>
"""


class TestExtractListingRows:
    """Test listing row extraction."""

    def test_extract_two_contracts(self):
        """Test extracting two contracts from listing HTML."""
        rows = extract_listing_rows(SAMPLE_LISTING_HTML)

        assert len(rows) == 2

        # First contract
        assert rows[0]["published_day"] == "1."
        assert rows[0]["published_month"] == "Marec"
        assert rows[0]["published_year"] == "2026"
        assert rows[0]["published_date"] == "2026-03-01"
        assert rows[0]["contract_title"] == "ramcova dohoda"
        assert rows[0]["contract_number"] == "2026/22/E/CI"
        assert rows[0]["price_numeric_eur"] == 28978.27
        assert rows[0]["supplier"] == "Liptovske pekarne a cukrarne VCELA - Lippek k.s."
        assert rows[0]["buyer"] == "Liptovska nemocnica s poliklinikou MUDr. Ivana Stodolu Liptovsky Mikulas"
        assert rows[0]["contract_url"] == "https://www.crz.gov.sk/zmluva/12048046/"
        assert rows[0]["contract_id"] == "12048046"

        # Second contract
        assert rows[1]["price_numeric_eur"] == 0.0
        assert rows[1]["contract_id"] == "12048044"


class TestExtractContractDetails:
    """Test contract detail extraction."""

    def test_extract_dates_ids_and_identification_fields(self):
        """Test extraction of dates, IDs, rezort, and full identification section."""
        details = extract_contract_details(
            SAMPLE_DETAIL_HTML,
            "https://example.com/zmluva/12048046/",
        )

        assert details.get("contract_number_detail") == "2026/22/E/CI"
        assert details.get("contract_id_detail") == "12048046"
        assert details.get("contract_type") == "Zmluva"
        assert details.get("rezort") == "Ministerstvo zdravotnictva Slovenskej republiky"
        assert details.get("date_published") == "2026-03-01"
        assert details.get("date_concluded") == "2026-02-28"
        assert details.get("date_effective") == "2026-03-02"
        assert details.get("date_valid_until") is None
        assert details.get("ico_buyer") == "17336163"
        assert details.get("ico_supplier") == "36394556"

        assert "identification_fields" in details
        assert "identification_section_items" in details
        assert details["identification_fields"]["Rezort"] == "Ministerstvo zdravotnictva Slovenskej republiky"

    def test_extract_pdf_urls(self):
        """Test extracting PDF URLs from detail page."""
        details = extract_contract_details(SAMPLE_DETAIL_HTML, "https://example.com/zmluva/12048046/")

        pdf_urls = details.get("pdf_urls", [])
        assert len(pdf_urls) == 1
        assert pdf_urls[0] == "https://www.crz.gov.sk/data/att/6568046.pdf"


class TestScrapeContractsSmoke:
    """Smoke test for the full scraping function."""

    @patch("scraper.download_and_extract_pdf")
    @patch("scraper.fetch_page")
    def test_smoke_test_single_page(self, mock_fetch, mock_pdf_download):
        """Smoke test: scrape one page and verify output structure."""
        mock_fetch.side_effect = [
            SAMPLE_LISTING_HTML,
            SAMPLE_DETAIL_HTML,
            SAMPLE_DETAIL_HTML,
        ]
        mock_pdf_download.return_value = {
            "pdf_url": "https://www.crz.gov.sk/data/att/6568046.pdf",
            "pdf_local_path": None,
            "pdf_text": None,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        try:
            count = scrape_contracts(
                start_page=1,
                max_pages=1,
                output_file=output_file,
                delay=0,
            )

            assert count == 2

            with open(output_file, "r", encoding="utf-8") as f:
                contracts = json.load(f)

            assert len(contracts) == 2

            contract1 = contracts[0]
            assert contract1["contract_url"] == "https://www.crz.gov.sk/zmluva/12048046/"
            assert "scraped_at" in contract1
            assert contract1["contract_id"] == "12048046"
            assert contract1["price_numeric_eur"] == 28978.27

            contract2 = contracts[1]
            assert contract2["contract_id"] == "12048044"
            assert contract2["price_numeric_eur"] == 0.0

        finally:
            Path(output_file).unlink(missing_ok=True)

    @patch("scraper.download_and_extract_pdf")
    @patch("scraper.fetch_page")
    def test_price_filter_applied_before_detail_fetch(self, mock_fetch, mock_pdf_download):
        """Only matching listing rows should proceed to detail-page scraping."""
        mock_fetch.side_effect = [
            SAMPLE_LISTING_HTML,
            SAMPLE_DETAIL_HTML,
        ]
        mock_pdf_download.return_value = {
            "pdf_url": "https://www.crz.gov.sk/data/att/6568046.pdf",
            "pdf_local_path": None,
            "pdf_text": None,
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_file = f.name

        try:
            count = scrape_contracts(
                start_page=1,
                max_pages=1,
                output_file=output_file,
                delay=0,
                min_price=1000.0,
            )

            assert count == 1
            assert mock_fetch.call_count == 2

            with open(output_file, "r", encoding="utf-8") as f:
                contracts = json.load(f)

            assert len(contracts) == 1
            contract = contracts[0]
            assert contract["contract_id"] == "12048046"
            assert contract["price_numeric_eur"] == 28978.27
        finally:
            Path(output_file).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
