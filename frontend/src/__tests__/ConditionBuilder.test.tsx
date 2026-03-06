/**
 * Tests for ConditionBuilder component (Phase 4)
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ConditionBuilder from '../components/ConditionBuilder';

// Mock the API module
vi.mock('../api', () => ({
  evaluateCustomConditions: vi.fn(),
}));

import { evaluateCustomConditions } from '../api';

describe('ConditionBuilder', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (evaluateCustomConditions as ReturnType<typeof vi.fn>).mockResolvedValue({
      total_matched: 3,
      total_evaluated: 10,
      contracts: [],
    });
  });

  it('renders the builder', () => {
    render(
      <MemoryRouter>
        <ConditionBuilder filters={{}} />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('condition-builder')).toBeInTheDocument();
  });

  it('has at least one condition row by default', () => {
    render(
      <MemoryRouter>
        <ConditionBuilder filters={{}} />
      </MemoryRouter>,
    );
    expect(screen.getAllByTestId('condition-row')).toHaveLength(1);
  });

  it('can add condition rows', () => {
    render(
      <MemoryRouter>
        <ConditionBuilder filters={{}} />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByTestId('add-condition'));
    expect(screen.getAllByTestId('condition-row')).toHaveLength(2);
  });

  it('can remove condition rows', () => {
    render(
      <MemoryRouter>
        <ConditionBuilder filters={{}} />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByTestId('add-condition'));
    expect(screen.getAllByTestId('condition-row')).toHaveLength(2);

    const removeButtons = screen.getAllByTestId('condition-remove');
    fireEvent.click(removeButtons[0]);
    expect(screen.getAllByTestId('condition-row')).toHaveLength(1);
  });

  it('toggles logic between AND and OR', () => {
    render(
      <MemoryRouter>
        <ConditionBuilder filters={{}} />
      </MemoryRouter>,
    );
    const toggle = screen.getByTestId('logic-toggle');
    expect(toggle.textContent).toBe('AND');
    fireEvent.click(toggle);
    expect(toggle.textContent).toBe('OR');
    fireEvent.click(toggle);
    expect(toggle.textContent).toBe('AND');
  });

  it('calls API on evaluate', async () => {
    render(
      <MemoryRouter>
        <ConditionBuilder filters={{}} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByTestId('custom-evaluate-btn'));

    await waitFor(() => {
      expect(evaluateCustomConditions).toHaveBeenCalled();
    });
  });

  it('shows results after evaluation', async () => {
    render(
      <MemoryRouter>
        <ConditionBuilder filters={{}} />
      </MemoryRouter>,
    );

    fireEvent.click(screen.getByTestId('custom-evaluate-btn'));

    await waitFor(() => {
      expect(screen.getByTestId('custom-results')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
    });
  });

  it('serializes output correctly', async () => {
    const onResult = vi.fn();
    render(
      <MemoryRouter>
        <ConditionBuilder filters={{}} onResult={onResult} />
      </MemoryRouter>,
    );

    // Change field to buyer
    const fieldSelects = screen.getAllByTestId('condition-field');
    fireEvent.change(fieldSelects[0], { target: { value: 'buyer' } });

    // Change operator to contains
    const opSelects = screen.getAllByTestId('condition-operator');
    fireEvent.change(opSelects[0], { target: { value: 'contains' } });

    // Set value
    const valueInputs = screen.getAllByTestId('condition-value');
    fireEvent.change(valueInputs[0], { target: { value: 'Mesto' } });

    fireEvent.click(screen.getByTestId('custom-evaluate-btn'));

    await waitFor(() => {
      expect(evaluateCustomConditions).toHaveBeenCalledWith(
        expect.objectContaining({
          logic: 'AND',
          conditions: [
            { field: 'buyer', operator: 'contains', value: 'Mesto' },
          ],
        }),
        {},
      );
    });
  });
});
