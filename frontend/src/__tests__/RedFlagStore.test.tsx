/**
 * Tests for RedFlagStore context and utility functions
 *
 * Covers: RedFlagProvider, dataset management, computed lookups,
 * severity utilities, and default dataset naming.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { RedFlagProvider, useRedFlagContext, severityToLabel, severityEmoji, severityColor, severityBgColor, defaultDatasetName } from '../RedFlagStore';
import type { RedFlagDataset, RedFlagOccurrence } from '../types';

// ── Test helper to access context ──────────────────────────────────

function TestConsumer({ onContext }: { onContext: (ctx: ReturnType<typeof useRedFlagContext>) => void }) {
  const ctx = useRedFlagContext();
  onContext(ctx);
  return <div data-testid="consumer">loaded</div>;
}

const mockDataset1: RedFlagDataset = {
  dataset_name: 'Test Dataset 1',
  created_at: '2026-03-11T07:00:00.000Z',
  total_flags: 3,
  total_contracts_evaluated: 100,
  rules_used: [
    { rule_id: 'threshold_proximity', rule_name: 'Threshold Proximity', severity_label: 'moderate', params: { threshold_eur: 50000 } },
  ],
  flags: [
    {
      contract_id: 'c1',
      contract_title: 'Contract 1',
      institution: 'Ministry A',
      vendor: 'Vendor X',
      ico_buyer: '111',
      ico_supplier: '222',
      price_numeric_eur: 49500,
      date_published: '2026-01-15',
      category: 'IT',
      award_type: 'direct_award',
      red_flag_type: 'threshold_proximity',
      red_flag_name: 'Threshold Proximity',
      severity: 'moderate',
      description: 'Near threshold',
    },
    {
      contract_id: 'c2',
      contract_title: 'Contract 2',
      institution: 'Ministry A',
      vendor: 'Vendor Y',
      ico_buyer: '111',
      ico_supplier: '333',
      price_numeric_eur: 48000,
      date_published: '2026-02-10',
      category: 'Construction',
      award_type: 'open_tender',
      red_flag_type: 'threshold_proximity',
      red_flag_name: 'Threshold Proximity',
      severity: 'moderate',
      description: 'Near threshold',
    },
    {
      contract_id: 'c3',
      contract_title: 'Contract 3',
      institution: 'Ministry B',
      vendor: 'Vendor X',
      ico_buyer: '444',
      ico_supplier: '222',
      price_numeric_eur: 99000,
      date_published: '2026-03-01',
      category: 'IT',
      award_type: 'direct_award',
      red_flag_type: 'threshold_proximity',
      red_flag_name: 'Threshold Proximity',
      severity: 'moderate',
      description: 'Near threshold',
    },
  ],
};

const mockDataset2: RedFlagDataset = {
  dataset_name: 'Test Dataset 2',
  created_at: '2026-03-12T10:00:00.000Z',
  total_flags: 2,
  total_contracts_evaluated: 100,
  rules_used: [
    { rule_id: 'vendor_concentration', rule_name: 'Vendor Concentration', severity_label: 'severe', params: { top_n: 1 } },
  ],
  flags: [
    {
      contract_id: 'c1',
      contract_title: 'Contract 1',
      institution: 'Ministry A',
      vendor: 'Vendor X',
      ico_buyer: '111',
      ico_supplier: '222',
      price_numeric_eur: 49500,
      date_published: '2026-01-15',
      category: 'IT',
      award_type: 'direct_award',
      red_flag_type: 'vendor_concentration',
      red_flag_name: 'Vendor Concentration',
      severity: 'severe',
      description: 'Vendor holds too much spend',
    },
    {
      contract_id: 'c4',
      contract_title: 'Contract 4',
      institution: 'Ministry C',
      vendor: 'Vendor Z',
      ico_buyer: '555',
      ico_supplier: '666',
      price_numeric_eur: 75000,
      date_published: '2026-02-20',
      category: 'Services',
      award_type: 'negotiated',
      red_flag_type: 'vendor_concentration',
      red_flag_name: 'Vendor Concentration',
      severity: 'severe',
      description: 'Vendor holds too much spend',
    },
  ],
};

// ── Utility function tests ─────────────────────────────────────────

describe('Red Flag Utility Functions', () => {
  describe('severityToLabel', () => {
    it('returns severe for values >= 0.7', () => {
      expect(severityToLabel(0.7)).toBe('severe');
      expect(severityToLabel(0.9)).toBe('severe');
      expect(severityToLabel(1.0)).toBe('severe');
    });

    it('returns moderate for values >= 0.4 and < 0.7', () => {
      expect(severityToLabel(0.4)).toBe('moderate');
      expect(severityToLabel(0.5)).toBe('moderate');
      expect(severityToLabel(0.69)).toBe('moderate');
    });

    it('returns mild for values < 0.4', () => {
      expect(severityToLabel(0.0)).toBe('mild');
      expect(severityToLabel(0.2)).toBe('mild');
      expect(severityToLabel(0.39)).toBe('mild');
    });
  });

  describe('severityEmoji', () => {
    it('returns correct emoji for each severity', () => {
      expect(severityEmoji('severe')).toBe('🔴');
      expect(severityEmoji('moderate')).toBe('🟠');
      expect(severityEmoji('mild')).toBe('🟡');
    });
  });

  describe('severityColor', () => {
    it('returns correct CSS class for each severity', () => {
      expect(severityColor('severe')).toContain('red');
      expect(severityColor('moderate')).toContain('orange');
      expect(severityColor('mild')).toContain('yellow');
    });
  });

  describe('severityBgColor', () => {
    it('returns background CSS class for each severity', () => {
      expect(severityBgColor('severe')).toContain('bg-red');
      expect(severityBgColor('moderate')).toContain('bg-orange');
      expect(severityBgColor('mild')).toContain('bg-yellow');
    });
  });

  describe('defaultDatasetName', () => {
    it('returns a string based on current datetime', () => {
      const name = defaultDatasetName();
      expect(name).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}$/);
    });

    it('does not contain colons or dots', () => {
      const name = defaultDatasetName();
      expect(name).not.toContain(':');
      expect(name).not.toContain('.');
    });
  });
});

// ── RedFlagProvider Context tests ──────────────────────────────────

describe('RedFlagProvider', () => {
  it('provides empty state initially', () => {
    let ctx: ReturnType<typeof useRedFlagContext> | null = null;
    render(
      <RedFlagProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </RedFlagProvider>,
    );
    expect(ctx).not.toBeNull();
    expect(ctx!.datasets).toEqual([]);
    expect(ctx!.datasetNames).toEqual([]);
    expect(ctx!.allFlagTypes).toEqual([]);
  });

  it('adds a dataset', () => {
    let ctx: ReturnType<typeof useRedFlagContext> | null = null;
    render(
      <RedFlagProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </RedFlagProvider>,
    );
    act(() => {
      ctx!.addDataset(mockDataset1);
    });
    expect(ctx!.datasets).toHaveLength(1);
    expect(ctx!.datasetNames).toEqual(['Test Dataset 1']);
  });

  it('replaces dataset with same name', () => {
    let ctx: ReturnType<typeof useRedFlagContext> | null = null;
    render(
      <RedFlagProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </RedFlagProvider>,
    );
    act(() => {
      ctx!.addDataset(mockDataset1);
    });
    act(() => {
      ctx!.addDataset({ ...mockDataset1, total_flags: 99 });
    });
    expect(ctx!.datasets).toHaveLength(1);
    expect(ctx!.datasets[0].total_flags).toBe(99);
  });

  it('removes a dataset', () => {
    let ctx: ReturnType<typeof useRedFlagContext> | null = null;
    render(
      <RedFlagProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </RedFlagProvider>,
    );
    act(() => {
      ctx!.addDataset(mockDataset1);
      ctx!.addDataset(mockDataset2);
    });
    act(() => {
      ctx!.removeDataset('Test Dataset 1');
    });
    expect(ctx!.datasets).toHaveLength(1);
    expect(ctx!.datasetNames).toEqual(['Test Dataset 2']);
  });

  it('computes allFlagTypes from all datasets', () => {
    let ctx: ReturnType<typeof useRedFlagContext> | null = null;
    render(
      <RedFlagProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </RedFlagProvider>,
    );
    act(() => {
      ctx!.addDataset(mockDataset1);
      ctx!.addDataset(mockDataset2);
    });
    expect(ctx!.allFlagTypes).toEqual(['threshold_proximity', 'vendor_concentration']);
  });

  it('returns flags for specific datasets', () => {
    let ctx: ReturnType<typeof useRedFlagContext> | null = null;
    render(
      <RedFlagProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </RedFlagProvider>,
    );
    act(() => {
      ctx!.addDataset(mockDataset1);
      ctx!.addDataset(mockDataset2);
    });
    const flagsDs1 = ctx!.getFlagsForDatasets(['Test Dataset 1']);
    expect(flagsDs1).toHaveLength(3);
    const flagsDs2 = ctx!.getFlagsForDatasets(['Test Dataset 2']);
    expect(flagsDs2).toHaveLength(2);
    const flagsAll = ctx!.getFlagsForDatasets([]);
    expect(flagsAll).toHaveLength(5);
  });

  it('builds contract flag map', () => {
    let ctx: ReturnType<typeof useRedFlagContext> | null = null;
    render(
      <RedFlagProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </RedFlagProvider>,
    );
    act(() => {
      ctx!.addDataset(mockDataset1);
      ctx!.addDataset(mockDataset2);
    });
    const map = ctx!.contractFlagMap([]);
    // c1 appears in both datasets
    expect(map.get('c1')).toHaveLength(2);
    expect(map.get('c2')).toHaveLength(1);
    expect(map.get('c3')).toHaveLength(1);
    expect(map.get('c4')).toHaveLength(1);
  });

  it('computes vendor flag counts', () => {
    let ctx: ReturnType<typeof useRedFlagContext> | null = null;
    render(
      <RedFlagProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </RedFlagProvider>,
    );
    act(() => {
      ctx!.addDataset(mockDataset1);
      ctx!.addDataset(mockDataset2);
    });
    const counts = ctx!.vendorFlagCounts([]);
    // Vendor X: c1 (from ds1 + ds2 = 1 unique), c3 (from ds1) = 2 unique contracts
    expect(counts.get('Vendor X')).toBe(2);
    // Vendor Y: c2 = 1
    expect(counts.get('Vendor Y')).toBe(1);
    // Vendor Z: c4 = 1
    expect(counts.get('Vendor Z')).toBe(1);
  });

  it('computes institution flag counts', () => {
    let ctx: ReturnType<typeof useRedFlagContext> | null = null;
    render(
      <RedFlagProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </RedFlagProvider>,
    );
    act(() => {
      ctx!.addDataset(mockDataset1);
      ctx!.addDataset(mockDataset2);
    });
    const counts = ctx!.institutionFlagCounts([]);
    // Ministry A: c1 + c2 = 2 unique contracts
    expect(counts.get('Ministry A')).toBe(2);
    // Ministry B: c3 = 1
    expect(counts.get('Ministry B')).toBe(1);
    // Ministry C: c4 = 1
    expect(counts.get('Ministry C')).toBe(1);
  });

  it('computes vendors in datasets', () => {
    let ctx: ReturnType<typeof useRedFlagContext> | null = null;
    render(
      <RedFlagProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </RedFlagProvider>,
    );
    act(() => {
      ctx!.addDataset(mockDataset1);
      ctx!.addDataset(mockDataset2);
    });
    const vendors = ctx!.vendorsInDatasets(['Test Dataset 1']);
    expect(vendors.has('Vendor X')).toBe(true);
    expect(vendors.has('Vendor Y')).toBe(true);
    expect(vendors.has('Vendor Z')).toBe(false);
  });

  it('computes institutions in datasets', () => {
    let ctx: ReturnType<typeof useRedFlagContext> | null = null;
    render(
      <RedFlagProvider>
        <TestConsumer onContext={(c) => { ctx = c; }} />
      </RedFlagProvider>,
    );
    act(() => {
      ctx!.addDataset(mockDataset1);
      ctx!.addDataset(mockDataset2);
    });
    const institutions = ctx!.institutionsInDatasets(['Test Dataset 2']);
    expect(institutions.has('Ministry A')).toBe(true);
    expect(institutions.has('Ministry B')).toBe(false);
    expect(institutions.has('Ministry C')).toBe(true);
  });
});

// ── RedFlagDataset type structure tests ────────────────────────────

describe('RedFlagDataset type validation', () => {
  it('has all required fields', () => {
    const ds = mockDataset1;
    expect(ds).toHaveProperty('dataset_name');
    expect(ds).toHaveProperty('created_at');
    expect(ds).toHaveProperty('total_flags');
    expect(ds).toHaveProperty('total_contracts_evaluated');
    expect(ds).toHaveProperty('rules_used');
    expect(ds).toHaveProperty('flags');
  });

  it('flags have all required fields', () => {
    const flag = mockDataset1.flags[0];
    expect(flag).toHaveProperty('contract_id');
    expect(flag).toHaveProperty('contract_title');
    expect(flag).toHaveProperty('institution');
    expect(flag).toHaveProperty('vendor');
    expect(flag).toHaveProperty('ico_buyer');
    expect(flag).toHaveProperty('ico_supplier');
    expect(flag).toHaveProperty('price_numeric_eur');
    expect(flag).toHaveProperty('date_published');
    expect(flag).toHaveProperty('category');
    expect(flag).toHaveProperty('award_type');
    expect(flag).toHaveProperty('red_flag_type');
    expect(flag).toHaveProperty('red_flag_name');
    expect(flag).toHaveProperty('severity');
    expect(flag).toHaveProperty('description');
  });

  it('severity is a valid value', () => {
    for (const flag of mockDataset1.flags) {
      expect(['mild', 'moderate', 'severe']).toContain(flag.severity);
    }
  });

  it('rules_used have correct structure', () => {
    const rule = mockDataset1.rules_used[0];
    expect(rule).toHaveProperty('rule_id');
    expect(rule).toHaveProperty('rule_name');
    expect(rule).toHaveProperty('severity_label');
    expect(rule).toHaveProperty('params');
    expect(['mild', 'moderate', 'severe']).toContain(rule.severity_label);
  });
});
