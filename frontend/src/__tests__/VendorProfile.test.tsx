/**
 * Tests for VendorProfile page
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import VendorProfile from '../pages/VendorProfile';
import type { VendorProfile as VendorProfileType } from '../types';
import * as api from '../api';

vi.mock('../api');

const mockProfile: VendorProfileType = {
  name: 'Test Vendor',
  ico: '87654321',
  contract_count: 30,
  total_spend: 900000,
  avg_value: 30000,
  max_value: 150000,
  institutions_served: [
    { name: 'Ministry A', contract_count: 15, total_spend: 500000 },
    { name: 'Ministry B', contract_count: 8, total_spend: 200000 },
  ],
  trend: [
    { period: '2024-01', value: 80000, count: 3 },
    { period: '2024-02', value: 95000, count: 4 },
  ],
  contracts: [
    {
      contract_id: 'v1',
      contract_title: 'Vendor Contract One',
      contract_number: null,
      buyer: 'Ministry A',
      supplier: 'Test Vendor',
      price_numeric_eur: 40000,
      price_raw: null,
      published_date: '2024-02-10',
      category: 'Consulting',
      award_type: 'direct_award',
      pdf_text_summary: '',
      contract_url: null,
      ico_buyer: null,
      ico_supplier: null,
      date_published: null,
      date_concluded: null,
      date_effective: null,
      date_valid_until: null,
      pdf_url: null,
      pdf_text: null,
      scraped_at: null,
    },
  ],
};

function renderPage(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/vendor/${id}`]}>
      <Routes>
        <Route path="/vendor/:id" element={<VendorProfile />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('VendorProfile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state', () => {
    vi.mocked(api.fetchVendorProfile).mockReturnValue(new Promise(() => {}));
    renderPage('Test%20Vendor');
    expect(screen.getByTestId('vendor-loading')).toBeInTheDocument();
  });

  it('renders profile on success', async () => {
    vi.mocked(api.fetchVendorProfile).mockResolvedValue(mockProfile);
    renderPage('Test%20Vendor');

    await waitFor(() => {
      expect(screen.getByTestId('vendor-profile')).toBeInTheDocument();
    });

    expect(screen.getByText('Test Vendor')).toBeInTheDocument();
    expect(screen.getByText(/87654321/)).toBeInTheDocument();
    expect(screen.getByText('Revenue Trend')).toBeInTheDocument();
    expect(screen.getByText('Institutions Served')).toBeInTheDocument();
    expect(screen.getByText('Vendor Contract One')).toBeInTheDocument();
  });

  it('shows error state on failure', async () => {
    vi.mocked(api.fetchVendorProfile).mockRejectedValue(new Error('Not found'));
    renderPage('Test%20Vendor');

    await waitFor(() => {
      expect(screen.getByTestId('vendor-error')).toBeInTheDocument();
    });
    expect(screen.getByText(/Not found/)).toBeInTheDocument();
  });
});
