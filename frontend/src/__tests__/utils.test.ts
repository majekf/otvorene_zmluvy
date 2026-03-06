/**
 * Tests for utils.ts: formatEur, formatCompact, formatDate
 */
import { describe, it, expect } from 'vitest';
import { formatEur, formatCompact, formatDate } from '../utils';

describe('formatEur', () => {
  it('formats a number as EUR', () => {
    const result = formatEur(12345.67);
    // Slovak locale with maximumFractionDigits:0 rounds to 12 346
    expect(result).toContain('12');
    expect(result).toContain('346');
  });

  it('returns dash for null', () => {
    expect(formatEur(null)).toBe('—');
  });

  it('returns dash for undefined', () => {
    expect(formatEur(undefined)).toBe('—');
  });
});

describe('formatCompact', () => {
  it('formats large numbers compactly', () => {
    const result = formatCompact(1500000);
    expect(result).toBe('1.5M €');
  });

  it('formats thousands', () => {
    const result = formatCompact(5000);
    expect(result).toBe('5k €');
  });

  it('formats small numbers', () => {
    expect(formatCompact(42)).toBe('42 €');
  });
});

describe('formatDate', () => {
  it('formats ISO date string', () => {
    const result = formatDate('2024-03-15');
    // Should contain year, should not be the raw ISO string
    expect(result).toContain('2024');
  });

  it('returns dash for null', () => {
    expect(formatDate(null)).toBe('—');
  });

  it('returns dash for empty string', () => {
    expect(formatDate('')).toBe('—');
  });
});
