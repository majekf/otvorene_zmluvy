/**
 * CompareView Page (Phase 9)
 *
 * Contracts vs Subcontractors comparison view.
 * Shows clustered bar charts comparing aggregated data from
 * the primary contracts dataset and the subcontractors dataset.
 * Reuses FilterBar and GroupByControl for consistent global filtering.
 */

import { useState, useEffect, useCallback } from 'react';
import type { CompareAggregationsResponse, GroupByField } from '../types';
import { fetchCompareAggregations } from '../api';
import { formatEur, formatCompact } from '../utils';
import FilterBar from '../components/FilterBar';
import GroupByControl from '../components/GroupByControl';
import ClusteredBarChart from '../components/ClusteredBarChart';
import { useFilterContext } from '../FilterContext';
import WorkspaceToolbar from '../components/WorkspaceToolbar';
import { ChartSkeleton } from '../components/LoadingSkeleton';

type CompareMetric = 'total_spend' | 'contract_count' | 'avg_value';

const METRIC_OPTIONS: { id: CompareMetric; label: string }[] = [
  { id: 'total_spend', label: 'Total Spend' },
  { id: 'contract_count', label: 'Contract Count' },
  { id: 'avg_value', label: 'Average Value' },
];

export default function CompareView() {
  const { filters, setFilters, institutions, categories, vendors, awardTypes } = useFilterContext();
  const [groupBy, setGroupBy] = useState<GroupByField>('category');
  const [metric, setMetric] = useState<CompareMetric>('total_spend');
  const [data, setData] = useState<CompareAggregationsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchCompareAggregations(filters, groupBy)
      .then((res) => setData(res))
      .catch((err) => setError(err.message ?? 'Failed to load comparison data'))
      .finally(() => setLoading(false));
  }, [filters, groupBy]);

  const handleFilterChange = useCallback(
    (f: Parameters<typeof setFilters>[0]) => setFilters(f),
    [setFilters],
  );

  const cs = data?.contracts_summary;
  const ss = data?.subcontractors_summary;

  return (
    <div data-testid="compare-view" className="space-y-6 animate-fade-in">
      <div>
        <h1 className="page-title">Contracts vs Subcontractors</h1>
        <p className="text-sm text-slate-500 mt-1">
          Compare aggregated data between the primary contract dataset and the
          subcontractors dataset side-by-side.
        </p>
      </div>

      <WorkspaceToolbar filters={filters} mode="compare" />

      <FilterBar
        filters={filters}
        onChange={handleFilterChange}
        institutions={institutions}
        categories={categories}
        vendors={vendors}
        awardTypes={awardTypes}
      />

      {/* Controls row */}
      <div className="flex flex-wrap items-center gap-4">
        <GroupByControl value={groupBy} onChange={setGroupBy} />
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-slate-600">Metric:</span>
          {METRIC_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              data-testid={`metric-btn-${opt.id}`}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-all font-medium ${
                metric === opt.id
                  ? 'bg-primary-600 text-white border-primary-600 shadow-sm'
                  : 'bg-white text-slate-700 border-slate-200 hover:border-primary-400'
              }`}
              onClick={() => setMetric(opt.id)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Summary cards */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="compare-summary">
          <div className="glass-card p-5">
            <h3 className="text-sm font-semibold text-slate-500 mb-2 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-blue-500 inline-block" />
              Contracts
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs text-slate-400">Total Spend</div>
                <div className="text-lg font-bold text-slate-800">{formatCompact(cs?.total_spend ?? 0)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Count</div>
                <div className="text-lg font-bold text-slate-800">{cs?.contract_count ?? 0}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Avg Value</div>
                <div className="text-lg font-bold text-slate-800">{formatCompact(cs?.avg_value ?? 0)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Max Value</div>
                <div className="text-lg font-bold text-slate-800">{formatCompact(cs?.max_value ?? 0)}</div>
              </div>
            </div>
          </div>

          <div className="glass-card p-5">
            <h3 className="text-sm font-semibold text-slate-500 mb-2 flex items-center gap-2">
              <span className="w-3 h-3 rounded-full bg-orange-500 inline-block" />
              Subcontractors
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <div className="text-xs text-slate-400">Total Spend</div>
                <div className="text-lg font-bold text-slate-800">{formatCompact(ss?.total_spend ?? 0)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Count</div>
                <div className="text-lg font-bold text-slate-800">{ss?.contract_count ?? 0}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Avg Value</div>
                <div className="text-lg font-bold text-slate-800">{formatCompact(ss?.avg_value ?? 0)}</div>
              </div>
              <div>
                <div className="text-xs text-slate-400">Max Value</div>
                <div className="text-lg font-bold text-slate-800">{formatCompact(ss?.max_value ?? 0)}</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {!data?.has_subcontractors && !loading && (
        <div className="glass-card p-5 text-center text-sm text-amber-600 bg-amber-50 border border-amber-200">
          Subcontractors data is not loaded. Set <code>GOVLENS_SUBCONTRACTORS_DATA_PATH</code> environment variable.
        </div>
      )}

      {/* Chart */}
      {loading && <div data-testid="compare-loading"><ChartSkeleton /></div>}

      {error && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl p-4">
          {error}
        </div>
      )}

      {data && data.data.length > 0 && (
        <div className="glass-card p-5" data-testid="compare-chart-container">
          <h2 className="section-title mb-4">
            {METRIC_OPTIONS.find((o) => o.id === metric)?.label ?? metric} by {groupBy}
          </h2>
          <ClusteredBarChart data={data.data} metric={metric} />
        </div>
      )}

      {data && data.data.length === 0 && !loading && (
        <p className="text-sm text-slate-400">No data available for the selected filters.</p>
      )}
    </div>
  );
}
