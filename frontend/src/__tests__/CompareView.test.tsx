/**
 * Tests for CompareView page (Phase 9)
 *
 * Covers: page rendering, data loading, metric switching,
 * no-subcontractors warning, and FilterBar integration.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CompareView from '../pages/CompareView';
import { FilterProvider } from '../FilterContext';
import * as api from '../api';

vi.mock('../api');

const mockCompareData = {
  group_by: 'category',
  data: [
    {
      group_value: 'construction',
      contracts_total_spend: 1200000,
      contracts_contract_count: 5,
      contracts_avg_value: 240000,
      subcontractors_total_spend: 600000,
      subcontractors_contract_count: 3,
      subcontractors_avg_value: 200000,
    },
    {
      group_value: 'IT',
      contracts_total_spend: 500000,
      contracts_contract_count: 3,
      contracts_avg_value: 166667,
      subcontractors_total_spend: 300000,
      subcontractors_contract_count: 2,
      subcontractors_avg_value: 150000,
    },
  ],
  contracts_summary: { total_spend: 1700000, contract_count: 8, avg_value: 212500, max_value: 500000 },
  subcontractors_summary: { total_spend: 900000, contract_count: 5, avg_value: 180000, max_value: 350000 },
  has_subcontractors: true,
};

const mockCompareNoSub = {
  ...mockCompareData,
  subcontractors_summary: { total_spend: 0, contract_count: 0, avg_value: 0, max_value: 0 },
  has_subcontractors: false,
  data: mockCompareData.data.map((d) => ({
    ...d,
    subcontractors_total_spend: 0,
    subcontractors_contract_count: 0,
    subcontractors_avg_value: 0,
  })),
};

const emptyAggregations = {
  group_by: '',
  results: [],
  summary: { contract_count: 0, total_spend: 0, avg_value: 0, max_value: 0 },
};

const mockInstitutions = {
  institutions: [
    { name: 'Mesto Bratislava', ico: '001', contract_count: 10, total_spend: 1000000 },
  ],
};

function renderPage(route = '/compare') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <FilterProvider>
        <Routes>
          <Route path="/compare" element={<CompareView />} />
        </Routes>
      </FilterProvider>
    </MemoryRouter>,
  );
}

describe('CompareView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchCompareAggregations).mockResolvedValue(mockCompareData);
    vi.mocked(api.fetchAggregations).mockResolvedValue(emptyAggregations);
    vi.mocked(api.fetchInstitutions).mockResolvedValue(mockInstitutions);
    vi.mocked(api.fetchVendors).mockResolvedValue({ vendors: [] });
  });

  it('renders the page title', async () => {
    renderPage();
    expect(screen.getByTestId('compare-view')).toBeInTheDocument();
    expect(screen.getByText('Contracts vs Subcontractors')).toBeInTheDocument();
  });

  it('loads and displays comparison data', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('compare-summary')).toBeInTheDocument();
    });
    expect(screen.getByTestId('compare-chart-container')).toBeInTheDocument();
  });

  it('shows summary cards with correct labels', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Contracts')).toBeInTheDocument();
      expect(screen.getByText('Subcontractors')).toBeInTheDocument();
    });
  });

  it('switches metric when button clicked', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('compare-chart-container')).toBeInTheDocument();
    });
    const countBtn = screen.getByTestId('metric-btn-contract_count');
    fireEvent.click(countBtn);
    // Button should now be active
    expect(countBtn.className).toContain('bg-primary-600');
  });

  it('shows warning when subcontractors not loaded', async () => {
    vi.mocked(api.fetchCompareAggregations).mockResolvedValue(mockCompareNoSub);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText(/Subcontractors data is not loaded/)).toBeInTheDocument();
    });
  });

  it('calls fetchCompareAggregations on mount', async () => {
    renderPage();
    await waitFor(() => {
      expect(api.fetchCompareAggregations).toHaveBeenCalledTimes(1);
    });
  });
});
