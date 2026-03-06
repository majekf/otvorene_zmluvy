# Task description:
Create whole git repository for project explained below:

Write a robust Python scraper for the Centrálny register zmlúv site (root: `https://www.crz.gov.sk/`) that:

1. Paginates through the contracts register listing (table with class `table_list`).
2. For every row (`<tr>`) extracts: published day/month/year, contract title (text + hyperlink), contract number, price, supplier (Dodávateľ), buyer (Objednávateľ).
3. Visits each contract's detail page (the hyperlink in the title) and extracts structured fields present there (e.g., Č. zmluvy, ID zmluvy, Objednávateľ, Dodávateľ, IČO values, all dates under the "Dátum" card).
4. From the contract page, find and record any attachment/pdf links (e.g., `/data/att/6568046.pdf`), download the PDF, and extract text with `pdfplumber`.
5. Save everything to a newline-delimited JSON (NDJSON) or CSV with these fields:

   * published_day, published_month, published_year
   * contract_title, contract_number
   * price_raw, price_numeric_eur
   * supplier, buyer
   * contract_url (absolute)
   * contract_id (if found on detail page)
   * dates: published_date, concluded_date, effective_date, valid_until (where present)
   * ico_supplier, ico_buyer
   * pdf_url (absolute) (if present)
   * pdf_local_path (if downloaded)
   * pdf_text (string or truncated at X chars)
   * scraped_at (ISO datetime)
6. Use polite scraping: set a realistic `User-Agent`, retries, timeouts, optional delay between requests, and obey basic robots (stop if blocked).
7. Be resilient to small HTML differences (use class-based and fallback selectors).
8. Provide a CLI entry point `python scrape_crz.py --start-page 1 --max-pages 100 --out out.ndjson` and a configuration section (headers, delay, max_workers).

---

# Acceptance criteria (how to verify)

1. Running `python scrape_crz.py --start-page 1 --max-pages 3` produces a file `out.ndjson` with one JSON object per contract from pages 1..3.
2. Each JSON object contains `contract_url` and `scraped_at`.
3. If a PDF is present on a contract page, the file is downloaded to `data/pdfs/` and `pdf_text` contains non-empty text (or `pdf_text` length > 100 for non-empty PDFs).
4. Price normalization converted `'28 978,27 €'` → `28978.27` in `price_numeric_eur`.
5. Script retries on transient HTTP errors and logs progress (INFO level): pages fetched, contracts processed, pdfs downloaded.
6. No background/async promises — everything runs synchronously when invoked.

---

# Implementation notes, pitfalls & tips

* The listing sample uses `?page=0` for the first page in the HTML snippet; the site may be zero- or one-based. My script assumes `?page=0` corresponds to page 1. If actual site differs, adjust `start_page` offset accordingly (I included a small adjustment in CLI).
* Price parsing handles non-breaking spaces and Slovak decimal commas.
* PDF extraction uses `pdfplumber`. Some PDFs are scanned images — `pdfplumber` will not OCR them. If you need OCR, add `pytesseract` + `wand` or use an OCR service.
* Respect robots.txt and legal restrictions. If the site returns `429` or blocks, reduce scrape speed or get explicit permission.
* The script is intentionally conservative (synchronous, small delay). You can parallelize contract detail + pdf downloads later with a worker pool but keep retry/robustness logic.

---

# Tests / Quick checks for Copilot to add

1. Unit test `parse_price()` with a few formats: `"28 978,27 €"`, `"0,00 €"`, `"330 624,00 €"`.
2. Integration smoke test that scrapes only `--max-pages 1` and asserts the output file has > 0 lines and at least one `contract_url`.
3. Test pdf extraction using a known PDF url from the site to ensure `pdfplumber` yields text.

---

# Snippet from the contracts register website

<snippet_register>
value="2862619">Úrad komisára pre deti</option><option value="3956955">Úrad komisára pre osoby so zdravotným postihnutím</option><option value="561884">Úrad na ochranu osobných údajov Slovenskej republiky</option><option value="5742083">Úrad na ochranu oznamovateľov protispoločenskej činnosti</option><option value="10269138">Úrad podpredsedu vlády SR vlády pre Plán obnovy a znalostnú ekonomiku</option><option value="6706801">Úrad podpredsedu vlády, ktorý neriadi ministerstvo</option><option value="115005">Úrad pre dohľad nad výkonom auditu</option><option value="360085">Úrad pre dohľad nad zdravotnou starostlivosťou</option><option value="114735">Úrad pre normalizáciu, metrológiu a skúšobníctvo SR</option><option value="356704">Úrad pre reguláciu sieťových odvetví</option><option value="114729">Úrad pre verejné obstarávanie</option><option value="114489">Úrad priemyselného vlastníctva SR</option><option value="114688">Úrad vlády SR</option><option value="3805640">Ústav pamäti národa</option><option value="3953379">Ústredie ekumenickej pastoračnej služby v OS SR a OZ SR</option><option value="114503">Všeobecná zdravotná poisťovňa a.s.</option><option value="131437">Vysoká škola múzických umení</option><option value="117084">Vysoká škola výtvarných umení v Bratislave</option><option value="115836">Žilinská univerzita v Žiline</option></select>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-sm-4 control-label">
                <label for="frm_filter_3_art_zs1">Objednávateľ:</label>
            </div>
            <div class="col-sm-8">
                <input class="form-control fld width1" type="text" name="art_zs1" value="" maxlength="255" id="frm_filter_3_art_zs1" />
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-sm-4 control-label">
                <label for="frm_filter_3_nazov">Číslo zmluvy:</label>
            </div>
            <div class="col-sm-8">
                <input class="form-control fld width4" type="text" name="nazov" value="" maxlength="255" id="frm_filter_3_nazov" />
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-sm-4 control-label">
                <label for="frm_filter_3_art_ico1">IČO objednávateľa:</label>
            </div>
            <div class="col-sm-8">
                <input class="form-control fld width4" type="text" name="art_ico1" value="" maxlength="255" id="frm_filter_3_art_ico1" />
            </div>
        </div>
        <div class="form-group text-end">
            <button type="submit" name="odoslat" class="btn btn-primary">Vyhľadať</button>
        </div>
    </div>
</div><input id="frm_filter_3_ID" type="hidden" name="ID" value="2171273" /><div class="row form-group frmbutbg"><div class="col-sm-12"><button id="frm_filter_3_odoslat" class="btn btn-custom button0" type="submit" name="odoslat" value="Vyhľadať"  >Vyhľadať</button></div></div><input id="frm_filter_3_frm_id_frm_filter_3" type="hidden" name="frm_id_frm_filter_3" value="69a43b5bdd00c" /></form>
            </div>
        </div>


        <main id="page" class="py-4 py-lg-5 px-3 px-lg-4">
            <div>
<!--<div class="alert alert-danger mb-3" role="alert">Z dôvodu plánovanej údržby bude Centrálny register zmlúv od 17.5.2025, 9:00h do 18.5.2025, 23:00h nedostupný. <strong><a href="/technicka-odstavka/">VIAC INFORMÁCIÍ</a></strong></div>-->

<header class="page__heading">
    <h1 class="page__title">Zmluvy</h1>
</header>

<div class="page__body">
    Zverejnené zmluvy za posledných 24 hodín.<br />
<p>Všetky sumy v tabuľkách sú uvádzané v eurách.</p>
<div class="table-responsive">
    <table class="table table-bordered table-sm fs-7 table_list">
        <thead class="table-light">
            <tr>
                <th class="cell1">
                    <div class="d-flex align-items-center sort">
                        <span class="me-2">Zverejnené</span>
                        <!--<div class="table__sort d-flex flex-column ms-auto">-->
                        <!--    <a href="?order=31" class="sort-up table__sort--up" title="Zoradiť zoznam vzostupne"><i class="fa fa-angle-up" aria-hidden="true"></i></a>-->
                        <!--    <a href="?order=32" class="sort-down table__sort--down" title="Zoradiť zoznam zostupne"><i class="fa fa-angle-down" aria-hidden="true"></i></a>-->
                        <!--</div>-->
                    </div>
                </th>
                <th class="cell2">
                    <div class="d-flex align-items-center sort">
                        <span class="me-2">Názov zmluvy / Č. zmluvy</span>
                        <!--<div class="table__sort d-flex flex-column ms-auto">-->
                        <!--    <a href="?order=13" class="sort-up table__sort--up" title="Zoradiť zoznam vzostupne"><i class="fa fa-angle-up" aria-hidden="true"></i></a>-->
                        <!--    <a href="?order=14" class="sort-down table__sort--down" title="Zoradiť zoznam zostupne"><i class="fa fa-angle-down" aria-hidden="true"></i></a>-->
                        <!--</div>-->
                    </div>
                </th>
                <th class="cell3">
                    <div class="d-flex align-items-center sort">
                        <span class="me-2">Cena</span>
                        <div class="table__sort d-flex flex-column ms-auto">
                            <a href="?order=21" class="sort-up table__sort--up" title="Zoradiť zoznam vzostupne"><i class="fa fa-angle-up" aria-hidden="true"></i></a>
                            <a href="?order=22" class="sort-down table__sort--down" title="Zoradiť zoznam zostupne"><i class="fa fa-angle-down" aria-hidden="true"></i></a>
                        </div>
                    </div>
                </th>
                <th class="cell4">
                    <div class="d-flex align-items-center sort">
                        <span class="me-2">Dodávateľ</span>
                        <!--<div class="table__sort d-flex flex-column ms-auto">-->
                        <!--    <a href="?order=11" class="sort-up table__sort--up" title="Zoradiť zoznam vzostupne"><i class="fa fa-angle-up" aria-hidden="true"></i></a>-->
                        <!--    <a href="?order=12" class="sort-down table__sort--down" title="Zoradiť zoznam zostupne"><i class="fa fa-angle-down" aria-hidden="true"></i></a>-->
                        <!--</div>-->
                    </div>
                </th>
                <th class="cell5">
                    <div class="d-flex align-items-center sort">
                        <span class="me-2">Objednávateľ</span>
                        <!--<div class="table__sort d-flex flex-column ms-auto">-->
                        <!--    <a href="?order=9" class="sort-up table__sort--up" title="Zoradiť zoznam vzostupne"><i class="fa fa-angle-up" aria-hidden="true"></i></a>-->
                        <!--    <a href="?order=10" class="sort-down table__sort--down" title="Zoradiť zoznam zostupne"><i class="fa fa-angle-down" aria-hidden="true"></i></a>-->
                        <!--</div>-->
                    </div>
                </th>
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
    <td class="cell2"><a href="/zmluva/12048046/">rámcová dohoda</a><br /><span>2026/22/E/CI</span><br /></td>
    <td class="cell3 text-nowrap text-end">28 978,27&nbsp;&euro;</td>
    <td class="cell4">Liptovské pekárne a cukrárne VČELA – Lippek k.s.</td>
    <td class="cell5">Liptovská nemocnica s poliklinikou MUDr. Ivana Stodolu Liptovský Mikuláš</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">1.</span>
            <span class="d-block">Marec</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048044/">Zmluva o spolupráci - Kúpna zmluva</a><br /><span>08/BAB/2026</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Poľnohospodárske Družstvo Hrušov</td>
    <td class="cell5">Obec Báb</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">1.</span>
            <span class="d-block">Marec</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048042/">Rámcová kúpna zmluva - platí pre časť zákazky č. 2</a><br /><span>80162026</span><br /></td>
    <td class="cell3 text-nowrap text-end">330 624,00&nbsp;&euro;</td>
    <td class="cell4">Metrostav DS a.s.</td>
    <td class="cell5">Regionálna správa a údržba ciest Nitra a.s.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">1.</span>
            <span class="d-block">Marec</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048040/">Rámcová kúpna zmluva - platí pre časť zákazky č. 1</a><br /><span>80152026</span><br /></td>
    <td class="cell3 text-nowrap text-end">725 699,98&nbsp;&euro;</td>
    <td class="cell4">Metrostav DS a.s.</td>
    <td class="cell5">Regionálna správa a údržba ciest Nitra a.s.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">1.</span>
            <span class="d-block">Marec</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048038/">Kanalizácia Pinkovce</a><br /><span>ZMLUVA O DIELO č. 08/2025</span><br /></td>
    <td class="cell3 text-nowrap text-end">982 170,10&nbsp;&euro;</td>
    <td class="cell4">TAMALEX s.r.o.</td>
    <td class="cell5">Obec Pinkovce</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">1.</span>
            <span class="d-block">Marec</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048036/">Zmluva o prenájme nebytových priestorov v Domu smútku</a><br /><span>Nájomná zmluva 1/2026</span><br /></td>
    <td class="cell3 text-nowrap text-end">600,00&nbsp;&euro;</td>
    <td class="cell4">Obec Pinkovce</td>
    <td class="cell5">spol. JOZANA, s.r.o.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">1.</span>
            <span class="d-block">Marec</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048034/">Dodatok č. 1 k zmluve o dielo</a><br /><span>17/2025</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Izotech Group, spol. s r.o.</td>
    <td class="cell5">Obec Dolné Srnie</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">1.</span>
            <span class="d-block">Marec</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048032/">Hospodárska zmluva o poskytovaní stravovacích služieb</a><br /><span>3/2026</span><br /></td>
    <td class="cell3 text-nowrap text-end">6,00&nbsp;&euro;</td>
    <td class="cell4">BS Real Team s.r.o.</td>
    <td class="cell5">Obec Rakša, Obecný úrad Rakša 41, 039 01 Turčianske Teplice</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048030/">Dodatok k zmluve o zabezpečení systému združeného nakladania s odpadmi</a><br /><span>50/2026</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">NATUR-PACK, a.s.</td>
    <td class="cell5">Obec Rakúsy</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048028/">Dohoda o zriadení, tvorbe a použití fondu údržby a opráv bytového domu</a><br /><span>1645/71/20260701</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Igor Závodský</td>
    <td class="cell5">BYSPRAV spol. s r.o.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048026/">Dohoda o zriadení, tvorbe a použití fondu údržby a opráv bytového domu</a><br /><span>1645/71/20260401</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Mária Ficeková</td>
    <td class="cell5">BYSPRAV spol. s r.o.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048024/">Dohoda o zriadení, tvorbe a použití fondu údržby a opráv bytového domu</a><br /><span>1645/71/22</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Pavol Kohút</td>
    <td class="cell5">BYSPRAV spol. s r.o.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048022/">Dohoda o zriadení, tvorbe a použití fondu údržby a opráv bytového domu</a><br /><span>1645/71/14</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Júlia Lakatosová</td>
    <td class="cell5">BYSPRAV spol. s r.o.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048020/">Dohoda o zriadení, tvorbe a použití fondu údržby a opráv bytového domu</a><br /><span>1645/71/28</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Renáta Kiáczová</td>
    <td class="cell5">BYSPRAV spol. s r.o.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048018/">Dohoda o zriadení, tvorbe a použití fondu údržby a opráv bytového domu</a><br /><span>1645/71/07</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Renáta Kiáczová</td>
    <td class="cell5">BYSPRAV spol. s r.o.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048016/">Dohoda o zriadení, tvorbe a použití fondu údržby a opráv bytového domu</a><br /><span>DORO_022/2025</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Andrea Valášeková</td>
    <td class="cell5">BYSPRAV spol. s r.o.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048014/">Dohoda o zriadení, tvorbe a použití fondu údržby a opráv bytového domu</a><br /><span>DORO_012/2025</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Marek Szilágyi</td>
    <td class="cell5">BYSPRAV spol. s r.o.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048012/">Dohoda o zriadení, tvorbe a použití fondu údržby a opráv bytového domu</a><br /><span>DORO_021/2025</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Tomáš Herák</td>
    <td class="cell5">BYSPRAV spol. s r.o.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048010/">Dohoda o zriadení, tvorbe a použití fondu údržby a opráv bytového domu</a><br /><span>DORO_019/2025</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Karol Papp</td>
    <td class="cell5">BYSPRAV spol. s r.o.</td>
</tr><tr>
    <td class="cell1">
        <div class="text-center">
            <span class="d-block fs-6 lh-sm mt-1">28.</span>
            <span class="d-block">Február</span>
            <span class="d-block">2026</span>
        </div>
    </td>
    <td class="cell2"><a href="/zmluva/12048008/">Dohoda o zriadení, tvorbe a použití fondu údržby a opráv bytového domu</a><br /><span>DORO_023/2025</span><br /></td>
    <td class="cell3 text-nowrap text-end">0,00&nbsp;&euro;</td>
    <td class="cell4">Timár Zoltán</td>
    <td class="cell5">BYSPRAV spol. s r.o.</td>
</tr>        </tbody>
    </table>
</div>
<nav role="navigation" aria-label="Strankovanie"><ul class="pagination justify-content-center"><li class="page-item active" aria-current="true"><span class="page-link">1<span class="sr-only"> Aktuálna stránka 1</span></span></li> <li class="page-item"><a class="page-link" href="/zmluvy/?page=1" aria-label="Stránka 2">2</a></li> <li class="page-item"><a class="page-link" href="/zmluvy/?page=2" aria-label="Stránka 3">3</a></li> <li class="page-item"><a class="page-link" href="/zmluvy/?page=3" aria-label="Stránka 4">4</a></li> <li class="page-item"><a class="page-link" href="/zmluvy/?page=4" aria-label="Stránka 5">5</a></li> <li class="page-item"><a class="page-link" href="/zmluvy/?page=5" aria-label="Stránka 6">6</a></li><li class="page-item"><a class="page-link page-link---next" href="/zmluvy/?page=1" aria-label="Nasledujuca-strana"><span aria-hidden="true">&raquo;</span></a></li></ul></nav>
    
</div>
</div>
</snippet_register>

---

# Snippet from the website of a specific contract detail page

<snippet_contract_detail>
osobných údajov Slovenskej republiky</option><option value="5742083">Úrad na ochranu oznamovateľov protispoločenskej činnosti</option><option value="10269138">Úrad podpredsedu vlády SR vlády pre Plán obnovy a znalostnú ekonomiku</option><option value="6706801">Úrad podpredsedu vlády, ktorý neriadi ministerstvo</option><option value="115005">Úrad pre dohľad nad výkonom auditu</option><option value="360085">Úrad pre dohľad nad zdravotnou starostlivosťou</option><option value="114735">Úrad pre normalizáciu, metrológiu a skúšobníctvo SR</option><option value="356704">Úrad pre reguláciu sieťových odvetví</option><option value="114729">Úrad pre verejné obstarávanie</option><option value="114489">Úrad priemyselného vlastníctva SR</option><option value="114688">Úrad vlády SR</option><option value="3805640">Ústav pamäti národa</option><option value="3953379">Ústredie ekumenickej pastoračnej služby v OS SR a OZ SR</option><option value="114503">Všeobecná zdravotná poisťovňa a.s.</option><option value="131437">Vysoká škola múzických umení</option><option value="117084">Vysoká škola výtvarných umení v Bratislave</option><option value="115836">Žilinská univerzita v Žiline</option></select>
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-sm-4 control-label">
                <label for="frm_filter_3_art_zs1">Objednávateľ:</label>
            </div>
            <div class="col-sm-8">
                <input class="form-control fld width1" type="text" name="art_zs1" value="" maxlength="255" id="frm_filter_3_art_zs1" />
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-sm-4 control-label">
                <label for="frm_filter_3_nazov">Číslo zmluvy:</label>
            </div>
            <div class="col-sm-8">
                <input class="form-control fld width4" type="text" name="nazov" value="" maxlength="255" id="frm_filter_3_nazov" />
            </div>
        </div>
        <div class="row mb-3">
            <div class="col-sm-4 control-label">
                <label for="frm_filter_3_art_ico1">IČO objednávateľa:</label>
            </div>
            <div class="col-sm-8">
                <input class="form-control fld width4" type="text" name="art_ico1" value="" maxlength="255" id="frm_filter_3_art_ico1" />
            </div>
        </div>
        <div class="form-group text-end">
            <button type="submit" name="odoslat" class="btn btn-primary">Vyhľadať</button>
        </div>
    </div>
</div><input id="frm_filter_3_ID" type="hidden" name="ID" value="2171273" /><div class="row form-group frmbutbg"><div class="col-sm-12"><button id="frm_filter_3_odoslat" class="btn btn-custom button0" type="submit" name="odoslat" value="Vyhľadať"  >Vyhľadať</button></div></div><input id="frm_filter_3_frm_id_frm_filter_3" type="hidden" name="frm_id_frm_filter_3" value="69a43d46d84c1" /></form>
            </div>
        </div>


        <main id="page" class="py-4 py-lg-5 px-3 px-lg-4">
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
</li><!-- typ -->
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">Rezort:</strong>
                            <span class="col-sm-9">Subjekty verejnej správy</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">Objednávateľ:</strong>
                            <span class="col-sm-9">Liptovská nemocnica s poliklinikou MUDr. Ivana Stodolu Liptovský Mikuláš<br />Palúčanská 214/25, 03123 Liptovský Mikuláš</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
    <div class="row gx-3">
        <strong class="col-sm-3 text-sm-end">IČO:</strong>
        <span class="col-sm-9">17336163</span>
    </div>
</li><!-- ico1 -->
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">Dodávateľ:</strong>
                            <span class="col-sm-9">Liptovské pekárne a cukrárne VČELA – Lippek k.s.<br />ul. 1 mája 1919, 031 01 Lipovský Mikuláš</span>
                        </div>
                    </li>
                    <li class="py-2 border-top">
    <div class="row gx-3">
        <strong class="col-sm-3 text-sm-end">IČO:</strong>
        <span class="col-sm-9">36394556</span>
    </div>
</li><!-- ico -->
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">Názov zmluvy:</strong>
                            <span class="col-sm-9">rámcová dohoda</span>
                        </div>
                    </li>
                    <!-- popis -->
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">ID zmluvy:</strong>
                            <span class="col-sm-9">12048046</span>
                        </div>
                    </li>
                    <!-- uvo -->
                    <!-- poznamka -->
                    <!-- stav 4 -->
                    <!-- stav 3 -->
                    <li class="py-2 border-top">
                        <div class="row gx-3">
                            <strong class="col-sm-3 text-sm-end">Zverejnil:</strong>
                            <span class="col-sm-9"><a href="/6277186-sk/liptovska-nemocnica-s-poliklinikou-mudr-ivana-stodolu-liptovsky-mikulas/">Liptovská nemocnica s poliklinikou MUDr. Ivana Stodolu Liptovský Mikuláš</a></span>
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
        <a href="/data/att/6568046.pdf" target="_blank" aria-label="PDF súbor - Textová verzia: rámcová dohoda" aria-describedby="fileSize_text_12048047">rámcová dohoda</a>
        <small class="text-muted fs-7" id="fileSize_text_12048047">(.pdf, 402.87 kB)</small>
    </div>
</li></ul>

    </div>
</div><!-- prilohy -->
    </div>
</div>

<div class="card mb-5">
    <h2 class="card-header">Cenové plnenie</h2>
    <div class="card-body p-0">
        <div class="row g-0 align-items-center">
            <div class="col-md-9 p-3">
                <span class="me-3">Zmluvne dohodnutá čiastka:</span> <span class="text-danger text-nowrap">28 978,27 €</span>
            </div>
            <div class="col-md-3 p-3 bg-gray-200">
                <strong class="me-3">Celková čiastka:</strong> <strong class="text-danger fs-5 text-nowrap">28 978,27 €</strong>
            </div>
        </div>
    </div>
</div>

<!-- dodatky -->

<!--zmeny-->

<a href="javascript:history.go(-1)" class="btn btn-outline-primary btn-sm"><i class="fa fa-angle-left me-2" aria-hidden="true"></i>Návrat späť</a>

<div class="bg-gray-200 py-2 px-3 mt-5 text-center fs-7">
    <strong>Vystavil:</strong> Liptovská nemocnica s poliklinikou MUDr. Ivana Stodolu Liptovský Mikuláš
</div>


        </main>

        <footer id="footer" class="px-3 px-lg-4 fs-7">
            <div class="row border-top g-0 py-3">
                <div class="col-md-6 footer__col--1">
                    &copy; <a href="https://vlada.gov.sk">Úrad vlády SR</a> - Všetky práva vyhradené
                    <ul class="list-inline mb-0">
                        <li class="list-inline-item"><a class="mr-4" href="#">Prehlásenie o prístupnosti</a></li>
                        <li class="list-inline-item"><a href="https://www.zmluvy.gov.sk" target="_blank">Zmluvy do 31.12.2010</a></li>
</snippet_contract_detail>

---

# pdf file location:

In the previous snippet example, the pdf file location is stored at:
        <a href="/data/att/6568046.pdf" target="_blank" aria-label="PDF súbor - Textová verzia: rámcová dohoda" aria-describedby="fileSize_text_12048047">rámcová dohoda</a>
        <small class="text-muted fs-7" id="fileSize_text_12048047">(.pdf, 402.87 kB)</small>