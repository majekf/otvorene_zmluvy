/**
 * ContractDetail Page
 *
 * Shows full contract info, PDF link, summary text, category badge.
 * Route: /contract/:id
 */

import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import type { Contract } from '../types';
import { fetchContract } from '../api';
import { formatEur, formatDate } from '../utils';

export default function ContractDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [contract, setContract] = useState<Contract | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchContract(id)
      .then((c) => {
        if (!cancelled) setContract(c);
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

  return (
    <div data-testid="contract-detail" className="max-w-4xl mx-auto animate-fade-in">
      <button onClick={() => navigate(-1)} className="btn-ghost inline-flex items-center gap-1.5 mb-6 text-primary-600">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" /></svg>
        Back
      </button>

      <div className="glass-card p-8">
        <h1 className="page-title mb-3">{contract.contract_title || 'Untitled'}</h1>

        <div className="flex flex-wrap gap-2 mb-8">
          <span className="chip chip-blue" data-testid="badge-category">
            {contract.category}
          </span>
          <span
            className={`chip ${
              contract.award_type === 'direct_award'
                ? 'chip-red'
                : contract.award_type === 'open_tender'
                  ? 'chip-green'
                  : 'chip-gray'
            }`}
            data-testid="badge-award"
          >
            {contract.award_type}
          </span>
        </div>

        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-6 mb-8">
          <div className="space-y-1">
            <dt className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Institution</dt>
            <dd>
              <Link to={`/institution/${encodeURIComponent(contract.buyer || '')}`} className="text-primary-600 hover:text-primary-800 font-medium transition-colors">
                {contract.buyer || '—'}
              </Link>
            </dd>
          </div>
          <div className="space-y-1">
            <dt className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Vendor</dt>
            <dd>
              <Link to={`/vendor/${encodeURIComponent(contract.supplier || '')}`} className="text-primary-600 hover:text-primary-800 font-medium transition-colors">
                {contract.supplier || '—'}
              </Link>
            </dd>
          </div>
          <div className="space-y-1">
            <dt className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Value</dt>
            <dd className="font-mono text-2xl font-bold text-slate-800">{formatEur(contract.price_numeric_eur)}</dd>
          </div>
          <div className="space-y-1">
            <dt className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Published</dt>
            <dd className="text-slate-700">{formatDate(contract.published_date)}</dd>
          </div>
          <div className="space-y-1">
            <dt className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Effective From</dt>
            <dd className="text-slate-700">{formatDate(contract.date_effective)}</dd>
          </div>
          <div className="space-y-1">
            <dt className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Valid Until</dt>
            <dd className="text-slate-700">{formatDate(contract.date_valid_until)}</dd>
          </div>
          <div className="space-y-1">
            <dt className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Contract ID</dt>
            <dd className="font-mono text-sm text-slate-600">{contract.contract_id}</dd>
          </div>
          <div className="space-y-1">
            <dt className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Price (original)</dt>
            <dd className="text-slate-700">{contract.price_raw ?? '—'}</dd>
          </div>
        </dl>

        {contract.pdf_url && (
          <div className="mb-6">
            <a
              href={contract.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary inline-flex items-center gap-2"
              data-testid="pdf-link"
            >
              <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>
              View PDF
            </a>
          </div>
        )}

        {contract.pdf_text_summary && (
          <div className="mb-6" data-testid="pdf-summary">
            <h2 className="section-title mb-3">PDF Summary</h2>
            <p className="bg-slate-50 p-5 rounded-xl text-sm text-slate-700 whitespace-pre-wrap leading-relaxed border border-slate-100">{contract.pdf_text_summary}</p>
          </div>
        )}
      </div>
    </div>
  );
}
