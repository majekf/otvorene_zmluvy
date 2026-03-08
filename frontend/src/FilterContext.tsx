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
import { fetchAggregations, fetchInstitutions, fetchVendors, fetchFilterOptions } from './api';
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
  institutionIcos: string[];
  vendorIcos: string[];
  institutionIcoMap: Record<string, string>;
  vendorIcoMap: Record<string, string>;
  institutionCounts: Record<string, number>;
  vendorCounts: Record<string, number>;
  institutionIcoCounts: Record<string, number>;
  vendorIcoCounts: Record<string, number>;
  categoryCounts: Record<string, number>;
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
  const [institutionIcos, setInstitutionIcos] = useState<string[]>([]);
  const [vendorIcos, setVendorIcos] = useState<string[]>([]);
  const [institutionIcoMap, setInstitutionIcoMap] = useState<Record<string, string>>({});
  const [vendorIcoMap, setVendorIcoMap] = useState<Record<string, string>>({});
  const [institutionCounts, setInstitutionCounts] = useState<Record<string, number>>({});
  const [vendorCounts, setVendorCounts] = useState<Record<string, number>>({});
  const [institutionIcoCounts, setInstitutionIcoCounts] = useState<Record<string, number>>({});
  const [vendorIcoCounts, setVendorIcoCounts] = useState<Record<string, number>>({});
  const [categoryCounts, setCategoryCounts] = useState<Record<string, number>>({});
  const [awardTypes, setAwardTypes] = useState<string[]>([]);
  const [optionsLoaded, setOptionsLoaded] = useState(false);

  // Fetch name->ICO maps once from JSON-backed endpoints.
  const fetchedRef = useRef(false);
  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    Promise.all([fetchInstitutions(), fetchVendors(), fetchAggregations({}, 'award_type'), fetchFilterOptions({})])
      .then(([instRes, vendRes, awardRes, optionsRes]) => {
        const instMap: Record<string, string> = {};
        const vendMap: Record<string, string> = {};
        for (const r of instRes.institutions) if (r.ico) instMap[r.name] = r.ico;
        for (const r of vendRes.vendors) if (r.ico) vendMap[r.name] = r.ico;
        setInstitutions(optionsRes.institutions.map((o) => o.value));
        setVendors(optionsRes.vendors.map((o) => o.value));
        setInstitutionIcos(optionsRes.institution_icos.map((o) => o.value));
        setVendorIcos(optionsRes.vendor_icos.map((o) => o.value));
        setCategories(optionsRes.categories.map((o) => o.value));
        setInstitutionIcoMap(instMap);
        setVendorIcoMap(vendMap);
        setAwardTypes(awardRes.results.map((r) => r.group_value));
      })
      .catch(() => {
        // Non-fatal; dynamic options still load from /api/filter-options.
      });
  }, []);

  // Dynamic slicer options + counts. Each dimension is already
  // cross-filtered server-side (self-filter excluded).
  useEffect(() => {
    let cancelled = false;

    fetchFilterOptions(filters)
      .then((res) => {
        if (cancelled) return;
        const mergeSelected = (base: string[], selected?: string[]) =>
          Array.from(new Set([...(selected || []), ...base]));

        const inst = mergeSelected(res.institutions.map((o) => o.value), filters.institutions);
        const vend = mergeSelected(res.vendors.map((o) => o.value), filters.vendors);
        const instIco = mergeSelected(res.institution_icos.map((o) => o.value), filters.institution_icos);
        const vendIco = mergeSelected(res.vendor_icos.map((o) => o.value), filters.vendor_icos);
        const cat = mergeSelected(res.categories.map((o) => o.value), filters.categories);
        setInstitutions(inst);
        setVendors(vend);
        setInstitutionIcos(instIco);
        setVendorIcos(vendIco);
        setCategories(cat);
        setInstitutionCounts(Object.fromEntries(res.institutions.map((o) => [o.value, o.count])));
        setVendorCounts(Object.fromEntries(res.vendors.map((o) => [o.value, o.count])));
        setInstitutionIcoCounts(Object.fromEntries(res.institution_icos.map((o) => [o.value, o.count])));
        setVendorIcoCounts(Object.fromEntries(res.vendor_icos.map((o) => [o.value, o.count])));
        setCategoryCounts(Object.fromEntries(res.categories.map((o) => [o.value, o.count])));
        setOptionsLoaded(true);
      })
      .catch(() => {
        if (!cancelled) setOptionsLoaded(true);
      });

    return () => {
      cancelled = true;
    };
  }, [filters]);

  return (
    <FilterContext.Provider
      value={{
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
      }}
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
