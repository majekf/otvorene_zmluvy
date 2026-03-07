from scrape_josephine import parse_tender_summary


def test_parse_tender_summary_extracts_sections_and_documents():
    html = """
    <html><head><title>Test Tender</title></head><body>
      <h2>Informácie</h2>
      <dl>
        <dt>ID zákazky</dt><dd>12345</dd>
        <dt>Názov predmetu</dt><dd>Test predmet</dd>
        <dt>Doplňujúci CPV</dt><dd>51410000-9 - Inštalácia lekárskych zariadení 45259000-7 - Opravy a údržba zariadenia</dd>
      </dl>
      <h2>Termíny</h2>
      <dl>
        <dt>Lehota na predkladanie ponúk</dt><dd>01.01.2026 10:00:00</dd>
      </dl>
      <h2>Verejný obstarávateľ</h2>
      <dl>
        <dt>Názov organizácie</dt><dd>Obec Test</dd>
      </dl>
      <h2>Dokumenty</h2>
      <table>
        <tbody>
          <tr>
            <td><span title="Informacia.pdf">Informácia o výsledku vyhodnotenia ponúk</span></td>
            <td>Informácia o výsledku vyhodnotenia ponúk</td>
            <td>240 KB</td>
            <td>17.02.2026 13:44:02</td>
            <td><a href="/sk/tender/12345/summary/download/1"><span class="fa fa-download"></span></a></td>
          </tr>
        </tbody>
      </table>
    </body></html>
    """

    parsed = parse_tender_summary(html, "https://josephine.proebiz.com/sk/tender/12345/summary")

    assert parsed["tender_id"] == "12345"
    assert parsed["subject_name"] == "Test predmet"
    assert parsed["additional_cpv"] == [
      {"code": "51410000-9", "name": "Inštalácia lekárskych zariadení"},
      {"code": "45259000-7", "name": "Opravy a údržba zariadenia"},
    ]
    assert parsed["offer_submission_deadline"] == "01.01.2026 10:00:00"
    assert parsed["buyer_organization_name"] == "Obec Test"

    documents = parsed["documents"]
    assert len(documents) == 1
    assert documents[0]["document_name"] == "Informácia o výsledku vyhodnotenia ponúk"
    assert documents[0]["document_type"] == "Informácia o výsledku vyhodnotenia ponúk"
    assert documents[0]["file_size"] == "240 KB"
    assert documents[0]["uploaded_at"] == "17.02.2026 13:44:02"
    assert documents[0]["link"] == "https://josephine.proebiz.com/sk/tender/12345/summary/download/1"
