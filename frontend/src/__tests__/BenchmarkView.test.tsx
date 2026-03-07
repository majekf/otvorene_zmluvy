/**
 * Tests for BenchmarkView page (Phase 6)
 *
 * Covers: page rendering, institution selection, peer suggestions,
 * comparison chart loading, min-contract filter, FilterBar integration,
 * and global filter state persistence via FilterContext.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import BenchmarkView from '../pages/BenchmarkView';
import { FilterProvider } from '../FilterContext';
import * as api from '../api';

vi.mock('../api');

const mockInstitutions = {
  institutions: [
    { name: 'Mesto Bratislava', ico: '001', contract_count: 10, total_spend: 1000000 },
    { name: 'Mesto Košice', ico: '002', contract_count: 5, total_spend: 500000 },
    { name: 'Ministry XY', ico: '003', contract_count: 1, total_spend: 100000 },
  ],
};

const mockPeers = {
  institution: 'Mesto Bratislava',
  min_contracts: 1,
  peers: ['Mesto Košice', 'Ministry XY'],
};

const mockMultiMetric = {
  metrics: ['total_spend', 'contract_count', 'direct_award_rate'],
  results: [
    { institution: 'Mesto Bratislava', total_spend: 1000000, contract_count: 10, direct_award_rate: 0.3 },
    { institution: 'Mesto Košice', total_spend: 500000, contract_count: 5, direct_award_rate: 0.6 },
  ],
};

const emptyAggregations = {
  group_by: '',
  results: [],
  summary: { contract_count: 0, total_spend: 0, avg_value: 0, max_value: 0 },
};

function renderPage(route = '/benchmark') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <FilterProvider>
        <Routes>
          <Route path="/benchmark" element={<BenchmarkView />} />
        </Routes>
      </FilterProvider>
    </MemoryRouter>,
  );
}

describe('BenchmarkView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchInstitutions).mockResolvedValue(mockInstitutions);
    vi.mocked(api.fetchBenchmarkPeers).mockResolvedValue(mockPeers);
    vi.mocked(api.fetchBenchmarkMultiMetric).mockResolvedValue(mockMultiMetric);
    // FilterProvider calls fetchAggregations to populate dropdown option lists
    vi.mocked(api.fetchAggregations).mockResolvedValue(emptyAggregations);
  });

  it('renders page and institutions', async () => {
    renderPage();
    expect(screen.getByTestId('benchmark-view')).toBeInTheDocument();
    expect(screen.getByText('Benchmark Comparison')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/Mesto Bratislava/)).toBeInTheDocument();
    });
  });

  it('shows institution buttons with contract count', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Mesto Bratislava (10)')).toBeInTheDocument();
      expect(screen.getByText('Mesto Košice (5)')).toBeInTheDocument();
    });
  });

  it('peer suggestions appear after selecting one institution', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Mesto Bratislava (10)')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Mesto Bratislava (10)'));
    await waitFor(() => {
      expect(screen.getByTestId('peer-suggestions')).toBeInTheDocument();
    });
  });

  it('fetches comparison data after selecting two institutions', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Mesto Bratislava (10)')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Mesto Bratislava (10)'));
    fireEvent.click(screen.getByText('Mesto Košice (5)'));
    await waitFor(() => {
      expect(api.fetchBenchmarkMultiMetric).toHaveBeenCalled();
    });
  });

  it('renders comparison charts when data is loaded', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Mesto Bratislava (10)')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText('Mesto Bratislava (10)'));
    fireEvent.click(screen.getByText('Mesto Košice (5)'));
    await waitFor(() => {
      expect(screen.getByTestId('benchmark-charts')).toBeInTheDocument();
    });
  });

  it('min contracts filter works', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('min-contracts')).toBeInTheDocument();
    });
    const input = screen.getByTestId('min-contracts');
    fireEvent.change(input, { target: { value: '10' } });
    // After setting min to 10, only Bratislava should show
    await waitFor(() => {
      expect(screen.queryByText('Mesto Košice (5)')).not.toBeInTheDocument();
    });
  });

  // ── FilterBar integration tests ────────────────────────────────────

  it('renders the shared FilterBar', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('filter-bar')).toBeInTheDocument();
    });
  });

  it('FilterBar date filter is present and interactive', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('filter-date-from')).toBeInTheDocument();
      expect(screen.getByTestId('filter-date-to')).toBeInTheDocument();
    });
    fireEvent.change(screen.getByTestId('filter-date-from'), { target: { value: '2025-01-01' } });
    // The filter bar should reflect the value
    expect((screen.getByTestId('filter-date-from') as HTMLInputElement).value).toBe('2025-01-01');
  });

  it('FilterBar category selector is present', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('filter-category')).toBeInTheDocument();
    });
  });

  it('FilterBar award type selector is present', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('filter-award-type')).toBeInTheDocument();
    });
  });

  it('FilterBar reset clears all filters', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('filter-bar')).toBeInTheDocument();
    });
    // Set a date filter first
    fireEvent.change(screen.getByTestId('filter-date-from'), { target: { value: '2025-06-01' } });
    expect((screen.getByTestId('filter-date-from') as HTMLInputElement).value).toBe('2025-06-01');
    // Reset all
    fireEvent.click(screen.getByTestId('filter-reset'));
    await waitFor(() => {
      expect((screen.getByTestId('filter-date-from') as HTMLInputElement).value).toBe('');
    });
  });

  it('passes filters to fetchBenchmarkMultiMetric', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('filter-date-from')).toBeInTheDocument();
      expect(screen.getByText('Mesto Bratislava (10)')).toBeInTheDocument();
    });

    // Set a date filter
    fireEvent.change(screen.getByTestId('filter-date-from'), { target: { value: '2025-01-01' } });

    // Select two institutions to trigger comparison
    fireEvent.click(screen.getByText('Mesto Bratislava (10)'));
    fireEvent.click(screen.getByText('Mesto Košice (5)'));

    await waitFor(() => {
      expect(api.fetchBenchmarkMultiMetric).toHaveBeenCalled();
      const calls = vi.mocked(api.fetchBenchmarkMultiMetric).mock.calls;
      const lastCall = calls[calls.length - 1];
      // Third argument is the filters object
      expect(lastCall[2]).toEqual(expect.objectContaining({ date_from: '2025-01-01' }));
    });
  });

  it('passes filters to fetchBenchmarkPeers', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('filter-date-from')).toBeInTheDocument();
      expect(screen.getByText('Mesto Bratislava (10)')).toBeInTheDocument();
    });

    // Set a date filter
    fireEvent.change(screen.getByTestId('filter-date-from'), { target: { value: '2025-06-01' } });

    // Select one institution to trigger peer lookup
    fireEvent.click(screen.getByText('Mesto Bratislava (10)'));

    await waitFor(() => {
      expect(api.fetchBenchmarkPeers).toHaveBeenCalled();
      const calls = vi.mocked(api.fetchBenchmarkPeers).mock.calls;
      const lastCall = calls[calls.length - 1];
      // Third argument is the filters object
      expect(lastCall[2]).toEqual(expect.objectContaining({ date_from: '2025-06-01' }));
    });
  });

  it('re-fetches institutions with filters when FilterBar changes', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Mesto Bratislava (10)')).toBeInTheDocument();
    });

    vi.mocked(api.fetchInstitutions).mockClear();

    // Change a filter — should trigger a new fetchInstitutions call with filters
    fireEvent.change(screen.getByTestId('filter-date-from'), { target: { value: '2026-01-01' } });

    await waitFor(() => {
      expect(api.fetchInstitutions).toHaveBeenCalled();
      const calls = vi.mocked(api.fetchInstitutions).mock.calls;
      const lastCall = calls[calls.length - 1];
      expect(lastCall[0]).toEqual(expect.objectContaining({ date_from: '2026-01-01' }));
    });
  });

  it('hides institutions not matching active filters', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Mesto Bratislava (10)')).toBeInTheDocument();
      expect(screen.getByText('Mesto Košice (5)')).toBeInTheDocument();
    });

    // Simulate a filter narrowing the institution set to just Bratislava
    const filteredInstitutions = {
      institutions: [
        { name: 'Mesto Bratislava', ico: '001', contract_count: 3, total_spend: 500000 },
      ],
    };
    vi.mocked(api.fetchInstitutions).mockResolvedValue(filteredInstitutions);

    fireEvent.change(screen.getByTestId('filter-date-from'), { target: { value: '2025-12-01' } });

    await waitFor(() => {
      expect(screen.getByText('Mesto Bratislava (3)')).toBeInTheDocument();
      expect(screen.queryByText('Mesto Košice (5)')).not.toBeInTheDocument();
    });
  });
});
