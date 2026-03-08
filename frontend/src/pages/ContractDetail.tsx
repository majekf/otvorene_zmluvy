/**
 * ContractDetail Page
 *
 * Shows full contract info, subcontractors, documents, PDF links,
 * tender data (if linked via public_procurement_id), and chatbot.
 * Route: /contract/:id
 */

import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import type { Contract, Tender, TenderDocument, TenderPart, TenderParticipant } from '../types';
import { fetchContract, fetchTender } from '../api';
import { formatEur, formatDate } from '../utils';
import ChatBar from '../components/ChatBar';

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <dt className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</dt>
      <dd className="text-slate-700">{children}</dd>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return <h2 className="section-title mb-4 mt-2">{children}</h2>;
}

function PdfIcon() {
  return (
    <svg className="w-4 h-4 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}

function ExternalLinkIcon() {
  return (
    <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
    </svg>
  );
}

function DocumentRow({ doc }: { doc: TenderDocument }) {
  return (
    <div className="flex items-start gap-3 py-2.5 border-b border-slate-100 last:border-0">
      <PdfIcon />
      <div className="flex-1 min-w-0">
        <a
          href={doc.link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary-600 hover:text-primary-800 font-medium text-sm truncate block"
        >
          {doc.document_name}
        </a>
        {doc.document_name !== doc.document_title && (
          <p className="text-xs text-slate-500 truncate">{doc.document_title}</p>
        )}
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-0.5">
          {doc.document_type && (
            <span className="text-xs text-slate-400">{doc.document_type}</span>
          )}
          {doc.file_size && doc.file_size !== '?' && (
            <span className="text-xs text-slate-400">{doc.file_size}</span>
          )}
          {doc.uploaded_at && (
            <span className="text-xs text-slate-400">{doc.uploaded_at}</span>
          )}
        </div>
      </div>
      {doc.is_external_link && (
        <span className="text-slate-400 mt-0.5"><ExternalLinkIcon /></span>
      )}
    </div>
  );
}

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [contract, setContract] = useState<Contract | null>(null);
  const [tender, setTender] = useState<Tender | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    setTender(null);
    fetchContract(id)
      .then((c) => {
        if (!cancelled) {
          setContract(c);
          // Use tender embedded in contract response (preferred)
          if (c._tender) {
            setTender(c._tender);
          } else {
            // Fallback: fetch separately (only works if backend has /api/tenders endpoint)
            const procId = c.public_procurement_id != null ? String(c.public_procurement_id) : null;
            if (procId) {
              fetchTender(procId).then((t) => {
                if (!cancelled) setTender(t);
              }).catch((err) => {
                console.warn('[ContractDetail] tender not found for id', procId, err?.message ?? err);
              });
            }
          }
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message ?? 'Failed to load contract');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading)
    return (
      <div data-testid="contract-detail-loading" className="p-8 text-slate-500 flex items-center gap-2">
        <svg className="animate-spin w-5 h-5 text-primary-500" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
        Loading…
      </div>
    );
  if (error)
    return (
      <div data-testid="contract-detail-error" className="p-8 text-red-600 glass-card bg-red-50/50 text-center">
        Error: {error}
      </div>
    );
  if (!contract)
    return (
      <div data-testid="contract-detail-notfound" className="p-8 text-slate-500 text-center">
        Contract not found
      </div>
    );

  const subcontractors = contract.scanned_subcontractors?.length
    ? contract.scanned_subcontractors
    : contract.subcontractor
      ? [{ name: contract.subcontractor, ico: contract.ico_subcontractor ?? null }]
      : [];

  const allPdfUrls: string[] = contract.pdf_urls?.length
    ? contract.pdf_urls
    : contract.pdf_url
      ? [contract.pdf_url]
      : [];

  const effectiveTitle = contract.scanned_suggested_title || contract.contract_title || 'Untitled';

  return (
    <div data-testid="contract-detail" className="max-w-4xl mx-auto animate-fade-in">
      <button onClick={() => navigate(-1)} className="btn-ghost inline-flex items-center gap-1.5 mb-6 text-primary-600">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" /></svg>
        Back
      </button>

      {/* ── Main contract card ── */}
      <div className="glass-card p-8 mb-6">
        <h1 className="page-title mb-1">{effectiveTitle}</h1>
        {contract.scanned_suggested_title && contract.contract_title && contract.scanned_suggested_title !== contract.contract_title && (
          <p className="text-sm text-slate-500 mb-3">Original: {contract.contract_title}</p>
        )}

        <div className="flex flex-wrap gap-2 mb-8">
          {contract.category && contract.category !== 'not_decided' && (
            <span className="chip chip-blue" data-testid="badge-category">{contract.category}</span>
          )}
          {contract.award_type && contract.award_type !== 'unknown' && (
            <span
              className={`chip ${contract.award_type === 'direct_award' ? 'chip-red' : contract.award_type === 'open_tender' ? 'chip-green' : 'chip-gray'}`}
              data-testid="badge-award"
            >
              {contract.award_type}
            </span>
          )}
          {contract.contract_type && (
            <span className="chip chip-gray">{contract.contract_type}</span>
          )}
          {contract.scanned_service_type && (
            <span className="chip chip-blue">{contract.scanned_service_type}</span>
          )}
          {contract.scanned_service_subtype && (
            <span className="chip chip-gray">{contract.scanned_service_subtype}</span>
          )}
        </div>

        {/* ── Parties ── */}
        <SectionTitle>Parties</SectionTitle>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
          <Field label="Buyer (Institution)">
            <Link to={`/institution/${encodeURIComponent(contract.buyer || '')}`} className="text-primary-600 hover:text-primary-800 font-medium transition-colors">
              {contract.buyer || '—'}
            </Link>
            {contract.buyer_detail && contract.buyer_detail !== contract.buyer && (
              <p className="text-xs text-slate-500 mt-0.5">{contract.buyer_detail}</p>
            )}
            {contract.ico_buyer && (
              <p className="text-xs text-slate-500 mt-0.5">IČO: {contract.ico_buyer}</p>
            )}
            {contract.ico_buyer && (
              <div className="flex flex-wrap gap-2 mt-1.5">
                <a
                  href={`https://finstat.sk/${contract.ico_buyer}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-primary-700 bg-slate-100 hover:bg-primary-50 px-2 py-1 rounded-md transition-colors"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" /></svg>
                  Finstat
                </a>
                <a
                  href={`https://www.foaf.sk/${contract.ico_buyer}/vizualizacia`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-primary-700 bg-slate-100 hover:bg-primary-50 px-2 py-1 rounded-md transition-colors"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z" /></svg>
                  FOAF
                </a>
              </div>
            )}
          </Field>
          <Field label="Supplier (Vendor)">
            <Link to={`/vendor/${encodeURIComponent(contract.supplier || '')}`} className="text-primary-600 hover:text-primary-800 font-medium transition-colors">
              {contract.supplier || '—'}
            </Link>
            {contract.supplier_detail && contract.supplier_detail !== contract.supplier && (
              <p className="text-xs text-slate-500 mt-0.5">{contract.supplier_detail}</p>
            )}
            {contract.ico_supplier && (
              <p className="text-xs text-slate-500 mt-0.5">IČO: {contract.ico_supplier}</p>
            )}
            {contract.ico_supplier && (
              <div className="flex flex-wrap gap-2 mt-1.5">
                <a
                  href={`https://finstat.sk/${contract.ico_supplier}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-primary-700 bg-slate-100 hover:bg-primary-50 px-2 py-1 rounded-md transition-colors"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" /></svg>
                  Finstat
                </a>
                <a
                  href={`https://www.foaf.sk/${contract.ico_supplier}/vizualizacia`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-slate-600 hover:text-primary-700 bg-slate-100 hover:bg-primary-50 px-2 py-1 rounded-md transition-colors"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z" /></svg>
                  FOAF
                </a>
              </div>
            )}
          </Field>
          {contract.rezort && (
            <Field label="Rezort">{contract.rezort}</Field>
          )}
        </dl>

        {/* ── Financial ── */}
        <SectionTitle>Financial</SectionTitle>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
          <Field label="Value">
            <span className="font-mono text-2xl font-bold text-slate-800">{formatEur(contract.price_numeric_eur)}</span>
          </Field>
          <Field label="Price (original)">{contract.price_raw ?? '—'}</Field>
          {contract.scanned_contract_value != null && contract.scanned_contract_value !== contract.price_numeric_eur && (
            <Field label="Scanned Value">{formatEur(contract.scanned_contract_value)}</Field>
          )}
          {contract.scanned_payment_reason && (
            <Field label="Payment Reason">{contract.scanned_payment_reason}</Field>
          )}
        </dl>

        {/* ── Dates ── */}
        <SectionTitle>Dates</SectionTitle>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
          <Field label="Published">{formatDate(contract.published_date) || formatDate(contract.date_published) || '—'}</Field>
          <Field label="Concluded">{formatDate(contract.date_concluded) || '—'}</Field>
          <Field label="Effective From">{formatDate(contract.date_effective) || '—'}</Field>
          <Field label="Valid Until">{formatDate(contract.date_valid_until) || '—'}</Field>
        </dl>

        {/* ── Identifiers ── */}
        <SectionTitle>Contract Details</SectionTitle>
        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
          <Field label="Contract ID">
            <span className="font-mono text-sm">{contract.contract_id}</span>
          </Field>
          <Field label="Contract Number">
            {contract.contract_number_detail || contract.contract_number || '—'}
          </Field>
          {contract.scanned_related_contract_number && (
            <Field label="Related Contract No.">{contract.scanned_related_contract_number}</Field>
          )}
          {contract.scanned_contract_type && (
            <Field label="Contract Type (scanned)">{contract.scanned_contract_type}</Field>
          )}
          {contract.scraped_at && (
            <Field label="Scraped At">{contract.scraped_at}</Field>
          )}
          {contract.contract_url && (
            <Field label="Source URL">
              <a href={contract.contract_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:text-primary-800 inline-flex items-center gap-1 text-sm font-medium">
                CRZ registry <ExternalLinkIcon />
              </a>
            </Field>
          )}
          {contract.public_procurement_id && (
            <Field label="Public Procurement">
              {contract.public_procurement_url ? (
                <a href={contract.public_procurement_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:text-primary-800 inline-flex items-center gap-1 text-sm font-medium">
                  {contract.public_procurement_portal || 'Procurement portal'} #{contract.public_procurement_id} <ExternalLinkIcon />
                </a>
              ) : (
                <span>{contract.public_procurement_portal || 'Portal'} #{contract.public_procurement_id}</span>
              )}
            </Field>
          )}
        </dl>

        {/* ── AI Summary ── */}
        {contract.scanned_summary && (
          <div className="mb-6">
            <SectionTitle>AI Summary</SectionTitle>
            <p className="bg-slate-50 p-5 rounded-xl text-sm text-slate-700 whitespace-pre-wrap leading-relaxed border border-slate-100">
              {contract.scanned_summary}
            </p>
          </div>
        )}
        {contract.pdf_text_summary && contract.pdf_text_summary !== 'not_summarized' && (
          <div className="mb-6" data-testid="pdf-summary">
            <SectionTitle>PDF Summary</SectionTitle>
            <p className="bg-slate-50 p-5 rounded-xl text-sm text-slate-700 whitespace-pre-wrap leading-relaxed border border-slate-100">
              {contract.pdf_text_summary}
            </p>
          </div>
        )}

        {/* ── Documents / PDFs ── */}
        {allPdfUrls.length > 0 && (
          <div className="mb-6">
            <SectionTitle>Documents ({allPdfUrls.length})</SectionTitle>
            <div className="space-y-2">
              {allPdfUrls.map((url, i) => (
                <a
                  key={url}
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary inline-flex items-center gap-2 mr-2 mb-2"
                  data-testid={i === 0 ? 'pdf-link' : undefined}
                >
                  <PdfIcon />
                  {allPdfUrls.length === 1 ? 'View PDF' : `PDF ${i + 1}`}
                </a>
              ))}
            </div>
          </div>
        )}

        {/* ── Subcontractors ── */}
        {subcontractors.length > 0 && (
          <div className="mb-6" data-testid="subcontractors">
            <SectionTitle>Subcontractors ({subcontractors.length})</SectionTitle>
            <div className="overflow-x-auto rounded-xl border border-slate-200">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-slate-500 text-xs uppercase">
                  <tr>
                    <th className="text-left px-4 py-2 font-semibold">Name</th>
                    <th className="text-left px-4 py-2 font-semibold">IČO</th>
                  </tr>
                </thead>
                <tbody>
                  {subcontractors.map((s, i) => (
                    <tr key={i} className="border-t border-slate-100 hover:bg-slate-50">
                      <td className="px-4 py-3 text-slate-700">{s.name}</td>
                      <td className="px-4 py-3 font-mono text-slate-500">{s.ico || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* ── Tender card ── */}
      {tender && (
        <div className="glass-card p-8 mb-6" data-testid="tender-section">
          <div className="flex items-center gap-3 mb-6">
            <span className="chip chip-green text-xs">Public Procurement</span>
            <h2 className="text-xl font-bold text-slate-800">
              {tender.subject_name || tender.page_title || `Tender #${tender.tender_id}`}
            </h2>
          </div>

          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-6">
            {tender.tender_url && (
              <Field label="Tender URL">
                <a href={tender.tender_url} target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:text-primary-800 inline-flex items-center gap-1 text-sm font-medium">
                  Open on portal <ExternalLinkIcon />
                </a>
              </Field>
            )}
            {tender.file_reference && <Field label="File Reference">{tender.file_reference}</Field>}
            {tender.procedure_type && <Field label="Procedure Type">{tender.procedure_type}</Field>}
            {tender.procurement_type && <Field label="Procurement Type">{tender.procurement_type}</Field>}
            {tender.procurement_result && <Field label="Result">{tender.procurement_result}</Field>}
            {tender.estimated_value && <Field label="Estimated Value">{tender.estimated_value}</Field>}
            {tender.main_cpv && <Field label="CPV Code">{tender.main_cpv}</Field>}
            {tender.evaluation_criterion && <Field label="Evaluation Criterion">{tender.evaluation_criterion}</Field>}
            {tender.evaluation_price_basis && <Field label="Price Basis">{tender.evaluation_price_basis}</Field>}
            {tender.offer_submission_deadline && <Field label="Submission Deadline">{tender.offer_submission_deadline}</Field>}
            {tender.nuts && <Field label="NUTS Region">{tender.nuts}</Field>}
            {tender.is_divided_into_parts && <Field label="Divided into Parts">{tender.is_divided_into_parts}</Field>}
            {tender.electronic_auction && <Field label="Electronic Auction">{tender.electronic_auction}</Field>}
            {tender.central_procurement && <Field label="Central Procurement">{tender.central_procurement}</Field>}
          </dl>

          {tender.short_description && (
            <div className="mb-6">
              <dt className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Description</dt>
              <p className="bg-slate-50 p-4 rounded-xl text-sm text-slate-700 whitespace-pre-wrap leading-relaxed border border-slate-100">
                {tender.short_description}
              </p>
            </div>
          )}

          {tender.parts?.length > 0 && (
            <div className="mt-6">
              <SectionTitle>Bidding Results by Part ({tender.parts.length})</SectionTitle>
              <div className="space-y-4">
                {tender.parts.map((part: TenderPart, i: number) => {
                  const participants = part.participants ?? [];
                  return (
                    <div key={i} className="rounded-xl border border-slate-200 overflow-hidden">
                      <div className="bg-slate-50 px-4 py-2.5 flex items-center justify-between border-b border-slate-200">
                        <span className="text-sm font-semibold text-slate-700">
                          Part {part.part_number ?? i + 1}
                        </span>
                        {part.document && (
                          <a
                            href={part.document.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-primary-600 hover:text-primary-800 inline-flex items-center gap-1 font-medium"
                          >
                            {part.document.document_name} <ExternalLinkIcon />
                          </a>
                        )}
                      </div>
                      {participants.length > 0 ? (
                        <table className="w-full text-sm">
                          <thead className="bg-slate-50/50 text-slate-500 text-xs uppercase border-b border-slate-100">
                            <tr>
                              <th className="text-left px-4 py-2 font-semibold">#</th>
                              <th className="text-left px-4 py-2 font-semibold">Bidder</th>
                              <th className="text-left px-4 py-2 font-semibold">IČO</th>
                              <th className="text-right px-4 py-2 font-semibold">Bid (EUR)</th>
                            </tr>
                          </thead>
                          <tbody>
                            {participants.map((p: TenderParticipant, pi: number) => (
                              <tr key={pi} className={`border-t border-slate-100 ${
                                pi === 0 ? 'bg-green-50/50' : 'hover:bg-slate-50'
                              }`}>
                                <td className="px-4 py-3 text-slate-400 text-xs">
                                  {pi === 0 ? (
                                    <span className="inline-flex items-center gap-1 text-green-700 font-semibold">
                                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth="2.5" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M16.5 18.75h-9m9 0a3 3 0 0 1 3 3h-15a3 3 0 0 1 3-3m9 0v-3.375c0-.621-.503-1.125-1.125-1.125h-.871M7.5 18.75v-3.375c0-.621.504-1.125 1.125-1.125h.872m5.007 0H9.497m5.007 0a7.454 7.454 0 0 1-.982-3.172M9.497 14.25a7.454 7.454 0 0 0 .981-3.172M5.25 4.236c-.982.143-1.954.317-2.916.52A6.003 6.003 0 0 0 7.73 9.728M5.25 4.236V4.5c0 2.108.966 3.99 2.48 5.228M5.25 4.236V2.721C7.456 2.41 9.71 2.25 12 2.25c2.291 0 4.545.16 6.75.47v1.516M7.73 9.728a6.726 6.726 0 0 0 2.748 1.35m8.272-6.842V4.5c0 2.108-.966 3.99-2.48 5.228m2.48-5.492a46.32 46.32 0 0 1 2.916.52 6.003 6.003 0 0 1-5.395 4.972m0 0a6.726 6.726 0 0 1-2.749 1.35m0 0a6.772 6.772 0 0 1-3.044 0" /></svg>
                                      Winner
                                    </span>
                                  ) : pi + 1}
                                </td>
                                <td className="px-4 py-3 text-slate-800 font-medium">{p.name}</td>
                                <td className="px-4 py-3 text-slate-500 text-xs">
                                  <span className="font-mono">{p.ico || '—'}</span>
                                  {p.ico && (
                                    <div className="flex gap-2 mt-1">
                                      <a href={`https://finstat.sk/${p.ico}`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-xs text-slate-500 hover:text-primary-700 font-medium underline-offset-2 hover:underline">
                                        <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" /></svg>
                                        Finstat
                                      </a>
                                      <a href={`https://www.foaf.sk/${p.ico}/vizualizacia`} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-0.5 text-xs text-slate-500 hover:text-primary-700 font-medium underline-offset-2 hover:underline">
                                        <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0 0 20.25 18V6A2.25 2.25 0 0 0 18 3.75H6A2.25 2.25 0 0 0 3.75 6v12A2.25 2.25 0 0 0 6 20.25Z" /></svg>
                                        FOAF
                                      </a>
                                    </div>
                                  )}
                                </td>
                                <td className="px-4 py-3 text-right font-mono">
                                  {p.proposed_sum_eur != null
                                    ? <span className={pi === 0 ? 'font-bold text-green-700' : 'text-slate-700'}>{formatEur(p.proposed_sum_eur)}</span>
                                    : <span className="text-slate-400">—</span>
                                  }
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      ) : (
                        <p className="px-4 py-3 text-sm text-slate-400">No participant data available</p>
                      )}
                      {part.notes && (
                        <p className="px-4 py-3 text-xs text-slate-500 border-t border-slate-100 bg-slate-50/50">{part.notes}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {tender.documents?.length > 0 && (
            <div className="mt-6">
              <SectionTitle>Tender Documents ({tender.documents.length})</SectionTitle>
              <div className="rounded-xl border border-slate-200 divide-y divide-slate-100 px-4">
                {tender.documents.map((doc, i) => (
                  <DocumentRow key={i} doc={doc} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Contract-scoped chatbot */}
      <ChatBar filters={{}} contractId={contract.contract_id ?? undefined} />
    </div>
  );
}
