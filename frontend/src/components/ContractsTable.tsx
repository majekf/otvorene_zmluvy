/**
 * ContractsTable Component
 *
 * Multi-column sortable table. Click a header to sort; Shift+click to
 * add secondary/tertiary sort keys. Sort state is managed externally
 * so it can be encoded in the URL.
 */

import { useCallback } from 'react';
import { Link } from 'react-router-dom';
import type { Contract, SortSpec } from '../types';
import { formatEur, formatDate } from '../utils';
import SeverityIndicator from './SeverityIndicator';

interface ContractsTableProps {
  contracts: Contract[];
  sort: SortSpec;
  onSortChange: (sort: SortSpec) => void;
  onRowClick?: (contractId: string) => void;
  contractSeverities?: Record<string, number>;
  variant?: 'default' | 'all-contracts';
}

interface ColumnDef {
  key: string;
  label: string;
  sortable: boolean;
  render: (c: Contract) => React.ReactNode;
  className?: string;
}

const DEFAULT_COLUMNS: ColumnDef[] = [
  {
    key: 'contract_title',
    label: 'Title',
    sortable: true,
    className: 'max-w-[300px] truncate',
    render: (c) => (
      <Link
        to={`/contract/${c.contract_id}`}
        className="text-primary-600 hover:text-primary-800 font-medium transition-colors"
        title={c.contract_title || ''}
        onClick={(e) => e.stopPropagation()}
      >
        {c.contract_title || '—'}
      </Link>
    ),
  },
  {
    key: 'supplier',
    label: 'Vendor',
    sortable: true,
    render: (c) =>
      c.supplier ? (
        <Link
          to={`/vendor/${encodeURIComponent(c.supplier)}`}
          className="text-primary-600 hover:text-primary-800 transition-colors"
          onClick={(e) => e.stopPropagation()}
        >
          {c.supplier}
        </Link>
      ) : (
        '—'
      ),
  },
  {
    key: 'buyer',
    label: 'Institution',
    sortable: true,
    render: (c) =>
      c.buyer ? (
        <Link
          to={`/institution/${encodeURIComponent(c.buyer)}`}
          className="text-primary-600 hover:text-primary-800 transition-colors"
          onClick={(e) => e.stopPropagation()}
        >
          {c.buyer}
        </Link>
      ) : (
        '—'
      ),
  },
  {
    key: 'price_numeric_eur',
    label: 'Value',
    sortable: true,
    className: 'text-right',
    render: (c) => <span className="font-mono">{formatEur(c.price_numeric_eur)}</span>,
  },
  {
    key: 'published_date',
    label: 'Date',
    sortable: true,
    render: (c) => formatDate(c.published_date),
  },
  {
    key: 'award_type',
    label: 'Award',
    sortable: true,
    render: (c) => (
      <span
        className={`chip ${
          c.award_type === 'direct_award'
            ? 'chip-red'
            : c.award_type === 'open_tender'
              ? 'chip-green'
              : 'chip-gray'
        }`}
      >
        {c.award_type === 'direct_award' && <span className="badge-dot bg-red-500" />}
        {c.award_type === 'open_tender' && <span className="badge-dot bg-green-500" />}
        {c.award_type}
      </span>
    ),
  },
];

const ALL_CONTRACTS_COLUMNS: ColumnDef[] = [
  ...DEFAULT_COLUMNS.slice(0, 5),
  {
    key: 'scanned_suggested_title',
    label: 'Subject',
    sortable: true,
    className: 'max-w-[260px] truncate',
    render: (c) => c.scanned_suggested_title || 'â€”',
  },
  {
    key: 'scanned_service_type',
    label: 'Type',
    sortable: true,
    render: (c) => c.scanned_service_type || 'â€”',
  },
  {
    key: 'scanned_service_subtype',
    label: 'Subtype',
    sortable: true,
    render: (c) => c.scanned_service_subtype || 'â€”',
  },
];

function findSortIndex(sort: SortSpec, field: string): number {
  return sort.findIndex(([f]) => f === field);
}

function directionArrow(dir: string): string {
  return dir === 'desc' ? '↓' : '↑';
}

const PRIORITY_BADGES = ['①', '②', '③'];

export default function ContractsTable({ contracts, sort, onSortChange, onRowClick, contractSeverities, variant = 'default' }: ContractsTableProps) {
  const columns = variant === 'all-contracts' ? ALL_CONTRACTS_COLUMNS : DEFAULT_COLUMNS;

  const handleHeaderClick = useCallback(
    (field: string, e: React.MouseEvent | React.KeyboardEvent) => {
      const shiftKey = e.shiftKey;
      const idx = findSortIndex(sort, field);
      if (shiftKey) {
        // Shift+click: append or toggle direction for existing secondary key
        if (idx >= 0) {
          const newSort = [...sort];
          newSort[idx] = [field, sort[idx][1] === 'asc' ? 'desc' : 'asc'];
          onSortChange(newSort);
        } else {
          onSortChange([...sort, [field, 'asc']]);
        }
      } else {
        // Plain click: set as primary (toggle direction if already primary)
        if (idx === 0) {
          onSortChange([[field, sort[0][1] === 'asc' ? 'desc' : 'asc']]);
        } else {
          onSortChange([[field, 'asc']]);
        }
      }
    },
    [sort, onSortChange],
  );

  const handleHeaderKeyDown = useCallback(
    (field: string, e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleHeaderClick(field, e);
      }
    },
    [handleHeaderClick],
  );

  const handleRowKeyDown = useCallback(
    (contractId: string, e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        onRowClick?.(contractId);
      }
    },
    [onRowClick],
  );

  function getAriaSort(field: string): 'ascending' | 'descending' | 'none' {
    const idx = findSortIndex(sort, field);
    if (idx < 0) return 'none';
    return sort[idx][1] === 'asc' ? 'ascending' : 'descending';
  }

  if (!contracts.length) {
    return (
      <div data-testid="contracts-table" className="text-slate-400 text-sm p-8 text-center" role="status">
        <svg className="w-10 h-10 mx-auto mb-2 text-slate-300" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m5.231 13.481L15 17.25m-4.5-15H5.625c-.621 0-1.125.504-1.125 1.125v16.5c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Zm3.75 11.625a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" /></svg>
        No contracts to display
      </div>
    );
  }

  return (
    <div data-testid="contracts-table" className="glass-card overflow-hidden">
      <div className="overflow-x-auto">
      <table className="data-table" aria-label="Contracts">
        <thead>
          <tr>
            {columns.map((col) => {
              const sortIdx = findSortIndex(sort, col.key);
              const isSorted = sortIdx >= 0;
              return (
                <th
                  key={col.key}
                  scope="col"
                  data-testid={`th-${col.key}`}
                  aria-sort={col.sortable ? getAriaSort(col.key) : undefined}
                  tabIndex={col.sortable ? 0 : undefined}
                  role="columnheader"
                  className={`${col.sortable ? 'sortable' : ''} ${col.className || ''}`}
                  onClick={col.sortable ? (e) => handleHeaderClick(col.key, e) : undefined}
                  onKeyDown={col.sortable ? (e) => handleHeaderKeyDown(col.key, e) : undefined}
                >
                  {col.label}
                  {isSorted && (
                    <span className="ml-1 text-primary-600">
                      {directionArrow(sort[sortIdx][1])}
                      {sort.length > 1 && PRIORITY_BADGES[sortIdx] ? (
                        <span className="text-primary-500 ml-0.5">{PRIORITY_BADGES[sortIdx]}</span>
                      ) : null}
                    </span>
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {contracts.map((c) => (
            <tr
              key={c.contract_id}
              data-testid={`row-${c.contract_id}`}
              className="cursor-pointer"
              tabIndex={0}
              role="row"
              aria-label={`Contract: ${c.contract_title || 'Unknown'}`}
              onClick={() => c.contract_id && onRowClick?.(c.contract_id)}
              onKeyDown={(e) => c.contract_id ? handleRowKeyDown(c.contract_id, e) : undefined}
            >
              {columns.map((col) => (
                <td key={col.key} className={col.className || ''}>
                  {col.render(c)}
                </td>
              ))}
              {contractSeverities && c.contract_id && contractSeverities[c.contract_id] != null && (
                <td data-testid={`severity-${c.contract_id}`}>
                  <SeverityIndicator severity={contractSeverities[c.contract_id]} />
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}
