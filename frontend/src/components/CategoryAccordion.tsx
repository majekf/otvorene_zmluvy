/**
 * CategoryAccordion Component
 *
 * Expandable rows showing group name + aggregated total.
 * Click expands to reveal the contracts table.
 */

import { useState } from 'react';
import type { AggregationResult } from '../types';
import { formatEur } from '../utils';

interface CategoryAccordionProps {
  groups: AggregationResult[];
  /** Render the expanded content (contracts table) for a given group value. */
  renderExpanded: (groupValue: string) => React.ReactNode;
  /** Currently open groups (controlled from outside for URL state). */
  openGroups?: Set<string>;
  onToggle?: (groupValue: string) => void;
}

export default function CategoryAccordion({
  groups,
  renderExpanded,
  openGroups: controlledOpen,
  onToggle,
}: CategoryAccordionProps) {
  const [internalOpen, setInternalOpen] = useState<Set<string>>(new Set());
  const openGroups = controlledOpen ?? internalOpen;

  function toggle(groupValue: string) {
    if (onToggle) {
      onToggle(groupValue);
    } else {
      setInternalOpen((prev) => {
        const next = new Set(prev);
        if (next.has(groupValue)) next.delete(groupValue);
        else next.add(groupValue);
        return next;
      });
    }
  }

  if (!groups.length) {
    return <div className="text-slate-400 text-sm p-6 text-center" role="status">No groups to display</div>;
  }

  return (
    <div data-testid="category-accordion" className="glass-card overflow-hidden divide-y divide-slate-100">
      {groups.map((g) => {
        const isOpen = openGroups.has(g.group_value);
        return (
          <div key={g.group_value}>
            <button
              data-testid={`accordion-header-${g.group_value}`}
              className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-slate-50/80 transition-colors text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-400"
              onClick={() => toggle(g.group_value)}
              aria-expanded={isOpen}
              aria-controls={`panel-${g.group_value}`}
              id={`header-${g.group_value}`}
            >
              <div className="flex items-center gap-3">
                <svg className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${isOpen ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" /></svg>
                <span className="font-semibold text-slate-800">{g.group_value}</span>
                <span className="chip chip-gray">
                  {g.contract_count} contract{g.contract_count !== 1 ? 's' : ''}
                </span>
              </div>
              <span className="font-bold text-slate-700 tabular-nums">{formatEur(g.total_spend)}</span>
            </button>
            {isOpen && (
              <div
                data-testid={`accordion-content-${g.group_value}`}
                className="px-5 pb-4 animate-fade-in"
                id={`panel-${g.group_value}`}
                role="region"
                aria-labelledby={`header-${g.group_value}`}
              >
                {renderExpanded(g.group_value)}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
