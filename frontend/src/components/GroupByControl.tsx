/**
 * GroupByControl Component
 *
 * Toggle between group-by fields: Vendor, Institution, Category, Month, Award Type.
 */

import type { GroupByField } from '../types';

interface GroupByControlProps {
  value: GroupByField;
  onChange: (field: GroupByField) => void;
}

const OPTIONS: { value: GroupByField; label: string }[] = [
  { value: 'supplier', label: 'Vendor' },
  { value: 'buyer', label: 'Institution' },
  { value: 'category', label: 'Category' },
  { value: 'month', label: 'Month' },
  { value: 'award_type', label: 'Award Type' },
  { value: 'red_flag_type', label: 'Red Flag Type' },
];

export default function GroupByControl({ value, onChange }: GroupByControlProps) {
  return (
    <div data-testid="group-by-control" className="toggle-group" role="group" aria-label="Group data by">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          aria-pressed={value === opt.value}
          aria-label={`Group by ${opt.label}`}
          className={value === opt.value ? 'active' : ''}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}
