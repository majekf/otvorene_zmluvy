/**
 * Red Flag Store
 *
 * Provides red flag dataset management across the application.
 * Loads datasets from JSON files and provides computed lookup maps
 * for filtering contracts by red flag information.
 */

import {
  createContext,
  useContext,
  useState,
  useMemo,
  useCallback,
  type ReactNode,
} from 'react';
import type {
  RedFlagDataset,
  RedFlagOccurrence,
  RedFlagSeverity,
} from './types';

// ── Context shape ──────────────────────────────────────────────────

export interface RedFlagContextValue {
  /** All loaded red flag datasets. */
  datasets: RedFlagDataset[];
  /** Add a dataset (e.g. from file upload or download). */
  addDataset: (dataset: RedFlagDataset) => void;
  /** Remove a dataset by name. */
  removeDataset: (name: string) => void;
  /** All available dataset names. */
  datasetNames: string[];
  /** All unique red flag types across all datasets. */
  allFlagTypes: string[];
  /**
   * Get merged flags from the specified datasets.
   * If datasetNames is empty, returns all flags.
   */
  getFlagsForDatasets: (datasetNames: string[]) => RedFlagOccurrence[];
  /** Map of contract_id → list of red flag occurrences across all/selected datasets. */
  contractFlagMap: (datasetNames: string[]) => Map<string, RedFlagOccurrence[]>;
  /** Map of vendor → count of flagged contracts in selected datasets. */
  vendorFlagCounts: (datasetNames: string[]) => Map<string, number>;
  /** Map of institution → count of flagged contracts in selected datasets. */
  institutionFlagCounts: (datasetNames: string[]) => Map<string, number>;
  /** Set of all vendor names that appear in selected datasets. */
  vendorsInDatasets: (datasetNames: string[]) => Set<string>;
  /** Set of all institution names that appear in selected datasets. */
  institutionsInDatasets: (datasetNames: string[]) => Set<string>;
}

const RedFlagContext = createContext<RedFlagContextValue | null>(null);

// ── Provider ───────────────────────────────────────────────────────

export function RedFlagProvider({ children }: { children: ReactNode }) {
  const [datasets, setDatasets] = useState<RedFlagDataset[]>([]);

  const addDataset = useCallback((dataset: RedFlagDataset) => {
    setDatasets((prev) => {
      // Replace if same name already exists
      const filtered = prev.filter((d) => d.dataset_name !== dataset.dataset_name);
      return [...filtered, dataset];
    });
  }, []);

  const removeDataset = useCallback((name: string) => {
    setDatasets((prev) => prev.filter((d) => d.dataset_name !== name));
  }, []);

  const datasetNames = useMemo(
    () => datasets.map((d) => d.dataset_name),
    [datasets],
  );

  const allFlagTypes = useMemo(() => {
    const types = new Set<string>();
    for (const ds of datasets) {
      for (const flag of ds.flags) {
        types.add(flag.red_flag_type);
      }
    }
    return Array.from(types).sort();
  }, [datasets]);

  const getFlagsForDatasets = useCallback(
    (names: string[]): RedFlagOccurrence[] => {
      const selected = names.length > 0
        ? datasets.filter((d) => names.includes(d.dataset_name))
        : datasets;
      return selected.flatMap((d) => d.flags);
    },
    [datasets],
  );

  const contractFlagMap = useCallback(
    (names: string[]): Map<string, RedFlagOccurrence[]> => {
      const flags = getFlagsForDatasets(names);
      const map = new Map<string, RedFlagOccurrence[]>();
      for (const flag of flags) {
        const key = flag.contract_id;
        if (!map.has(key)) map.set(key, []);
        map.get(key)!.push(flag);
      }
      return map;
    },
    [getFlagsForDatasets],
  );

  const vendorFlagCounts = useCallback(
    (names: string[]): Map<string, number> => {
      const flags = getFlagsForDatasets(names);
      const counts = new Map<string, number>();
      // Count unique contracts per vendor
      const vendorContracts = new Map<string, Set<string>>();
      for (const flag of flags) {
        if (!flag.vendor) continue;
        if (!vendorContracts.has(flag.vendor)) vendorContracts.set(flag.vendor, new Set());
        vendorContracts.get(flag.vendor)!.add(flag.contract_id);
      }
      for (const [vendor, contracts] of vendorContracts) {
        counts.set(vendor, contracts.size);
      }
      return counts;
    },
    [getFlagsForDatasets],
  );

  const institutionFlagCounts = useCallback(
    (names: string[]): Map<string, number> => {
      const flags = getFlagsForDatasets(names);
      const counts = new Map<string, number>();
      const instContracts = new Map<string, Set<string>>();
      for (const flag of flags) {
        if (!flag.institution) continue;
        if (!instContracts.has(flag.institution)) instContracts.set(flag.institution, new Set());
        instContracts.get(flag.institution)!.add(flag.contract_id);
      }
      for (const [inst, contracts] of instContracts) {
        counts.set(inst, contracts.size);
      }
      return counts;
    },
    [getFlagsForDatasets],
  );

  const vendorsInDatasets = useCallback(
    (names: string[]): Set<string> => {
      const flags = getFlagsForDatasets(names);
      return new Set(flags.map((f) => f.vendor).filter(Boolean));
    },
    [getFlagsForDatasets],
  );

  const institutionsInDatasets = useCallback(
    (names: string[]): Set<string> => {
      const flags = getFlagsForDatasets(names);
      return new Set(flags.map((f) => f.institution).filter(Boolean));
    },
    [getFlagsForDatasets],
  );

  return (
    <RedFlagContext.Provider
      value={{
        datasets,
        addDataset,
        removeDataset,
        datasetNames,
        allFlagTypes,
        getFlagsForDatasets,
        contractFlagMap,
        vendorFlagCounts,
        institutionFlagCounts,
        vendorsInDatasets,
        institutionsInDatasets,
      }}
    >
      {children}
    </RedFlagContext.Provider>
  );
}

// ── Hook ───────────────────────────────────────────────────────────

export function useRedFlagContext(): RedFlagContextValue {
  const ctx = useContext(RedFlagContext);
  if (!ctx) {
    throw new Error('useRedFlagContext must be used inside <RedFlagProvider>');
  }
  return ctx;
}

// ── Utility functions ──────────────────────────────────────────────

/** Map numeric severity (0-1) to a RedFlagSeverity label. */
export function severityToLabel(severity: number): RedFlagSeverity {
  if (severity >= 0.7) return 'severe';
  if (severity >= 0.4) return 'moderate';
  return 'mild';
}

/** Get display emoji for a severity level. */
export function severityEmoji(severity: RedFlagSeverity): string {
  switch (severity) {
    case 'severe': return '🔴';
    case 'moderate': return '🟠';
    case 'mild': return '🟡';
  }
}

/** Get CSS color class for a severity level. */
export function severityColor(severity: RedFlagSeverity): string {
  switch (severity) {
    case 'severe': return 'text-red-600';
    case 'moderate': return 'text-orange-500';
    case 'mild': return 'text-yellow-500';
  }
}

/** Get background CSS class for a severity level. */
export function severityBgColor(severity: RedFlagSeverity): string {
  switch (severity) {
    case 'severe': return 'bg-red-100 text-red-700';
    case 'moderate': return 'bg-orange-100 text-orange-700';
    case 'mild': return 'bg-yellow-100 text-yellow-700';
  }
}

/** Generate default dataset name from current datetime. */
export function defaultDatasetName(): string {
  return new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
}
