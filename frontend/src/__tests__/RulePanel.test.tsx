/**
 * Tests for RulePanel component (Phase 4)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import RulePanel from '../components/RulePanel';

// Mock the API module
vi.mock('../api', () => ({
  fetchRulePresets: vi.fn(),
  evaluateRules: vi.fn(),
}));

import { fetchRulePresets, evaluateRules } from '../api';

const mockPresets = {
  presets: [
    {
      id: 'threshold_proximity',
      name: 'Threshold Proximity',
      description: 'Flags contracts near a threshold.',
      params: { threshold_eur: 100000, proximity_pct: 10 },
    },
    {
      id: 'vendor_concentration',
      name: 'Vendor Concentration',
      description: 'Top vendors holding too much spend.',
      params: { top_n: 1, max_share_pct: 60 },
    },
  ],
};

describe('RulePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (fetchRulePresets as ReturnType<typeof vi.fn>).mockResolvedValue(mockPresets);
    (evaluateRules as ReturnType<typeof vi.fn>).mockResolvedValue({
      total_flags: 1,
      contract_severities: { c1: 0.6 },
      flags: [
        {
          rule_id: 'threshold_proximity',
          rule_name: 'Threshold Proximity',
          severity: 0.6,
          description: 'Contract near threshold',
          contract_id: 'c1',
          vendor: 'Vendor X',
          institution: 'Inst A',
          details: {},
        },
      ],
    });
  });

  it('renders the rule panel', async () => {
    render(
      <MemoryRouter>
        <RulePanel filters={{}} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('rule-panel')).toBeInTheDocument();
    });
  });

  it('loads and displays presets', async () => {
    render(
      <MemoryRouter>
        <RulePanel filters={{}} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByText('Threshold Proximity')).toBeInTheDocument();
      expect(screen.getByText('Vendor Concentration')).toBeInTheDocument();
    });
  });

  it('slider changes update params', async () => {
    render(
      <MemoryRouter>
        <RulePanel filters={{}} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('param-threshold_proximity-threshold_eur')).toBeInTheDocument();
    });

    const slider = screen.getByTestId('param-threshold_proximity-threshold_eur') as HTMLInputElement;
    fireEvent.change(slider, { target: { value: '50000' } });
    expect(slider.value).toBe('50000');
  });

  it('evaluate button calls API', async () => {
    const onFlagsChange = vi.fn();
    render(
      <MemoryRouter>
        <RulePanel filters={{}} onFlagsChange={onFlagsChange} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('evaluate-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('evaluate-btn'));

    await waitFor(() => {
      expect(evaluateRules).toHaveBeenCalled();
      expect(onFlagsChange).toHaveBeenCalled();
    });
  });

  it('displays results after evaluation', async () => {
    render(
      <MemoryRouter>
        <RulePanel filters={{}} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('evaluate-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('evaluate-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('rule-results')).toBeInTheDocument();
      expect(screen.getByText(/1 flag found/)).toBeInTheDocument();
    });
  });

  it('toggling a rule checkbox works', async () => {
    render(
      <MemoryRouter>
        <RulePanel filters={{}} />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId('rule-toggle-threshold_proximity')).toBeInTheDocument();
    });

    const checkbox = screen.getByTestId('rule-toggle-threshold_proximity') as HTMLInputElement;
    expect(checkbox.checked).toBe(true);
    fireEvent.click(checkbox);
    expect(checkbox.checked).toBe(false);
  });
});
