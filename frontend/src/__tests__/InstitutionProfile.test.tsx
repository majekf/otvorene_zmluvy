/**
 * Tests for InstitutionProfile page
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import InstitutionProfile from '../pages/InstitutionProfile';
import type { InstitutionProfile as InstitutionProfileType } from '../types';
import * as api from '../api';

vi.mock('../api');

const mockProfile: InstitutionProfileType = {
  name: 'Test Ministry',
  ico: '12345678',
  contract_count: 50,
  total_spend: 1500000,
  avg_value: 30000,
  max_value: 200000,
  top_vendors: [
    { name: 'Vendor A', contract_count: 20, total_spend: 800000 },
    { name: 'Vendor B', contract_count: 10, total_spend: 300000 },
  ],
  trend: [
    { period: '2024-01', value: 100000, count: 5 },
    { period: '2024-02', value: 120000, count: 6 },
  ],
  contracts: [
    {
      contract_id: 'c1',
      contract_title: 'Contract One',
      contract_number: null,
      buyer: 'Test Ministry',
      supplier: 'Vendor A',
      price_numeric_eur: 50000,
      price_raw: null,
      published_date: '2024-01-15',
      category: 'IT',
      award_type: 'open_tender',
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
    <MemoryRouter initialEntries={[`/institution/${id}`]}>
      <Routes>
        <Route path="/institution/:id" element={<InstitutionProfile />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('InstitutionProfile', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows loading state', () => {
    vi.mocked(api.fetchInstitutionProfile).mockReturnValue(new Promise(() => {}));
    renderPage('Test%20Ministry');
    expect(screen.getByTestId('institution-loading')).toBeInTheDocument();
  });

  it('renders profile on success', async () => {
    vi.mocked(api.fetchInstitutionProfile).mockResolvedValue(mockProfile);
    renderPage('Test%20Ministry');

    await waitFor(() => {
      expect(screen.getByTestId('institution-profile')).toBeInTheDocument();
    });

    expect(screen.getByText('Test Ministry')).toBeInTheDocument();
    expect(screen.getByText(/12345678/)).toBeInTheDocument();
    expect(screen.getByText('Spending Trend')).toBeInTheDocument();
    expect(screen.getByText('Top Vendors')).toBeInTheDocument();
    expect(screen.getByText('Contract One')).toBeInTheDocument();
  });

  it('shows error state on failure', async () => {
    vi.mocked(api.fetchInstitutionProfile).mockRejectedValue(new Error('Server error'));
    renderPage('Test%20Ministry');

    await waitFor(() => {
      expect(screen.getByTestId('institution-error')).toBeInTheDocument();
    });
    expect(screen.getByText(/Server error/)).toBeInTheDocument();
  });
});
