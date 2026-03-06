/**
 * RuleBadge Component (Phase 4)
 *
 * Small badge displayed on contract or vendor rows to indicate
 * which rules fired. Color-coded by rule type.
 */

interface RuleBadgeProps {
  ruleId: string;
  ruleName: string;
}

const RULE_COLORS: Record<string, string> = {
  threshold_proximity: 'bg-yellow-100 text-yellow-800',
  vendor_concentration: 'bg-purple-100 text-purple-800',
  fragmentation: 'bg-orange-100 text-orange-800',
  overnight_turnaround: 'bg-red-100 text-red-800',
  new_vendor_large_contract: 'bg-blue-100 text-blue-800',
  round_number_clustering: 'bg-pink-100 text-pink-800',
};

export default function RuleBadge({ ruleId, ruleName }: RuleBadgeProps) {
  const colorClass = RULE_COLORS[ruleId] || 'bg-slate-100 text-slate-700';
  return (
    <span
      data-testid="rule-badge"
      data-rule-id={ruleId}
      className={`inline-block text-xs px-2 py-0.5 rounded-md font-medium whitespace-nowrap ${colorClass}`}
      title={ruleName}
    >
      {ruleName}
    </span>
  );
}
