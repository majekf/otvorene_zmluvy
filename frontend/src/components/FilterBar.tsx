/**
 * FilterBar Component
 *
 * Renders filter controls for institution, date range, category,
 * vendor, ICO, value range, award type, and text search.
 * All changes update the URL state via the onChange callback.
 */

import { useState, useEffect, useMemo, useRef } from 'react';
import type { FilterState } from '../types';

interface FilterBarProps {
  filters: FilterState;
  onChange: (filters: FilterState) => void;
  institutions?: string[];
  categories?: string[];
  vendors?: string[];
  institutionIcos?: string[];
  vendorIcos?: string[];
  institutionIcoMap?: Record<string, string>;
  vendorIcoMap?: Record<string, string>;
  institutionCounts?: Record<string, number>;
  vendorCounts?: Record<string, number>;
  institutionIcoCounts?: Record<string, number>;
  vendorIcoCounts?: Record<string, number>;
  categoryCounts?: Record<string, number>;
  awardTypes?: string[];
  optionsLoaded?: boolean;
}

function sortAlpha(values: string[]): string[] {
  return [...values].sort((a, b) => a.localeCompare(b, 'sk', { sensitivity: 'base' }));
}

function rankAndFilter(values: string[], rawQuery: string): string[] {
  const query = rawQuery.trim().toLowerCase();
  if (!query) return values;
  return values
    .filter((n) => n.toLowerCase().includes(query))
    .sort((a, b) => {
      const an = a.toLowerCase();
      const bn = b.toLowerCase();
      const ai = an.indexOf(query);
      const bi = bn.indexOf(query);
      const aWordStart = an.includes(` ${query}`);
      const bWordStart = bn.includes(` ${query}`);
      const aStarts = an.startsWith(query);
      const bStarts = bn.startsWith(query);
      const scoreA = aStarts ? 0 : aWordStart ? 1 : 2;
      const scoreB = bStarts ? 0 : bWordStart ? 1 : 2;
      if (scoreA !== scoreB) return scoreA - scoreB;
      if (ai !== bi) return ai - bi;
      return a.localeCompare(b, 'sk', { sensitivity: 'base' });
    });
}

function selectedFirst(values: string[], selected: string[] = []): string[] {
  const selectedSet = new Set(selected);
  const top = values.filter((v) => selectedSet.has(v));
  const rest = values.filter((v) => !selectedSet.has(v));
  return [...top, ...rest];
}

export default function FilterBar({
  filters,
  onChange,
  institutions = [],
  categories = [],
  vendors = [],
  institutionIcos = [],
  vendorIcos = [],
  institutionIcoMap = {},
  vendorIcoMap = {},
  institutionCounts = {},
  vendorCounts = {},
  institutionIcoCounts = {},
  vendorIcoCounts = {},
  categoryCounts = {},
  awardTypes = ['direct_award', 'open_tender', 'negotiated', 'unknown'],
  optionsLoaded = false,
}: FilterBarProps) {
  // Kept for backward compatibility of parent props; synchronisation now runs via shared slicer counts.
  void institutionIcoMap;
  void vendorIcoMap;

  const [textInput, setTextInput] = useState(filters.text_search || '');
  const [institutionSearch, setInstitutionSearch] = useState('');
  const [vendorSearch, setVendorSearch] = useState('');
  const [institutionIcoSearch, setInstitutionIcoSearch] = useState('');
  const [vendorIcoSearch, setVendorIcoSearch] = useState('');
  const [categorySearch, setCategorySearch] = useState('');

  const [institutionOpen, setInstitutionOpen] = useState(false);
  const [vendorOpen, setVendorOpen] = useState(false);
  const [institutionIcoOpen, setInstitutionIcoOpen] = useState(false);
  const [vendorIcoOpen, setVendorIcoOpen] = useState(false);
  const [categoryOpen, setCategoryOpen] = useState(false);

  const institutionRef = useRef<HTMLDivElement | null>(null);
  const vendorRef = useRef<HTMLDivElement | null>(null);
  const institutionIcoRef = useRef<HTMLDivElement | null>(null);
  const vendorIcoRef = useRef<HTMLDivElement | null>(null);
  const categoryRef = useRef<HTMLDivElement | null>(null);

  const sortedInstitutions = useMemo(() => sortAlpha(institutions), [institutions]);
  const sortedVendors = useMemo(() => sortAlpha(vendors), [vendors]);
  const sortedInstitutionIcos = useMemo(() => sortAlpha(institutionIcos), [institutionIcos]);
  const sortedVendorIcos = useMemo(() => sortAlpha(vendorIcos), [vendorIcos]);
  const sortedCategories = useMemo(() => sortAlpha(categories), [categories]);

  const filteredInstitutions = useMemo(
    () => rankAndFilter(sortedInstitutions, institutionSearch),
    [sortedInstitutions, institutionSearch],
  );
  const filteredVendors = useMemo(
    () => rankAndFilter(sortedVendors, vendorSearch),
    [sortedVendors, vendorSearch],
  );
  const filteredInstitutionIcos = useMemo(
    () => rankAndFilter(sortedInstitutionIcos, institutionIcoSearch),
    [sortedInstitutionIcos, institutionIcoSearch],
  );
  const filteredVendorIcos = useMemo(
    () => rankAndFilter(sortedVendorIcos, vendorIcoSearch),
    [sortedVendorIcos, vendorIcoSearch],
  );
  const filteredCategories = useMemo(
    () => rankAndFilter(sortedCategories, categorySearch),
    [sortedCategories, categorySearch],
  );
  const anySlicerActive =
    (filters.institutions?.length || 0) > 0 ||
    (filters.institution_icos?.length || 0) > 0 ||
    (filters.vendors?.length || 0) > 0 ||
    (filters.vendor_icos?.length || 0) > 0 ||
    (filters.categories?.length || 0) > 0;
  const availableInstitutions = useMemo(
    () => sortedInstitutions.filter((name) => (institutionCounts[name] ?? 0) > 0),
    [sortedInstitutions, institutionCounts],
  );
  const availableVendors = useMemo(
    () => sortedVendors.filter((name) => (vendorCounts[name] ?? 0) > 0),
    [sortedVendors, vendorCounts],
  );
  const availableInstitutionIcos = useMemo(
    () => sortedInstitutionIcos.filter((ico) => (institutionIcoCounts[ico] ?? 0) > 0),
    [sortedInstitutionIcos, institutionIcoCounts],
  );
  const availableVendorIcos = useMemo(
    () => sortedVendorIcos.filter((ico) => (vendorIcoCounts[ico] ?? 0) > 0),
    [sortedVendorIcos, vendorIcoCounts],
  );
  const availableCategories = useMemo(
    () => sortedCategories.filter((name) => (categoryCounts[name] ?? 0) > 0),
    [sortedCategories, categoryCounts],
  );
  const effectiveInstitutions = useMemo(
    () => (filters.institutions?.length ? filters.institutions : anySlicerActive ? availableInstitutions : []),
    [filters.institutions, anySlicerActive, availableInstitutions],
  );
  const effectiveVendors = useMemo(
    () => (filters.vendors?.length ? filters.vendors : anySlicerActive ? availableVendors : []),
    [filters.vendors, anySlicerActive, availableVendors],
  );
  const effectiveInstitutionIcos = useMemo(
    () => (filters.institution_icos?.length ? filters.institution_icos : anySlicerActive ? availableInstitutionIcos : []),
    [filters.institution_icos, anySlicerActive, availableInstitutionIcos],
  );
  const effectiveVendorIcos = useMemo(
    () => (filters.vendor_icos?.length ? filters.vendor_icos : anySlicerActive ? availableVendorIcos : []),
    [filters.vendor_icos, anySlicerActive, availableVendorIcos],
  );
  const effectiveCategories = useMemo(
    () => (filters.categories?.length ? filters.categories : anySlicerActive ? availableCategories : []),
    [filters.categories, anySlicerActive, availableCategories],
  );
  const orderedInstitutions = useMemo(
    () => selectedFirst(filteredInstitutions, effectiveInstitutions),
    [filteredInstitutions, effectiveInstitutions],
  );
  const orderedVendors = useMemo(
    () => selectedFirst(filteredVendors, effectiveVendors),
    [filteredVendors, effectiveVendors],
  );
  const orderedInstitutionIcos = useMemo(
    () => selectedFirst(filteredInstitutionIcos, effectiveInstitutionIcos),
    [filteredInstitutionIcos, effectiveInstitutionIcos],
  );
  const orderedVendorIcos = useMemo(
    () => selectedFirst(filteredVendorIcos, effectiveVendorIcos),
    [filteredVendorIcos, effectiveVendorIcos],
  );
  const orderedCategories = useMemo(
    () => selectedFirst(filteredCategories, effectiveCategories),
    [filteredCategories, effectiveCategories],
  );
  const selectedInstitutionIcoSet = useMemo(() => {
    const out = new Set(effectiveInstitutionIcos);
    for (const name of effectiveInstitutions) {
      const ico = institutionIcoMap[name];
      if (ico) out.add(ico);
    }
    return out;
  }, [effectiveInstitutionIcos, effectiveInstitutions, institutionIcoMap]);
  const selectedVendorIcoSet = useMemo(() => {
    const out = new Set(effectiveVendorIcos);
    for (const name of effectiveVendors) {
      const ico = vendorIcoMap[name];
      if (ico) out.add(ico);
    }
    return out;
  }, [effectiveVendorIcos, effectiveVendors, vendorIcoMap]);

  useEffect(() => {
    setTextInput(filters.text_search || '');
  }, [filters.text_search]);

  useEffect(() => {
    function onDocMouseDown(e: MouseEvent) {
      const target = e.target as Node;
      if (institutionRef.current && !institutionRef.current.contains(target)) setInstitutionOpen(false);
      if (vendorRef.current && !vendorRef.current.contains(target)) setVendorOpen(false);
      if (institutionIcoRef.current && !institutionIcoRef.current.contains(target)) setInstitutionIcoOpen(false);
      if (vendorIcoRef.current && !vendorIcoRef.current.contains(target)) setVendorIcoOpen(false);
      if (categoryRef.current && !categoryRef.current.contains(target)) setCategoryOpen(false);
    }

    document.addEventListener('mousedown', onDocMouseDown);
    return () => document.removeEventListener('mousedown', onDocMouseDown);
  }, []);

  function update(patch: Partial<FilterState>) {
    onChange({ ...filters, ...patch });
  }

  function handleTextSubmit(e: React.FormEvent) {
    e.preventDefault();
    update({ text_search: textInput || undefined });
  }

  function handleReset() {
    setTextInput('');
    setInstitutionSearch('');
    setVendorSearch('');
    setInstitutionIcoSearch('');
    setVendorIcoSearch('');
    setCategorySearch('');
    setInstitutionOpen(false);
    setVendorOpen(false);
    setInstitutionIcoOpen(false);
    setVendorIcoOpen(false);
    setCategoryOpen(false);
    onChange({});
  }

  function toggleInstitution(name: string) {
    const selected = effectiveInstitutions;
    const nextInstitutions = selected.includes(name)
      ? selected.filter((i) => i !== name)
      : [...selected, name];
    update({ institutions: nextInstitutions.length ? nextInstitutions : undefined });
  }

  function toggleVendor(name: string) {
    const selected = effectiveVendors;
    const nextVendors = selected.includes(name)
      ? selected.filter((v) => v !== name)
      : [...selected, name];
    update({ vendors: nextVendors.length ? nextVendors : undefined });
  }

  function toggleInstitutionIco(ico: string) {
    const selected = Array.from(selectedInstitutionIcoSet);
    const nextIcos = selected.includes(ico)
      ? selected.filter((i) => i !== ico)
      : [...selected, ico];

    update({
      institution_icos: nextIcos.length ? nextIcos : undefined,
    });
  }

  function toggleVendorIco(ico: string) {
    const selected = Array.from(selectedVendorIcoSet);
    const nextIcos = selected.includes(ico)
      ? selected.filter((i) => i !== ico)
      : [...selected, ico];

    update({
      vendor_icos: nextIcos.length ? nextIcos : undefined,
    });
  }

  function selectAllInstitutions() {
    const nextInstitutions = [...filteredInstitutions];
    update({ institutions: nextInstitutions.length ? nextInstitutions : undefined });
  }

  function selectAllVendors() {
    const nextVendors = [...filteredVendors];
    update({ vendors: nextVendors.length ? nextVendors : undefined });
  }

  function selectAllInstitutionIcos() {
    const nextIcos = [...filteredInstitutionIcos];
    update({
      institution_icos: nextIcos.length ? nextIcos : undefined,
    });
  }

  function selectAllVendorIcos() {
    const nextIcos = [...filteredVendorIcos];
    update({
      vendor_icos: nextIcos.length ? nextIcos : undefined,
    });
  }

  function clearInstitutions() {
    update({ institutions: undefined });
  }

  function clearVendors() {
    update({ vendors: undefined });
  }

  function clearInstitutionIcos() {
    update({ institution_icos: undefined });
  }

  function clearVendorIcos() {
    update({ vendor_icos: undefined });
  }

  function toggleCategory(name: string) {
    const selected = effectiveCategories;
    const next = selected.includes(name)
      ? selected.filter((c) => c !== name)
      : [...selected, name];
    update({ categories: next.length ? next : undefined });
  }

  function selectAllCategories() {
    const next = [...filteredCategories];
    update({ categories: next.length ? next : undefined });
  }

  function clearCategories() {
    update({ categories: undefined });
  }

  return (
    <div
      data-testid="filter-bar"
      className="glass-card p-5 relative z-30 overflow-visible"
      role="search"
      aria-label="Contract filters"
    >
      <div className="flex items-center gap-2 mb-4">
        <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z" /></svg>
        <span className="text-sm font-semibold text-slate-700">Filters</span>
      </div>
      <div className="flex flex-wrap gap-3 items-end">
        <div className="flex flex-col min-w-[250px] relative z-40" ref={institutionRef}>
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Institution</label>
          <button type="button" data-testid="filter-institution-trigger" className="form-input text-left flex items-center justify-between" onClick={() => setInstitutionOpen((v) => !v)}>
            <span className="truncate">{effectiveInstitutions.length ? `Selected: ${effectiveInstitutions.length}` : 'All institutions'}</span>
            <span className="text-slate-400">{institutionOpen ? '▴' : '▾'}</span>
          </button>
          {institutionOpen && (
            <div data-testid="filter-institution-dropdown" className="absolute z-[100] top-[calc(100%+6px)] left-0 w-full rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
              <input data-testid="filter-institution-search" type="text" className="form-input mb-2" placeholder="Search institutions..." value={institutionSearch} onChange={(e) => setInstitutionSearch(e.target.value)} />
              <div className="mb-2 flex items-center justify-between text-xs">
                <span data-testid="filter-institution-selected-count" className="text-slate-500">Selected: {effectiveInstitutions.length}</span>
                <div className="flex gap-2">
                  <button type="button" data-testid="filter-institution-select-all" className="text-slate-600 hover:text-slate-900" onClick={selectAllInstitutions}>Select all</button>
                  <button type="button" data-testid="filter-institution-clear" className="text-slate-600 hover:text-slate-900" onClick={clearInstitutions}>Clear</button>
                </div>
              </div>
              <div data-testid="filter-institution-list" className="max-h-36 overflow-y-auto space-y-1 pr-1">
                {filteredInstitutions.length === 0 && <p className="text-xs text-slate-400 px-1 py-1">No matches</p>}
                {orderedInstitutions.map((n) => (
                  <label key={n} className="flex items-center gap-2 text-sm text-slate-700 px-1 py-0.5">
                    <input
                      type="checkbox"
                      checked={effectiveInstitutions.includes(n)}
                      disabled={optionsLoaded && (institutionCounts[n] ?? 0) === 0 && !effectiveInstitutions.includes(n)}
                      onChange={() => toggleInstitution(n)}
                    />
                    <span className="flex-1 truncate">{n}</span>
                    <span className="text-xs text-slate-400 tabular-nums">{institutionCounts[n] ?? 0}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col min-w-[180px] relative z-40" ref={institutionIcoRef}>
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">IČO Institution</label>
          <button type="button" data-testid="filter-institution-ico-trigger" className="form-input text-left flex items-center justify-between" onClick={() => setInstitutionIcoOpen((v) => !v)}>
            <span className="truncate">{selectedInstitutionIcoSet.size ? `Selected: ${selectedInstitutionIcoSet.size}` : 'All institution IČO'}</span>
            <span className="text-slate-400">{institutionIcoOpen ? '▴' : '▾'}</span>
          </button>
          {institutionIcoOpen && (
            <div data-testid="filter-institution-ico-dropdown" className="absolute z-[100] top-[calc(100%+6px)] right-0 w-full max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
              <input data-testid="filter-institution-ico-search" type="text" className="form-input mb-2 w-full min-w-0" placeholder="Search institution IČO..." value={institutionIcoSearch} onChange={(e) => setInstitutionIcoSearch(e.target.value)} />
              <div className="mb-2 flex items-center justify-between text-xs">
                <span data-testid="filter-institution-ico-selected-count" className="text-slate-500">Selected: {selectedInstitutionIcoSet.size}</span>
                <div className="flex gap-2">
                  <button type="button" data-testid="filter-institution-ico-select-all" className="text-slate-600 hover:text-slate-900" onClick={selectAllInstitutionIcos}>Select all</button>
                  <button type="button" data-testid="filter-institution-ico-clear" className="text-slate-600 hover:text-slate-900" onClick={clearInstitutionIcos}>Clear</button>
                </div>
              </div>
              <div data-testid="filter-institution-ico-list" className="max-h-36 overflow-y-auto space-y-1 pr-1">
                {filteredInstitutionIcos.length === 0 && <p className="text-xs text-slate-400 px-1 py-1">No matches</p>}
                {orderedInstitutionIcos.map((ico) => (
                  <label key={ico} className="flex items-center gap-2 text-sm text-slate-700 px-1 py-0.5">
                    <input
                      type="checkbox"
                      checked={selectedInstitutionIcoSet.has(ico)}
                      disabled={optionsLoaded && (institutionIcoCounts[ico] ?? 0) === 0 && !selectedInstitutionIcoSet.has(ico)}
                      onChange={() => toggleInstitutionIco(ico)}
                    />
                    <span className="flex-1 truncate">{ico}</span>
                    <span className="text-xs text-slate-400 tabular-nums">{institutionIcoCounts[ico] ?? 0}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col min-w-[250px] relative z-40" ref={vendorRef}>
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Vendor</label>
          <button type="button" data-testid="filter-vendor-trigger" className="form-input text-left flex items-center justify-between" onClick={() => setVendorOpen((v) => !v)}>
            <span className="truncate">{effectiveVendors.length ? `Selected: ${effectiveVendors.length}` : 'All vendors'}</span>
            <span className="text-slate-400">{vendorOpen ? '▴' : '▾'}</span>
          </button>
          {vendorOpen && (
            <div data-testid="filter-vendor-dropdown" className="absolute z-[100] top-[calc(100%+6px)] left-0 w-full rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
              <input data-testid="filter-vendor-search" type="text" className="form-input mb-2" placeholder="Search vendors..." value={vendorSearch} onChange={(e) => setVendorSearch(e.target.value)} />
              <div className="mb-2 flex items-center justify-between text-xs">
                <span data-testid="filter-vendor-selected-count" className="text-slate-500">Selected: {effectiveVendors.length}</span>
                <div className="flex gap-2">
                  <button type="button" data-testid="filter-vendor-select-all" className="text-slate-600 hover:text-slate-900" onClick={selectAllVendors}>Select all</button>
                  <button type="button" data-testid="filter-vendor-clear" className="text-slate-600 hover:text-slate-900" onClick={clearVendors}>Clear</button>
                </div>
              </div>
              <div data-testid="filter-vendor-list" className="max-h-36 overflow-y-auto space-y-1 pr-1">
                {filteredVendors.length === 0 && <p className="text-xs text-slate-400 px-1 py-1">No matches</p>}
                {orderedVendors.map((n) => (
                  <label key={n} className="flex items-center gap-2 text-sm text-slate-700 px-1 py-0.5">
                    <input
                      type="checkbox"
                      checked={effectiveVendors.includes(n)}
                      disabled={optionsLoaded && (vendorCounts[n] ?? 0) === 0 && !effectiveVendors.includes(n)}
                      onChange={() => toggleVendor(n)}
                    />
                    <span className="flex-1 truncate">{n}</span>
                    <span className="text-xs text-slate-400 tabular-nums">{vendorCounts[n] ?? 0}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col min-w-[180px] relative z-40" ref={vendorIcoRef}>
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">IČO Vendor</label>
          <button type="button" data-testid="filter-vendor-ico-trigger" className="form-input text-left flex items-center justify-between" onClick={() => setVendorIcoOpen((v) => !v)}>
            <span className="truncate">{selectedVendorIcoSet.size ? `Selected: ${selectedVendorIcoSet.size}` : 'All vendor IČO'}</span>
            <span className="text-slate-400">{vendorIcoOpen ? '▴' : '▾'}</span>
          </button>
          {vendorIcoOpen && (
            <div data-testid="filter-vendor-ico-dropdown" className="absolute z-[100] top-[calc(100%+6px)] right-0 w-full max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
              <input data-testid="filter-vendor-ico-search" type="text" className="form-input mb-2 w-full min-w-0" placeholder="Search vendor IČO..." value={vendorIcoSearch} onChange={(e) => setVendorIcoSearch(e.target.value)} />
              <div className="mb-2 flex items-center justify-between text-xs">
                <span data-testid="filter-vendor-ico-selected-count" className="text-slate-500">Selected: {selectedVendorIcoSet.size}</span>
                <div className="flex gap-2">
                  <button type="button" data-testid="filter-vendor-ico-select-all" className="text-slate-600 hover:text-slate-900" onClick={selectAllVendorIcos}>Select all</button>
                  <button type="button" data-testid="filter-vendor-ico-clear" className="text-slate-600 hover:text-slate-900" onClick={clearVendorIcos}>Clear</button>
                </div>
              </div>
              <div data-testid="filter-vendor-ico-list" className="max-h-36 overflow-y-auto space-y-1 pr-1">
                {filteredVendorIcos.length === 0 && <p className="text-xs text-slate-400 px-1 py-1">No matches</p>}
                {orderedVendorIcos.map((ico) => (
                  <label key={ico} className="flex items-center gap-2 text-sm text-slate-700 px-1 py-0.5">
                    <input
                      type="checkbox"
                      checked={selectedVendorIcoSet.has(ico)}
                      disabled={optionsLoaded && (vendorIcoCounts[ico] ?? 0) === 0 && !selectedVendorIcoSet.has(ico)}
                      onChange={() => toggleVendorIco(ico)}
                    />
                    <span className="flex-1 truncate">{ico}</span>
                    <span className="text-xs text-slate-400 tabular-nums">{vendorIcoCounts[ico] ?? 0}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col min-w-[220px] relative z-40" ref={categoryRef}>
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Category</label>
          <button type="button" data-testid="filter-category-trigger" className="form-input text-left flex items-center justify-between" onClick={() => setCategoryOpen((v) => !v)}>
            <span className="truncate">{effectiveCategories.length ? `Selected: ${effectiveCategories.length}` : 'All categories'}</span>
            <span className="text-slate-400">{categoryOpen ? '▴' : '▾'}</span>
          </button>
          {categoryOpen && (
            <div data-testid="filter-category-dropdown" className="absolute z-[100] top-[calc(100%+6px)] right-0 w-full max-w-[calc(100vw-2rem)] rounded-xl border border-slate-200 bg-white p-2 shadow-lg">
              <input data-testid="filter-category-search" type="text" className="form-input mb-2 w-full min-w-0" placeholder="Search categories..." value={categorySearch} onChange={(e) => setCategorySearch(e.target.value)} />
              <div className="mb-2 flex items-center justify-between text-xs">
                <span data-testid="filter-category-selected-count" className="text-slate-500">Selected: {effectiveCategories.length}</span>
                <div className="flex gap-2">
                  <button type="button" data-testid="filter-category-select-all" className="text-slate-600 hover:text-slate-900" onClick={selectAllCategories}>Select all</button>
                  <button type="button" data-testid="filter-category-clear" className="text-slate-600 hover:text-slate-900" onClick={clearCategories}>Clear</button>
                </div>
              </div>
              <div data-testid="filter-category-list" className="max-h-36 overflow-y-auto space-y-1 pr-1">
                {orderedCategories.length === 0 && <p className="text-xs text-slate-400 px-1 py-1">No matches</p>}
                {orderedCategories.map((c) => (
                  <label key={c} className="flex items-center gap-2 text-sm text-slate-700 px-1 py-0.5">
                    <input
                      type="checkbox"
                      checked={effectiveCategories.includes(c)}
                      disabled={optionsLoaded && (categoryCounts[c] ?? 0) === 0 && !effectiveCategories.includes(c)}
                      onChange={() => toggleCategory(c)}
                    />
                    <span className="flex-1 truncate">{c}</span>
                    <span className="text-xs text-slate-400 tabular-nums">{categoryCounts[c] ?? 0}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Date from</label>
          <input data-testid="filter-date-from" type="date" className="form-input" value={filters.date_from || ''} onChange={(e) => update({ date_from: e.target.value || undefined })} />
        </div>
        <div className="flex flex-col">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Date to</label>
          <input data-testid="filter-date-to" type="date" className="form-input" value={filters.date_to || ''} onChange={(e) => update({ date_to: e.target.value || undefined })} />
        </div>

        <div className="flex flex-col">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Min value (€)</label>
          <input data-testid="filter-value-min" type="number" className="form-input w-28" placeholder="0" value={filters.value_min ?? ''} onChange={(e) => update({ value_min: e.target.value ? Number(e.target.value) : undefined })} />
        </div>
        <div className="flex flex-col">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Max value (€)</label>
          <input data-testid="filter-value-max" type="number" className="form-input w-28" placeholder="∞" value={filters.value_max ?? ''} onChange={(e) => update({ value_max: e.target.value ? Number(e.target.value) : undefined })} />
        </div>

        <div className="flex flex-col min-w-[140px]">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Award type</label>
          <select data-testid="filter-award-type" className="form-select" value={filters.award_types?.[0] || ''} onChange={(e) => update({ award_types: e.target.value ? [e.target.value] : undefined })}>
            <option value="">All types</option>
            {awardTypes.map((a) => (
              <option key={a} value={a}>{a}</option>
            ))}
          </select>
        </div>

        <form onSubmit={handleTextSubmit} className="flex flex-col">
          <label className="text-xs font-semibold text-slate-500 mb-1.5 tracking-wide uppercase">Search</label>
          <div className="flex gap-1.5">
            <input data-testid="filter-text-search" type="text" className="form-input w-48" placeholder="Search contracts…" value={textInput} onChange={(e) => setTextInput(e.target.value)} />
            <button type="submit" aria-label="Submit search" className="btn-primary">Search</button>
            <button type="button" data-testid="filter-reset" aria-label="Reset all filters" className="btn-secondary" onClick={handleReset}>Reset</button>
          </div>
        </form>
      </div>
    </div>
  );
}
