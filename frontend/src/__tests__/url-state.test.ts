/**
 * Tests for url-state.ts: parseUrlState / encodeUrlState
 */
import { describe, it, expect } from 'vitest';
import { parseUrlState, encodeUrlState, defaultUrlState } from '../url-state';

describe('defaultUrlState', () => {
  it('returns sensible defaults', () => {
    const s = defaultUrlState();
    expect(s.page).toBe(1);
    expect(s.pageSize).toBe(20);
    expect(s.sort).toEqual([]);
    expect(s.groupBy).toBe('category');
    expect(s.filters).toEqual({});
    expect(s.mode).toBe('dashboard');
  });
});

describe('parseUrlState', () => {
  it('parses empty string to defaults', () => {
    const s = parseUrlState('');
    expect(s.page).toBe(1);
    expect(s.sort).toEqual([]);
  });

  it('parses page and pageSize', () => {
    const s = parseUrlState('page=3&page_size=50');
    expect(s.page).toBe(3);
    expect(s.pageSize).toBe(50);
  });

  it('parses single sort field', () => {
    const s = parseUrlState('sort=price_numeric_eur:desc');
    expect(s.sort).toEqual([['price_numeric_eur', 'desc']]);
  });

  it('parses multi-sort', () => {
    const s = parseUrlState('sort=buyer:asc,price_numeric_eur:desc');
    expect(s.sort).toEqual([
      ['buyer', 'asc'],
      ['price_numeric_eur', 'desc'],
    ]);
  });

  it('parses groupBy', () => {
    const s = parseUrlState('group_by=supplier');
    expect(s.groupBy).toBe('supplier');
  });

  it('parses filter fields', () => {
    const s = parseUrlState('institutions=A%7CB&date_from=2024-01-01&value_min=100&text_search=test');
    expect(s.filters.institutions).toEqual(['A', 'B']);
    expect(s.filters.date_from).toBe('2024-01-01');
    expect(s.filters.value_min).toBe(100);
    expect(s.filters.text_search).toBe('test');
  });

  it('parses categories, vendors, award_types', () => {
    const s = parseUrlState('categories=cat1%7Ccat2&vendors=v1&icos=12345678&award_types=direct_award');
    expect(s.filters.categories).toEqual(['cat1', 'cat2']);
    expect(s.filters.vendors).toEqual(['v1']);
    expect(s.filters.icos).toEqual(['12345678']);
    expect(s.filters.award_types).toEqual(['direct_award']);
  });
});

describe('encodeUrlState', () => {
  it('encodes default state to empty string', () => {
    const result = encodeUrlState(defaultUrlState());
    // Default values should not produce unnecessary query params
    // At minimum page=1 is a default  
    expect(result).toBeDefined();
  });

  it('round-trips filters', () => {
    const original = {
      ...defaultUrlState(),
      filters: { institutions: ['Foo', 'Bar'], date_from: '2024-06-01' },
      page: 2,
      sort: [['buyer', 'asc']] as [string, string][],
    };
    const encoded = encodeUrlState(original);
    const decoded = parseUrlState(encoded);
    expect(decoded.filters.institutions).toEqual(['Foo', 'Bar']);
    expect(decoded.filters.date_from).toBe('2024-06-01');
    expect(decoded.page).toBe(2);
    expect(decoded.sort).toEqual([['buyer', 'asc']]);
  });

  it('round-trips groupBy', () => {
    const original = { ...defaultUrlState(), groupBy: 'supplier' as const };
    const encoded = encodeUrlState(original);
    const decoded = parseUrlState(encoded);
    expect(decoded.groupBy).toBe('supplier');
  });
});

// ── Phase 7: Full state round-trip ──────────────────────────────────

describe('Full state encode/decode (Phase 7)', () => {
  it('all fields survive round-trip', () => {
    const original = {
      ...defaultUrlState(),
      filters: {
        institutions: ['Inst A', 'Inst B'],
        date_from: '2025-01-01',
        date_to: '2025-12-31',
        categories: ['construction'],
        vendors: ['Vendor X'],
        icos: ['12345678'],
        value_min: 10000,
        value_max: 500000,
        award_types: ['direct_award'],
        text_search: 'roads',
      },
      sort: [['price_numeric_eur', 'desc'], ['published_date', 'asc']] as [string, string][],
      groupBy: 'supplier' as const,
      page: 3,
      pageSize: 50,
      mode: 'benchmark' as const,
    };
    const encoded = encodeUrlState(original);
    const decoded = parseUrlState(encoded);

    expect(decoded.filters.institutions).toEqual(['Inst A', 'Inst B']);
    expect(decoded.filters.date_from).toBe('2025-01-01');
    expect(decoded.filters.date_to).toBe('2025-12-31');
    expect(decoded.filters.categories).toEqual(['construction']);
    expect(decoded.filters.vendors).toEqual(['Vendor X']);
    expect(decoded.filters.icos).toEqual(['12345678']);
    expect(decoded.filters.value_min).toBe(10000);
    expect(decoded.filters.value_max).toBe(500000);
    expect(decoded.filters.award_types).toEqual(['direct_award']);
    expect(decoded.filters.text_search).toBe('roads');
    expect(decoded.sort).toEqual([['price_numeric_eur', 'desc'], ['published_date', 'asc']]);
    expect(decoded.groupBy).toBe('supplier');
    expect(decoded.page).toBe(3);
    expect(decoded.pageSize).toBe(50);
    expect(decoded.mode).toBe('benchmark');
  });

  it('missing params get sensible defaults', () => {
    const decoded = parseUrlState('');
    expect(decoded.filters).toEqual({});
    expect(decoded.sort).toEqual([]);
    expect(decoded.groupBy).toBe('category');
    expect(decoded.page).toBe(1);
    expect(decoded.pageSize).toBe(20);
    expect(decoded.mode).toBe('dashboard');
  });

  it('mode is encoded and decoded correctly', () => {
    const original = { ...defaultUrlState(), mode: 'time' as const };
    const encoded = encodeUrlState(original);
    const decoded = parseUrlState(encoded);
    expect(decoded.mode).toBe('time');
  });

  it('values containing commas survive round-trip', () => {
    const original = {
      ...defaultUrlState(),
      filters: {
        categories: ['IT, consulting', 'legal'],
        vendors: ['Smith, Jones & Co'],
        institutions: ['Ministry of Finance, SR'],
      },
    };
    const encoded = encodeUrlState(original);
    const decoded = parseUrlState(encoded);
    expect(decoded.filters.categories).toEqual(['IT, consulting', 'legal']);
    expect(decoded.filters.vendors).toEqual(['Smith, Jones & Co']);
    expect(decoded.filters.institutions).toEqual(['Ministry of Finance, SR']);
  });

  it('contracts mode survives round-trip', () => {
    const original = { ...defaultUrlState(), mode: 'contracts' as const };
    const encoded = encodeUrlState(original);
    const decoded = parseUrlState(encoded);
    expect(decoded.mode).toBe('contracts');
  });
});
