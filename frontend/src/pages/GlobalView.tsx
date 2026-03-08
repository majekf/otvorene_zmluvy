/**
 * GlobalView Page (Phase 6)
 *
 * Global Search & Ranking mode: sortable ranking table for
 * institutions or vendors, with metric selector and click-through
 * to detailed profiles.
 */

import { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import type { RankingItem } from '../types';
import { fetchRankings } from '../api';
import FilterBar from '../components/FilterBar';
import { useFilterContext } from '../FilterContext';
import { formatEur } from '../utils';
import WorkspaceToolbar from '../components/WorkspaceToolbar';
import { TableSkeleton } from '../components/LoadingSkeleton';
import Pagination from '../components/Pagination';

type EntityType = 'institutions' | 'vendors';

const INSTITUTION_METRICS = [
  { id: 'total_spend', label: 'Total Spend' },
  { id: 'contract_count', label: 'Contracts' },
  { id: 'avg_value', label: 'Avg Value' },
  { id: 'max_value', label: 'Max Value' },
  { id: 'direct_award_rate', label: 'Direct Award Rate' },
  { id: 'vendor_concentration', label: 'Vendor Concentration' },
  { id: 'fragmentation_score', label: 'Fragmentation Score' },
];

const VENDOR_METRICS = [
  { id: 'total_spend', label: 'Total Spend' },
  { id: 'contract_count', label: 'Contracts' },
  { id: 'avg_value', label: 'Avg Value' },
  { id: 'max_value', label: 'Max Value' },
];

function formatMetricValue(metric: string, value: number): string {
  if (
    metric === 'direct_award_rate' ||
    metric === 'vendor_concentration' ||
    metric === 'fragmentation_score'
  ) {
    return `${(value * 100).toFixed(1)}%`;
  }
  if (metric === 'contract_count') return String(Math.round(value));
  return formatEur(value);
}

export default function GlobalView() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [entity, setEntity] = useState<EntityType>(
    (searchParams.get('entity') as EntityType) || 'institutions',
  );
  const [metric, setMetric] = useState(searchParams.get('metric') || 'total_spend');
  const {
    filters,
    setFilters,
    institutions,
    categories,
    vendors,
    institutionIcos,
    vendorIcos,
    institutionIcoMap,
    vendorIcoMap,
    institutionCounts,
    vendorCounts,
    institutionIcoCounts,
    vendorIcoCounts,
    categoryCounts,
    awardTypes,
    optionsLoaded,
  } = useFilterContext();
  const [rankings, setRankings] = useState<RankingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const PAGE_SIZE = 20;

  const metrics = entity === 'institutions' ? INSTITUTION_METRICS : VENDOR_METRICS;

  // Sync state → URL
  useEffect(() => {
    const params = new URLSearchParams();
    if (entity !== 'institutions') params.set('entity', entity);
    if (metric !== 'total_spend') params.set('metric', metric);
    if (page > 1) params.set('page', String(page));
    if (filters.institutions?.length) params.set('institutions', filters.institutions.join('|'));
    if (filters.date_from) params.set('date_from', filters.date_from);
    if (filters.date_to) params.set('date_to', filters.date_to);
    if (filters.categories?.length) params.set('categories', filters.categories.join('|'));
    if (filters.vendors?.length) params.set('vendors', filters.vendors.join('|'));
    if (filters.institution_icos?.length) params.set('institution_icos', filters.institution_icos.join('|'));
    if (filters.vendor_icos?.length) params.set('vendor_icos', filters.vendor_icos.join('|'));
    setSearchParams(params, { replace: true });
  }, [entity, metric, filters, page, setSearchParams]);

  // Fetch rankings
  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    fetchRankings(entity, metric, filters, page, PAGE_SIZE)
      .then(({ rankings: r, total: t }) => {
        if (!cancelled) {
          setRankings(r);
          setTotal(t);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [entity, metric, filters, page]);

  const handleFilterChange = useCallback((f: Parameters<typeof setFilters>[0]) => {
    setFilters(f);
    setPage(1);
  }, [setFilters]);

  // Reset metric when entity changes if the current metric isn't valid
  useEffect(() => {
    const validIds = metrics.map((m) => m.id);
    if (!validIds.includes(metric)) {
      setMetric('total_spend');
      setPage(1);
    }
  }, [entity, metric, metrics]);

  function entityLabel(item: RankingItem): string {
    return entity === 'institutions'
      ? item.institution || '—'
      : item.vendor || '—';
  }

  function entityLink(item: RankingItem): string {
    const name = entityLabel(item);
    return entity === 'institutions'
      ? `/institution/${encodeURIComponent(name)}`
      : `/vendor/${encodeURIComponent(name)}`;
  }

  return (
    <div data-testid="global-view" className="space-y-6 animate-fade-in">
      <div>
        <h1 className="page-title">Global Rankings</h1>
        <p className="text-sm text-slate-500 mt-1">
          Rank institutions and vendors by key metrics. Click through to see full profiles.
        </p>
      </div>

      <WorkspaceToolbar filters={filters} mode="rankings" />

      <FilterBar
        filters={filters}
        onChange={handleFilterChange}
        institutions={institutions}
        categories={categories}
        vendors={vendors}
        institutionIcos={institutionIcos}
        vendorIcos={vendorIcos}
        institutionIcoMap={institutionIcoMap}
        vendorIcoMap={vendorIcoMap}
        institutionCounts={institutionCounts}
        vendorCounts={vendorCounts}
        institutionIcoCounts={institutionIcoCounts}
        vendorIcoCounts={vendorIcoCounts}
        categoryCounts={categoryCounts}
        awardTypes={awardTypes}
        optionsLoaded={optionsLoaded}
      />

      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4">
        {/* Entity toggle */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Entity:</span>
          <div className="toggle-group">
            <button
              data-testid="entity-institutions"
              className={entity === 'institutions' ? 'active' : ''}
              onClick={() => { setEntity('institutions'); setPage(1); }}
            >
              Institutions
            </button>
            <button
              data-testid="entity-vendors"
              className={entity === 'vendors' ? 'active' : ''}
              onClick={() => { setEntity('vendors'); setPage(1); }}
            >
              Vendors
            </button>
          </div>
        </div>

        {/* Metric selector */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Metric:</span>
          {metrics.map((m) => (
            <button
              key={m.id}
              data-testid={`metric-${m.id}`}
              className={`px-3 py-1.5 text-sm rounded-lg border transition-all font-medium ${
                metric === m.id
                  ? 'bg-primary-50 border-primary-400 text-primary-700 shadow-sm'
                  : 'bg-white border-slate-200 text-slate-600 hover:border-primary-300'
              }`}
              onClick={() => { setMetric(m.id); setPage(1); }}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      {/* Ranking table */}
      {loading ? (
        <div data-testid="global-loading"><TableSkeleton rows={8} /></div>
      ) : rankings.length === 0 ? (
        <p className="text-slate-400 text-sm" data-testid="global-empty">No rankings available.</p>
      ) : (
        <>
          <div data-testid="rankings-table" className="glass-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th className="w-16">#</th>
                    <th>
                      {entity === 'institutions' ? 'Institution' : 'Vendor'}
                    </th>
                    <th className="text-right">
                      {metrics.find((m) => m.id === metric)?.label || metric}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {rankings.map((item) => (
                    <tr
                      key={item.rank}
                      data-testid={`rank-row-${item.rank}`}
                    >
                      <td className="font-mono text-slate-400">{item.rank}</td>
                      <td>
                        <Link
                          to={entityLink(item)}
                          className="text-primary-600 hover:text-primary-800 font-medium transition-colors"
                        >
                          {entityLabel(item)}
                        </Link>
                      </td>
                      <td className="text-right font-mono tabular-nums">
                        {formatMetricValue(metric, item.value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            total={total}
            onPageChange={setPage}
          />
        </>
      )}

      {/* Summary */}
      {total > 0 && (
        <div className="text-xs text-slate-400" data-testid="global-summary">
          Showing {rankings.length} of {total} {entity} ranked by {metrics.find((m) => m.id === metric)?.label || metric}
        </div>
      )}
    </div>
  );
}
