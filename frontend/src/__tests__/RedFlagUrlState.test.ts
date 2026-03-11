/**
 * Tests for Red Flag URL state round-trip
 *
 * Covers: parsing and encoding of red flag filter fields in URL state.
 */
import { describe, it, expect } from 'vitest';
import { parseUrlState, encodeUrlState, defaultUrlState } from '../url-state';

describe('URL State - Red Flag Filters', () => {
  it('parses red_flag_datasets from URL', () => {
    const state = parseUrlState('red_flag_datasets=Dataset+1|Dataset+2');
    expect(state.filters.red_flag_datasets).toEqual(['Dataset 1', 'Dataset 2']);
  });

  it('parses red_flag_types from URL', () => {
    const state = parseUrlState('red_flag_types=threshold_proximity|vendor_concentration');
    expect(state.filters.red_flag_types).toEqual(['threshold_proximity', 'vendor_concentration']);
  });

  it('parses institution_flag_count_min from URL', () => {
    const state = parseUrlState('institution_flag_count_min=5');
    expect(state.filters.institution_flag_count_min).toBe(5);
  });

  it('parses institution_flag_count_max from URL', () => {
    const state = parseUrlState('institution_flag_count_max=10');
    expect(state.filters.institution_flag_count_max).toBe(10);
  });

  it('parses vendor_flag_count_min from URL', () => {
    const state = parseUrlState('vendor_flag_count_min=2');
    expect(state.filters.vendor_flag_count_min).toBe(2);
  });

  it('parses vendor_flag_count_max from URL', () => {
    const state = parseUrlState('vendor_flag_count_max=20');
    expect(state.filters.vendor_flag_count_max).toBe(20);
  });

  it('encodes red_flag_datasets in URL', () => {
    const state = {
      ...defaultUrlState(),
      filters: { red_flag_datasets: ['Dataset 1', 'Dataset 2'] },
    };
    const encoded = encodeUrlState(state);
    expect(encoded).toContain('red_flag_datasets=');
    const parsed = parseUrlState(encoded);
    expect(parsed.filters.red_flag_datasets).toEqual(['Dataset 1', 'Dataset 2']);
  });

  it('encodes red_flag_types in URL', () => {
    const state = {
      ...defaultUrlState(),
      filters: { red_flag_types: ['threshold_proximity'] },
    };
    const encoded = encodeUrlState(state);
    expect(encoded).toContain('red_flag_types=threshold_proximity');
  });

  it('encodes institution_flag_count_min in URL', () => {
    const state = {
      ...defaultUrlState(),
      filters: { institution_flag_count_min: 3 },
    };
    const encoded = encodeUrlState(state);
    expect(encoded).toContain('institution_flag_count_min=3');
  });

  it('encodes vendor_flag_count_max in URL', () => {
    const state = {
      ...defaultUrlState(),
      filters: { vendor_flag_count_max: 15 },
    };
    const encoded = encodeUrlState(state);
    expect(encoded).toContain('vendor_flag_count_max=15');
  });

  it('round-trips all red flag filter fields', () => {
    const state = {
      ...defaultUrlState(),
      filters: {
        red_flag_datasets: ['DS 1', 'DS 2'],
        red_flag_types: ['type_a', 'type_b'],
        institution_flag_count_min: 1,
        institution_flag_count_max: 50,
        vendor_flag_count_min: 0,
        vendor_flag_count_max: 100,
      },
    };
    const encoded = encodeUrlState(state);
    const parsed = parseUrlState(encoded);
    expect(parsed.filters.red_flag_datasets).toEqual(['DS 1', 'DS 2']);
    expect(parsed.filters.red_flag_types).toEqual(['type_a', 'type_b']);
    expect(parsed.filters.institution_flag_count_min).toBe(1);
    expect(parsed.filters.institution_flag_count_max).toBe(50);
    expect(parsed.filters.vendor_flag_count_min).toBe(0);
    expect(parsed.filters.vendor_flag_count_max).toBe(100);
  });

  it('omits red flag fields when not set', () => {
    const state = defaultUrlState();
    const encoded = encodeUrlState(state);
    expect(encoded).not.toContain('red_flag');
    expect(encoded).not.toContain('institution_flag_count');
    expect(encoded).not.toContain('vendor_flag_count');
  });
});
