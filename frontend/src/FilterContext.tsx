/**
 * FilterContext
 *
 * Provides shared filter state and dropdown option lists across all
 * pages/tabs. Lifting this state here means filters survive
 * in-app navigation — switching from Dashboard to BenchmarkView or
 * TimeView retains the active filter without re-encoding it into
 * every possible URL schema.
 *
 * Initialization strategy:
 *  - On first mount the context reads the current URL search params
 *    (via parseUrlState) so that deep-linked URLs still work.
 *  - Dropdown option lists (institutions, categories, vendors,
 *    awardTypes) are loaded from the API once and cached for the
 *    lifetime of the app session.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  type ReactNode,
} from 'react';
import type { FilterState } from './types';
import { fetchAggregations } from './api';
import { parseUrlState } from './url-state';

// ── Context shape ──────────────────────────────────────────────────

export interface FilterContextValue {
  /** The active global filter applied across all pages. */
  filters: FilterState;
  /** Replace the global filter (resets page counters in each page). */
  setFilters: (f: FilterState) => void;

  // Dropdown option lists (populated once from the API).
  institutions: string[];
  categories: string[];
  vendors: string[];
  awardTypes: string[];
  optionsLoaded: boolean;
}

const FilterContext = createContext<FilterContextValue | null>(null);

// ── Provider ───────────────────────────────────────────────────────

export function FilterProvider({ children }: { children: ReactNode }) {
  // Seed initial state from the current URL so that deep-linked pages
  // (e.g. /benchmark?date_from=2024-01-01) start with the right filters.
  const [filters, setFilters] = useState<FilterState>(
    () => parseUrlState(window.location.search).filters,
  );

  const [institutions, setInstitutions] = useState<string[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [vendors, setVendors] = useState<string[]>([]);
  const [awardTypes, setAwardTypes] = useState<string[]>([]);
  const [optionsLoaded, setOptionsLoaded] = useState(false);

  // Fetch dropdown options exactly once.
  const fetchedRef = useRef(false);
  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    Promise.all([
      fetchAggregations({}, 'buyer'),
      fetchAggregations({}, 'category'),
      fetchAggregations({}, 'supplier'),
      fetchAggregations({}, 'award_type'),
    ])
      .then(([instRes, catRes, vendRes, awardRes]) => {
        setInstitutions(instRes.results.map((r) => r.group_value));
        setCategories(catRes.results.map((r) => r.group_value));
        setVendors(vendRes.results.map((r) => r.group_value));
        setAwardTypes(awardRes.results.map((r) => r.group_value));
        setOptionsLoaded(true);
      })
      .catch(() => {
        // Non-fatal — dropdowns will be empty but the app still works.
        setOptionsLoaded(true);
      });
  }, []);

  return (
    <FilterContext.Provider
      value={{ filters, setFilters, institutions, categories, vendors, awardTypes, optionsLoaded }}
    >
      {children}
    </FilterContext.Provider>
  );
}

// ── Hook ───────────────────────────────────────────────────────────

/**
 * Returns the shared filter context.
 * Must be used inside a <FilterProvider>.
 */
export function useFilterContext(): FilterContextValue {
  const ctx = useContext(FilterContext);
  if (!ctx) {
    throw new Error('useFilterContext must be used inside <FilterProvider>');
  }
  return ctx;
}
