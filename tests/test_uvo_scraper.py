import json

from scrape_uvo import (
    is_uvo_tender_url,
    load_uvo_urls_from_contracts,
    parse_uvo_documents,
    parse_uvo_tender_detail,
    to_documents_url,
)


def test_parse_uvo_tender_detail_extracts_core_fields():
    html = """
    <html><head><title>Vyhľadávanie zákaziek - ÚVO</title></head><body>
      <main>
        <table>
          <tr><th>Názov zákazky:</th><td>Zabezpečenie leteniek EVO</td></tr>
          <tr><th>Obstarávateľ:</th><td>Ministerstvo obrany Slovenskej republiky</td></tr>
          <tr><th>Druh postupu:</th><td>Verejná súťaž</td></tr>
          <tr><th>CPV zákazky:</th><td>60400000-2 - Letecké dopravné služby 63510000-7 - Služby cestovných kancelárií</td></tr>
          <tr><th>Elektronická aukcia:</th><td>Nie</td></tr>
        </table>
      </main>
    </body></html>
    """

    parsed = parse_uvo_tender_detail(
        html,
        "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/detail/549162",
    )

    assert parsed["tender_id"] == "549162"
    assert parsed["subject_name"] == "Zabezpečenie leteniek EVO"
    assert parsed["buyer_organization_name"] == "Ministerstvo obrany Slovenskej republiky"
    assert parsed["procedure_type"] == "Verejná súťaž"
    assert parsed["electronic_auction"] == "Nie"
    assert parsed["additional_cpv"] == [
        {"code": "60400000-2", "name": "Letecké dopravné služby"},
        {"code": "63510000-7", "name": "Služby cestovných kancelárií"},
    ]


def test_parse_uvo_documents_extracts_rows_and_detail_links():
    html = """
    <html><body>
      <main>
        <table>
          <thead>
            <tr>
              <th>Druh dokumentu</th>
              <th>Názov dokumentu</th>
              <th>Obstarávateľ</th>
              <th>Zverejnenie</th>
              <th>Úprava</th>
            </tr>
          </thead>
          <tbody>
            <tr onclick="window.location.href='/vyhladavanie/vyhladavanie-dokumentov/detail/3553708?cHash=abc';">
              <td>Informácia o výsledku vyhodnotenia ponúk</td>
              <td>Informácia o výsledku vyhodnotenia ponúk</td>
              <td>Ministerstvo obrany Slovenskej republiky</td>
              <td>04.02.2026</td>
              <td>04.02.2026</td>
            </tr>
          </tbody>
        </table>
      </main>
    </body></html>
    """

    docs = parse_uvo_documents(
        html,
        "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/dokumenty/549162",
    )

    assert len(docs) == 1
    assert docs[0]["document_type"] == "Informácia o výsledku vyhodnotenia ponúk"
    assert docs[0]["document_name"] == "Informácia o výsledku vyhodnotenia ponúk"
    assert docs[0]["uploaded_at"] == "04.02.2026"
    assert docs[0]["link"] == (
        "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-dokumentov/detail/3553708?cHash=abc"
    )


def test_is_uvo_tender_url_accepts_only_detail_links():
    assert is_uvo_tender_url(
        "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/detail/538922"
    )
    assert is_uvo_tender_url(
        "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/detail/538922?cHash=abc"
    )
    assert is_uvo_tender_url(
        "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/dokumenty/538922"
    )
    assert is_uvo_tender_url(
        "http://ww.uvo.gov.sk/vyhladavanie-zakaziek/detail/dokumenty/538922"
    )
    assert not is_uvo_tender_url("https://josephine.proebiz.com/sk/tender/65482/summary")


def test_load_uvo_urls_from_contracts_filters_entries(tmp_path):
    contracts_path = tmp_path / "contracts.json"
    contracts_path.write_text(
        json.dumps(
            [
                {
                    "public_procurement_url": "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/detail/538922"
                },
                {
                    "public_procurement_url": "http://ww.uvo.gov.sk/vyhladavanie-zakaziek/detail/dokumenty/538922"
                },
                {
                    "public_procurement_url": "https://josephine.proebiz.com/sk/tender/65482/summary"
                },
                {
                    "public_procurement_url": "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/detail/538922"
                },
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    urls = load_uvo_urls_from_contracts(str(contracts_path))
    assert urls == [
        "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/detail/538922",
        "http://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/detail/538922",
        "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/detail/538922",
    ]


def test_to_documents_url_rewrites_detail_path():
    assert to_documents_url(
        "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/detail/549162?cHash=abc"
    ) == "https://www.uvo.gov.sk/vyhladavanie/vyhladavanie-zakaziek/dokumenty/549162?cHash=abc"
