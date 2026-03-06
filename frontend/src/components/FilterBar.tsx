/**
 * FilterBar Component
 *
 * Renders filter controls for institution, date range, category,
 * vendor, value range, award type, and text search.
 * All changes update the URL state via the onChange callback.
 */

import { useState, useEffect } from 'react';
import type { FilterState } from '../types';

interface FilterBarProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  institutions?: string[];
  categories?: string[];
  vendors?: string[];
  awardTypes?: string[];
}

export default function FilterBar({
  filters,
  onChange,
  institutions = [],
  categories = [],
  vendors = [],
  awardTypes = ['direct_award', 'open_tender', 'negotiated', 'unknown'],
}: FilterBarProps) {
  const [textInput, setTextInput] = useState(filters.text_search || '');

  useEffect(() => {
    setTextInput(filters.text_search || '');
  }, [filters.text_search]);

  function update(patch: Partial<FilterState>) {
    onChange({ ...filters, ...patch });
  }

  function handleTextSubmit(e: React.FormEvent) {
    e.preventDefault();
    update({ text_search: textInput || undefined });
  }

  function handleReset() {
    setTextInput('');
    onChange({});
  }

  return (
    <div data-testid="filter-bar" className="glass-card p-5" role="search" aria-label="Contract filters">
      <div className="flex items-center gap-2 mb-4">
        <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z" /></svg>
        <span className="text-sm font-semibold text-slate-700">Filters</span>
      </div>
      <div className="flex flex-wrap gap-3 items-end">
        {/* Institution selector */}
        <div className="flex flex-col min-w-[180px]">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Institution</label>
          <select
            data-testid="filter-institution"
            className="form-select"
            value={filters.institutions?.[0] || ''}
            onChange={(e) =>
              update({
                institutions: e.target.value ? [e.target.value] : undefined,
              })
            }
          >
            <option value="">All institutions</option>
            {institutions.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </div>

        {/* Date range */}
        <div className="flex flex-col">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Date from</label>
          <input
            data-testid="filter-date-from"
            type="date"
            className="form-input"
            value={filters.date_from || ''}
            onChange={(e) => update({ date_from: e.target.value || undefined })}
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Date to</label>
          <input
            data-testid="filter-date-to"
            type="date"
            className="form-input"
            value={filters.date_to || ''}
            onChange={(e) => update({ date_to: e.target.value || undefined })}
          />
        </div>

        {/* Category */}
        <div className="flex flex-col min-w-[140px]">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Category</label>
          <select
            data-testid="filter-category"
            className="form-select"
            value={filters.categories?.[0] || ''}
            onChange={(e) =>
              update({
                categories: e.target.value ? [e.target.value] : undefined,
              })
            }
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>

        {/* Vendor */}
        <div className="flex flex-col min-w-[180px]">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Vendor</label>
          <select
            data-testid="filter-vendor"
            className="form-select"
            value={filters.vendors?.[0] || ''}
            onChange={(e) =>
              update({
                vendors: e.target.value ? [e.target.value] : undefined,
              })
            }
          >
            <option value="">All vendors</option>
            {vendors.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </div>

        {/* Value range */}
        <div className="flex flex-col">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Min value (€)</label>
          <input
            data-testid="filter-value-min"
            type="number"
            className="form-input w-28"
            placeholder="0"
            value={filters.value_min ?? ''}
            onChange={(e) =>
              update({
                value_min: e.target.value ? Number(e.target.value) : undefined,
              })
            }
          />
        </div>
        <div className="flex flex-col">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Max value (€)</label>
          <input
            data-testid="filter-value-max"
            type="number"
            className="form-input w-28"
            placeholder="∞"
            value={filters.value_max ?? ''}
            onChange={(e) =>
              update({
                value_max: e.target.value ? Number(e.target.value) : undefined,
              })
            }
          />
        </div>

        {/* Award type */}
        <div className="flex flex-col min-w-[140px]">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Award type</label>
          <select
            data-testid="filter-award-type"
            className="form-select"
            value={filters.award_types?.[0] || ''}
            onChange={(e) =>
              update({
                award_types: e.target.value ? [e.target.value] : undefined,
              })
            }
          >
            <option value="">All types</option>
            {awardTypes.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>
        </div>

        {/* Text search */}
        <form onSubmit={handleTextSubmit} className="flex flex-col">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Search</label>
          <div className="flex gap-1.5">
            <input
              data-testid="filter-text-search"
              type="text"
              className="form-input w-48"
              placeholder="Search contracts…"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
            />
            <button
              type="submit"
              aria-label="Submit search"
              className="btn-primary"
            >
              Search
            </button>
            <button
              type="button"
              data-testid="filter-reset"
              aria-label="Reset all filters"
              className="btn-secondary"
              onClick={handleReset}
            >
              Reset
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
