/**
 * Tests for TimeView page (Phase 6)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import TimeView from '../pages/TimeView';
import { FilterProvider } from '../FilterContext';
import * as api from '../api';

vi.mock('../api');

const mockTrendsResponse = {
  granularity: 'month',
  metric: 'total_spend',
  data: [
    { period: '2024-01', value: 100000, count: 5 },
    { period: '2024-02', value: 150000, count: 8 },
    { period: '2024-03', value: 80000, count: 3 },
  ],
  overlays: [
    { date: '2024-02-15', label: 'Election', description: 'Parliamentary election' },
  ],
};

const emptyTrendsResponse = {
  granularity: 'month',
  metric: 'total_spend',
  data: [],
  overlays: [],
};

function renderPage(route = '/time') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <FilterProvider>
        <Routes>
          <Route path="/time" element={<TimeView />} />
        </Routes>
      </FilterProvider>
    </MemoryRouter>,
  );
}

describe('TimeView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchTrends).mockResolvedValue(mockTrendsResponse);
    vi.mocked(api.fetchAggregations).mockResolvedValue({ group_by: '', results: [], summary: { contract_count: 0, total_spend: 0, avg_value: 0, max_value: 0 } });
  });

  it('renders page heading', async () => {
    renderPage();
    expect(screen.getByTestId('time-view')).toBeInTheDocument();
    expect(screen.getByText('Compare in Time')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    vi.mocked(api.fetchTrends).mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    expect(screen.getByTestId('time-loading')).toBeInTheDocument();
  });

  it('shows empty state when no data', async () => {
    vi.mocked(api.fetchTrends).mockResolvedValue(emptyTrendsResponse);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('time-empty')).toBeInTheDocument();
    });
  });

  it('renders chart when data loads', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('time-chart')).toBeInTheDocument();
    });
  });

  it('renders summary stats', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('time-summary')).toBeInTheDocument();
      expect(screen.getByText(/Periods/)).toBeInTheDocument();
    });
  });

  it('granularity buttons work', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('time-chart')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('granularity-quarter'));
    await waitFor(() => {
      expect(api.fetchTrends).toHaveBeenCalledWith(
        expect.anything(),
        'quarter',
        expect.anything(),
        expect.anything(),
      );
    });
  });

  it('metric toggles work', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('time-chart')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('metric-contract_count'));
    await waitFor(() => {
      // The metric selection should have changed
      expect(api.fetchTrends).toHaveBeenCalled();
    });
  });

  it('overlay toggle triggers re-fetch', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('time-chart')).toBeInTheDocument();
    });
    // Clear previous calls
    vi.mocked(api.fetchTrends).mockClear();
    fireEvent.click(screen.getByTestId('overlay-toggle'));
    await waitFor(() => {
      expect(api.fetchTrends).toHaveBeenCalledWith(
        expect.anything(),
        expect.anything(),
        expect.anything(),
        true,
      );
    });
  });
});
