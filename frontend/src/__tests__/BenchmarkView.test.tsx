/**
 * Tests for BenchmarkView page (Phase 6)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import BenchmarkView from '../pages/BenchmarkView';
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

function renderPage(route = '/benchmark') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <Routes>
        <Route path="/benchmark" element={<BenchmarkView />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('BenchmarkView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.fetchInstitutions).mockResolvedValue(mockInstitutions);
    vi.mocked(api.fetchBenchmarkPeers).mockResolvedValue(mockPeers);
    vi.mocked(api.fetchBenchmarkMultiMetric).mockResolvedValue(mockMultiMetric);
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
});
