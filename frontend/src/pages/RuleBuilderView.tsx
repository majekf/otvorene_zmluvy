/**
 * Rule Builder Page
 *
 * Dedicated page for pattern detection: FilterBar on top (shared via
 * FilterContext), then RulePanel (preset rules) and ConditionBuilder
 * (custom no-code queries) side by side.
 */

import { useCallback } from 'react';
import { useFilterContext } from '../FilterContext';
import FilterBar from '../components/FilterBar';
import RulePanel from '../components/RulePanel';
import ConditionBuilder from '../components/ConditionBuilder';

export default function RuleBuilderView() {
  const {
    filters,
    setFilters,
    institutions: distinctInstitutions,
    categories: distinctCategories,
    vendors: distinctVendors,
    institutionIcos,
    vendorIcos,
    institutionIcoMap,
    vendorIcoMap,
    institutionCounts,
    vendorCounts,
    institutionIcoCounts,
    vendorIcoCounts,
    categoryCounts,
    awardTypes: distinctAwardTypes,
    optionsLoaded,
  } = useFilterContext();

  const handleFilterChange = useCallback(
    (newFilters: typeof filters) => {
      setFilters(newFilters);
    },
    [setFilters],
  );

  return (
    <div data-testid="rule-builder-view" className="space-y-8 animate-fade-in">
      {/* Filters */}
      <FilterBar
        filters={filters}
        onChange={handleFilterChange}
        institutions={distinctInstitutions}
        categories={distinctCategories}
        vendors={distinctVendors}
        institutionIcos={institutionIcos}
        vendorIcos={vendorIcos}
        institutionIcoMap={institutionIcoMap}
        vendorIcoMap={vendorIcoMap}
        institutionCounts={institutionCounts}
        vendorCounts={vendorCounts}
        institutionIcoCounts={institutionIcoCounts}
        vendorIcoCounts={vendorIcoCounts}
        categoryCounts={categoryCounts}
        awardTypes={distinctAwardTypes}
        optionsLoaded={optionsLoaded}
      />

      {/* Pattern Detection panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-5">
          <RulePanel filters={filters} />
        </div>
        <div className="glass-card p-5">
          <ConditionBuilder filters={filters} />
        </div>
      </div>
    </div>
  );
}
