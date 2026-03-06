/**
 * InstitutionProfile Page
 *
 * Shows institution's full footprint: summary stats, spend trend chart,
 * top vendor breakdown, and related contracts table.
 * Route: /institution/:id
 */

import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, BarChart as RBarChart, Bar, CartesianGrid } from 'recharts';
import type { InstitutionProfile as InstitutionProfileType } from '../types';
import { fetchInstitutionProfile } from '../api';
import { formatEur, formatCompact, formatDate } from '../utils';

export default function InstitutionProfile() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<InstitutionProfileType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchInstitutionProfile(id)
      .then((p) => {
        if (!cancelled) setProfile(p);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message ?? 'Failed to load');
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
      <div data-testid="institution-loading" className="p-8 text-slate-500 flex items-center gap-2">
        <svg className="animate-spin w-5 h-5 text-primary-500" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" /></svg>
        Loading…
      </div>
    );
  if (error)
    return (
      <div data-testid="institution-error" className="p-8 text-red-600 glass-card bg-red-50/50 text-center">
        Error: {error}
      </div>
    );
  if (!profile)
    return (
      <div data-testid="institution-notfound" className="p-8 text-slate-500 text-center">
        Institution not found
      </div>
    );

  return (
    <div data-testid="institution-profile" className="max-w-5xl mx-auto animate-fade-in">
      <button onClick={() => navigate(-1)} className="btn-ghost inline-flex items-center gap-1.5 mb-6 text-primary-600">
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" /></svg>
        Back
      </button>

      <div className="mb-8">
        <h1 className="page-title">{profile.name}</h1>
        {profile.ico && <p className="text-slate-500 text-sm mt-1 font-medium">IČO: <span className="font-mono">{profile.ico}</span></p>}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Spend" value={formatEur(profile.total_spend)} color="blue" />
        <StatCard label="Contracts" value={profile.contract_count.toLocaleString()} color="green" />
        <StatCard label="Avg Value" value={formatCompact(profile.avg_value)} color="amber" />
        <StatCard label="Max Value" value={formatCompact(profile.max_value)} color="purple" />
      </div>

      {/* Trend chart */}
      {profile.trend.length > 0 && (
        <section className="mb-8 chart-container">
          <h2 className="section-title mb-4">Spending Trend</h2>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={profile.trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="period" tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <YAxis tickFormatter={(v: number) => formatCompact(v)} tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <Tooltip formatter={(v: number | undefined) => formatEur(v ?? 0)} contentStyle={{ borderRadius: '0.75rem', border: '1px solid #e2e8f0' }} />
              <Line type="monotone" dataKey="value" stroke="#2563eb" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* Top vendors */}
      {profile.top_vendors.length > 0 && (
        <section className="mb-8 chart-container">
          <h2 className="section-title mb-4">Top Vendors</h2>
          <ResponsiveContainer width="100%" height={Math.max(200, profile.top_vendors.length * 36)}>
            <RBarChart data={profile.top_vendors} layout="vertical" margin={{ left: 120, right: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" horizontal={false} />
              <XAxis type="number" tickFormatter={(v: number) => formatCompact(v)} tick={{ fontSize: 11 }} stroke="#94a3b8" />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 11 }} width={110} stroke="#94a3b8" />
              <Tooltip formatter={(v: number | undefined) => formatEur(v ?? 0)} contentStyle={{ borderRadius: '0.75rem', border: '1px solid #e2e8f0' }} />
              <Bar dataKey="total_spend" fill="#3b82f6" radius={[0, 6, 6, 0]} />
            </RBarChart>
          </ResponsiveContainer>
        </section>
      )}

      {/* Recent contracts */}
      {profile.contracts.length > 0 && (
        <section>
          <h2 className="section-title mb-4">Contracts ({profile.contracts.length})</h2>
          <div className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Vendor</th>
                    <th className="text-right">Value</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {profile.contracts.map((c) => (
                    <tr key={c.contract_id}>
                      <td className="max-w-[250px] truncate">
                        <Link to={`/contract/${c.contract_id}`} className="text-primary-600 hover:text-primary-800 font-medium transition-colors">
                          {c.contract_title || '—'}
                        </Link>
                      </td>
                      <td className="text-slate-600">{c.supplier || '—'}</td>
                      <td className="text-right font-mono tabular-nums">{formatEur(c.price_numeric_eur)}</td>
                      <td className="text-slate-600">{formatDate(c.published_date)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}

const ACCENT_COLORS = {
  blue: 'from-primary-500 to-primary-600',
  green: 'from-green-500 to-green-600',
  amber: 'from-amber-500 to-amber-600',
  purple: 'from-purple-500 to-purple-600',
};

function StatCard({ label, value, color = 'blue' }: { label: string; value: string; color?: keyof typeof ACCENT_COLORS }) {
  return (
    <div className="stat-card">
      <div className={`w-8 h-1 rounded-full bg-gradient-to-r ${ACCENT_COLORS[color]} mb-3`} />
      <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{label}</div>
      <div className="text-xl font-bold text-slate-800 mt-1 tabular-nums">{value}</div>
    </div>
  );
}
