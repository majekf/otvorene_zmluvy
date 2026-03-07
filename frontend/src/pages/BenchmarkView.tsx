/**
 * BenchmarkView Page (Phase 6)
 *
 * Institution comparison mode: select 2–3 institutions and compare
 * them side-by-side on multiple metrics with bar charts.
 * Supports peer-group auto-discovery and min-contract threshold.
 */

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  Cell,
} from 'recharts';
import type { InstitutionSummary, BenchmarkMultiMetricResult } from '../types';
import { fetchInstitutions, fetchBenchmarkMultiMetric, fetchBenchmarkPeers } from '../api';
import { formatEur, formatCompact } from '../utils';
import WorkspaceToolbar from '../components/WorkspaceToolbar';
import { ChartSkeleton } from '../components/LoadingSkeleton';

const METRICS = [
  { id: 'total_spend', label: 'Total Spend' },
  { id: 'contract_count', label: 'Contracts' },
  { id: 'avg_value', label: 'Avg Value' },
  { id: 'max_value', label: 'Max Value' },
  { id: 'direct_award_rate', label: 'Direct Award Rate' },
  { id: 'vendor_concentration', label: 'Vendor Concentration' },
];

const BAR_COLORS = ['#2563eb', '#16a34a', '#f59e0b', '#ef4444'];

export default function BenchmarkView() {
  const [searchParams, setSearchParams] = useSearchParams();

  // Parse initial state from URL
  const urlInstitutions = searchParams.get('institutions')?.split('|').filter(Boolean) ?? [];
  const urlMinContracts = Number(searchParams.get('min_contracts')) || 1;

  const [allInstitutions, setAllInstitutions] = useState<InstitutionSummary[]>([]);
  const [selected, setSelected] = useState<string[]>(urlInstitutions);
  const [minContracts, setMinContracts] = useState(urlMinContracts);
  const [peers, setPeers] = useState<string[]>([]);
  const [comparisonData, setComparisonData] = useState<BenchmarkMultiMetricResult[]>([]);
  const [loading, setLoading] = useState(false);

  // Load institution list
  useEffect(() => {
    fetchInstitutions()
      .then(({ institutions }) => setAllInstitutions(institutions))
      .catch(() => {});
  }, []);

  // Sync state → URL
  useEffect(() => {
    const params = new URLSearchParams();
    if (selected.length) params.set('institutions', selected.join('|'));
    if (minContracts > 1) params.set('min_contracts', String(minContracts));
    setSearchParams(params, { replace: true });
  }, [selected, minContracts, setSearchParams]);

  // Fetch peer group when first institution selected
  useEffect(() => {
    if (selected.length !== 1) {
      setPeers([]);
      return;
    }
    fetchBenchmarkPeers(selected[0], minContracts)
      .then(({ peers: p }) => setPeers(p))
      .catch(() => setPeers([]));
  }, [selected, minContracts]);

  // Fetch comparison data
  useEffect(() => {
    if (selected.length < 2) {
      setComparisonData([]);
      return;
    }
    setLoading(true);
    fetchBenchmarkMultiMetric(selected, METRICS.map((m) => m.id))
      .then(({ results }) => setComparisonData(results))
      .catch(() => setComparisonData([]))
      .finally(() => setLoading(false));
  }, [selected]);

  const handleSelect = useCallback(
    (name: string) => {
      setSelected((prev) =>
        prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name].slice(0, 4),
      );
    },
    [],
  );

  // Build chart data for each metric
  function metricChart(metricId: string, label: string) {
    const chartData = comparisonData.map((r, idx) => ({
      institution: r.institution as string,
      value: (r[metricId] as number) ?? 0,
      fill: BAR_COLORS[idx % BAR_COLORS.length],
    }));
    if (!chartData.length) return null;

    const isRate = metricId === 'direct_award_rate' || metricId === 'vendor_concentration';
    const formatter = (v: number | undefined) => {
      if (typeof v !== 'number') return '';
      return isRate ? `${(v * 100).toFixed(1)}%` : formatCompact(v);
    };

    return (
      <div key={metricId} className="chart-container">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">{label}</h3>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis dataKey="institution" tick={{ fontSize: 11 }} stroke="#94a3b8" />
            <YAxis tickFormatter={formatter} tick={{ fontSize: 11 }} stroke="#94a3b8" />
            <Tooltip formatter={(v: number | undefined) => (typeof v === 'number' ? (isRate ? `${(v * 100).toFixed(1)}%` : formatEur(v)) : '')} contentStyle={{ borderRadius: '0.75rem', border: '1px solid #e2e8f0' }} />
            <Bar dataKey="value" radius={[6, 6, 0, 0]} isAnimationActive={false}>
              {chartData.map((entry, idx) => (
                <Cell key={`cell-${idx}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return (
    <div data-testid="benchmark-view" className="space-y-6 animate-fade-in">
      <div>
        <h1 className="page-title">Benchmark Comparison</h1>
        <p className="text-sm text-slate-500 mt-1">
          Select 2–4 institutions to compare side-by-side across multiple metrics.
        </p>
      </div>

      <WorkspaceToolbar
        filters={{ institutions: selected }}
        mode="benchmark"
      />

      {/* Institution selection */}
      <div className="glass-card p-5">
        <div className="flex items-center gap-4 mb-3">
          <h2 className="section-title">Select Institutions</h2>
          <label className="text-xs text-slate-500 flex items-center gap-1">
            Min contracts:
            <input
              type="number"
              data-testid="min-contracts"
              className="form-input w-20 text-sm"
              value={minContracts}
              min={1}
              onChange={(e) => setMinContracts(Math.max(1, Number(e.target.value) || 1))}
            />
          </label>
        </div>

        <div className="flex flex-wrap gap-2">
          {allInstitutions
            .filter((i) => i.contract_count >= minContracts)
            .map((inst) => (
              <button
                key={inst.name}
                data-testid={`inst-btn-${inst.name}`}
                className={`px-3 py-1.5 text-sm rounded-lg border transition-all font-medium ${
                  selected.includes(inst.name)
                    ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                    : 'bg-white text-slate-700 border-slate-200 hover:border-primary-400 hover:shadow-sm'
                }`}
                onClick={() => handleSelect(inst.name)}
              >
                {inst.name} ({inst.contract_count})
              </button>
            ))}
        </div>

        {/* Peer suggestions */}
        {selected.length === 1 && peers.length > 0 && (
          <div className="mt-3 text-sm" data-testid="peer-suggestions">
            <span className="text-slate-500">Suggested peers: </span>
            {peers.slice(0, 5).map((p) => (
              <button
                key={p}
                className="text-primary-600 hover:text-primary-800 font-medium mr-2 transition-colors"
                onClick={() => handleSelect(p)}
              >
                {p}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Selected institutions display */}
      {selected.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {selected.map((name, idx) => (
            <span
              key={name}
              className="inline-flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg font-medium"
              style={{ backgroundColor: `${BAR_COLORS[idx % BAR_COLORS.length]}15`, color: BAR_COLORS[idx % BAR_COLORS.length] }}
            >
              <Link to={`/institution/${encodeURIComponent(name)}`} className="hover:underline">
                {name}
              </Link>
              <button onClick={() => handleSelect(name)} className="ml-1 text-xs opacity-70 hover:opacity-100 transition-opacity">✕</button>
            </span>
          ))}
        </div>
      )}

      {/* Comparison charts */}
      {loading && <div data-testid="benchmark-loading"><ChartSkeleton /></div>}

      {comparisonData.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5" data-testid="benchmark-charts">
          {METRICS.map((m) => metricChart(m.id, m.label))}
        </div>
      )}

      {selected.length > 0 && selected.length < 2 && !loading && (
        <p className="text-sm text-slate-400">Select at least 2 institutions to start comparing.</p>
      )}
    </div>
  );
}
