/**
 * Tests for RedFlagsView page
 *
 * Covers: rendering, filter bar integration, RulePanel and ConditionBuilder
 * panels, loading states, dataset management, and absence of dashboard-specific elements.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import RedFlagsView from '../pages/RedFlagsView';
import { FilterProvider } from '../FilterContext';
import { RedFlagProvider } from '../RedFlagStore';
import * as api from '../api';
import type { RulePreset } from '../types';

vi.mock('../api');

const mockPresets: { presets: RulePreset[] } = {
  presets: [
    {
      id: 'threshold_proximity',
      name: 'Threshold Proximity',
      description: 'Flags contracts near a threshold.',
      params: { threshold_eur: 100000, proximity_pct: 10 } as Record<string, number>,
    },
    {
      id: 'vendor_concentration',
      name: 'Vendor Concentration',
      description: 'Top vendors holding too much spend.',
      params: { top_n: 1, max_share_pct: 60 } as Record<string, number>,
    },
  ],
};

function renderPage(route = '/red-flags') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <FilterProvider>
        <RedFlagProvider>
          <Routes>
            <Route path="/red-flags" element={<RedFlagsView />} />
          </Routes>
        </RedFlagProvider>
      </FilterProvider>
    </MemoryRouter>,
  );
}

describe('RedFlagsView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchRulePresets).mockResolvedValue(mockPresets);
    vi.mocked(api.fetchAggregations).mockResolvedValue({
      group_by: '',
      results: [],
      summary: { contract_count: 0, total_spend: 0, avg_value: 0, max_value: 0 },
    });
    vi.mocked(api.fetchInstitutions).mockResolvedValue({ institutions: [] });
    vi.mocked(api.fetchVendors).mockResolvedValue({ vendors: [] });
    vi.mocked(api.fetchFilterOptions).mockResolvedValue({
      institutions: [], categories: [], vendors: [],
      institution_icos: [], vendor_icos: [],
      scanned_service_types: [], scanned_service_subtypes: [],
    });
  });

  // ── Rendering ─────────────────────────────────────────────────────

  it('renders the page container', () => {
    renderPage();
    expect(screen.getByTestId('red-flags-view')).toBeInTheDocument();
  });

  it('renders the filter bar', () => {
    renderPage();
    expect(screen.getByTestId('filter-bar')).toBeInTheDocument();
  });

  it('renders the rule panel', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('rule-panel')).toBeInTheDocument();
    });
  });

  it('renders the condition builder', () => {
    renderPage();
    expect(screen.getByTestId('condition-builder')).toBeInTheDocument();
  });

  // ── Dataset management ────────────────────────────────────────────

  it('renders dataset manager section', () => {
    renderPage();
    expect(screen.getByTestId('dataset-manager')).toBeInTheDocument();
  });

  it('shows empty state when no datasets loaded', () => {
    renderPage();
    expect(screen.getByText(/No datasets loaded/i)).toBeInTheDocument();
  });

  it('renders upload dataset button', () => {
    renderPage();
    expect(screen.getByTestId('upload-dataset-btn')).toBeInTheDocument();
  });

  // ── Panels always visible (no toggle) ─────────────────────────────

  it('does NOT have a toggle-rules button', () => {
    renderPage();
    expect(screen.queryByTestId('toggle-rules')).not.toBeInTheDocument();
  });

  it('rule panel and condition builder are immediately visible without toggling', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('rule-panel')).toBeInTheDocument();
    });
    expect(screen.getByTestId('condition-builder')).toBeInTheDocument();
  });

  // ── Absent dashboard-specific elements ────────────────────────────

  it('does NOT render summary strip', () => {
    renderPage();
    expect(screen.queryByTestId('summary-strip')).not.toBeInTheDocument();
  });

  it('does NOT render treemap or bar chart', () => {
    renderPage();
    expect(screen.queryByTestId('treemap-chart')).not.toBeInTheDocument();
    expect(screen.queryByTestId('bar-chart')).not.toBeInTheDocument();
  });

  // ── Rule presets loaded ───────────────────────────────────────────

  it('loads rule presets on mount', async () => {
    renderPage();
    await waitFor(() => {
      expect(api.fetchRulePresets).toHaveBeenCalledTimes(1);
    });
  });

  it('displays preset rule names after loading', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Threshold Proximity')).toBeInTheDocument();
      expect(screen.getByText('Vendor Concentration')).toBeInTheDocument();
    });
  });

  // ── Severity selectors ────────────────────────────────────────────

  it('displays severity selectors for each preset rule', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('severity-select-threshold_proximity')).toBeInTheDocument();
      expect(screen.getByTestId('severity-select-vendor_concentration')).toBeInTheDocument();
    });
  });

  it('severity selector defaults to moderate', async () => {
    renderPage();
    await waitFor(() => {
      const select = screen.getByTestId('severity-select-threshold_proximity') as HTMLSelectElement;
      expect(select.value).toBe('moderate');
    });
  });

  // ── Dataset name input ────────────────────────────────────────────

  it('displays dataset name input', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('dataset-name-input')).toBeInTheDocument();
    });
  });

  // ── Condition builder elements ────────────────────────────────────

  it('renders add-condition button', () => {
    renderPage();
    expect(screen.getByTestId('add-condition')).toBeInTheDocument();
  });

  it('renders custom evaluate button', () => {
    renderPage();
    expect(screen.getByTestId('custom-evaluate-btn')).toBeInTheDocument();
  });
});
