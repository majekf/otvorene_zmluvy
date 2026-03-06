"""
Integration tests for CRZ scraper.
Tests scraper on actual website or with mocked responses.
"""

import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scraper import (
    extract_listing_rows,
    extract_contract_details,
    scrape_contracts,
)


# Sample HTML from the contract listing page
SAMPLE_LISTING_HTML = """
<table class="table_list">
    <thead class="table-light">
        <tr>
            <th class="cell1">Zverejnené</th>
            <th class="cell2">Názov zmluvy / Č. zmluvy</th>
            <th class="cell3">Cena</th>
            <th class="cell4">Dodávateľ</th>
            <th class="cell5">Objednávateľ</th>
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
                <a href="/zmluva/12048046/">rámcová dohoda</a><br />
                <span>2026/22/E/CI</span><br />
            </td>
            <td class="cell3 text-nowrap text-end">28 978,27&nbsp;€</td>
            <td class="cell4">Liptovské pekárne a cukrárne VČELA – Lippek k.s.</td>
            <td class="cell5">Liptovská nemocnica s poliklinikou MUDr. Ivana Stodolu Liptovský Mikuláš</td>
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
                <a href="/zmluva/12048044/">Zmluva o spolupráci</a><br />
                <span>08/BAB/2026</span><br />
            </td>
            <td class="cell3 text-nowrap text-end">0,00&nbsp;€</td>
            <td class="cell4">Poľnohospodárske Družstvo Hrušov</td>
            <td class="cell5">Obec Báb</td>
        </tr>
    </tbody>
</table>
"""

# Sample HTML from contract detail page
SAMPLE_DETAIL_HTML = """
<header class="page__heading">
    <h1 class="page__title">rámcová dohoda</h1>
</header>

<div class="row gutters-small">
    <div class="col-md-7 col-lg-8 order-md-2 mb-3">
        <div class="card h-100">
            <h2 class="card-header">Identifikácia zmluvy</h2>
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
                            <strong class="col-sm-3 text-sm-end">Č. zmluvy:</strong>
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
                            <strong class="col-sm-3 text-sm-end">Objednávateľ:</strong>
                            <span class="col-sm-9">Liptovská nemocnica s poliklinikou MUDr. Ivana Stodolu Liptovský Mikuláš</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">IČO:</strong>
                            <span class="col-sm-9">17336163</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">Dodávateľ:</strong>
                            <span class="col-sm-9">Liptovské pekárne a cukrárne VČELA – Lippek k.s.</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">IČO:</strong>
                            <span class="col-sm-9">36394556</span>
                        </div>
                    </li>
                </ul>
            </div>
        </div>
    </div>

    <div class="col-md-5 col-lg-4 order-md-1">
        <div class="card mb-3">
            <h2 class="card-header">Dátum</h2>
            <div class="card-body">
                <ul class="list-unstyled mb-0">
                    <li class="py-2">
                        <div class="row gx-3">
                            <strong class="col">Dátum zverejnenia:</strong>
                            <span class="col-auto">01.03.2026</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col">Dátum uzavretia:</strong>
                            <span class="col-auto">28.02.2026</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col">Dátum účinnosti:</strong>
                            <span class="col-auto">02.03.2026</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col">Dátum platnosti do:</strong>
                            <span class="col-auto">neuvedený</span>
                        </div>
                    </li>
                </ul>
            </div>
        </div>
        
        <div class="card mb-3">
            <h2 class="card-header">Príloha</h2>
            <div class="card-body">
                <ul class="list-unstyled mb-0">
                    <li class="row gx-2 py-2">
                        <div class="col-auto text-nowrap" style="width: 3.5em;" aria-hidden="true">
                            <i class="fa fa-file-pdf-o me-1" aria-hidden="true"></i><span class="fs-9 text-uppercase">text</span>
                        </div>
                        <div class="col">
                            <a href="/data/att/6568046.pdf" target="_blank" aria-label="PDF súbor">rámcová dohoda</a>
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
        assert rows[0]["contract_title"] == "rámcová dohoda"
        assert rows[0]["contract_number"] == "2026/22/E/CI"
        assert rows[0]["price_numeric_eur"] == 28978.27
        assert rows[0]["supplier"] == "Liptovské pekárne a cukrárne VČELA – Lippek k.s."
        assert rows[0]["buyer"] == "Liptovská nemocnica s poliklinikou MUDr. Ivana Stodolu Liptovský Mikuláš"
        assert rows[0]["contract_url"] == "https://www.crz.gov.sk/zmluva/12048046/"
        assert rows[0]["contract_id"] == "12048046"
        
        # Second contract
        assert rows[1]["price_numeric_eur"] == 0.0
        assert rows[1]["contract_id"] == "12048044"


class TestExtractContractDetails:
    """Test contract detail extraction."""
    
    def test_extract_dates_and_ids(self):
        """Test extracting dates and IDs from detail page."""
        details = extract_contract_details(SAMPLE_DETAIL_HTML, "https://example.com/zmluva/12048046/")
        
        assert details.get("contract_number_detail") == "2026/22/E/CI"
        assert details.get("contract_id_detail") == "12048046"
        assert details.get("date_published") == "2026-03-01"
        assert details.get("date_concluded") == "2026-02-28"
        assert details.get("date_effective") == "2026-03-02"
        assert details.get("date_valid_until") is None  # "neuvedený"
        assert details.get("ico_buyer") == "17336163"
        assert details.get("ico_supplier") == "36394556"
    
    def test_extract_pdf_urls(self):
        """Test extracting PDF URLs from detail page."""
        details = extract_contract_details(SAMPLE_DETAIL_HTML, "https://example.com/zmluva/12048046/")
        
        pdf_urls = details.get("pdf_urls", [])
        assert len(pdf_urls) == 1
        assert pdf_urls[0] == "https://www.crz.gov.sk/data/att/6568046.pdf"


class TestScrapeContractsSmoke:
    """Smoke test for the full scraping function."""
    
    @patch('scraper.fetch_page')
    def test_smoke_test_single_page(self, mock_fetch):
        """Smoke test: scrape one page and verify output structure."""
        # Mock HTTP responses
        mock_fetch.side_effect = [
            SAMPLE_LISTING_HTML,  # Listing page
            SAMPLE_DETAIL_HTML,   # Detail page 1
            SAMPLE_DETAIL_HTML,   # Detail page 2
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ndjson', delete=False) as f:
            output_file = f.name
        
        try:
            # Run scraper
            count = scrape_contracts(
                start_page=1,
                max_pages=1,
                output_file=output_file,
                delay=0,  # No delay for tests
            )
            
            # Verify output
            assert count == 2
            
            # Read and parse output file
            with open(output_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            assert len(lines) == 2
            
            # Parse first contract JSON
            contract1 = json.loads(lines[0])
            assert contract1["contract_url"] == "https://www.crz.gov.sk/zmluva/12048046/"
            assert "scraped_at" in contract1
            assert contract1["contract_id"] == "12048046"
            assert contract1["price_numeric_eur"] == 28978.27
            
            # Verify second contract
            contract2 = json.loads(lines[1])
            assert contract2["contract_id"] == "12048044"
            assert contract2["price_numeric_eur"] == 0.0
        
        finally:
            # Cleanup
            Path(output_file).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
