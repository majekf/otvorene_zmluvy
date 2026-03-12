/**
 * Red Flags Page
 *
 * Dedicated page for pattern detection: FilterBar on top (shared via
 * FilterContext), then RulePanel (preset rules) and ConditionBuilder
 * (custom no-code queries) side by side. Includes dataset management
 * for loading and viewing red flag datasets.
 */

import { useCallback, useRef } from 'react';
import { useFilterContext } from '../FilterContext';
import { useRedFlagContext, severityEmoji, severityBgColor } from '../RedFlagStore';
import FilterBar from '../components/FilterBar';
import RulePanel from '../components/RulePanel';
import ConditionBuilder from '../components/ConditionBuilder';
import type { RedFlagDataset } from '../types';

export default function RedFlagsView() {
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

  const { datasets, addDataset, removeDataset, datasetNames: rfDatasetNames, allFlagTypes: rfFlagTypes } = useRedFlagContext();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFilterChange = useCallback(
    (newFilters: typeof filters) => {
      setFilters(newFilters);
    },
    [setFilters],
  );

  const handleFileUpload = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (event) => {
        try {
          const dataset = JSON.parse(event.target?.result as string) as RedFlagDataset;
          if (dataset.dataset_name && Array.isArray(dataset.flags)) {
            addDataset(dataset);
          }
        } catch {
          // Invalid JSON - ignore
        }
      };
      reader.readAsText(file);
      // Reset input so same file can be re-uploaded
      e.target.value = '';
    },
    [addDataset],
  );

  return (
    <div data-testid="red-flags-view" className="space-y-8 animate-fade-in">
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
        redFlagDatasetNames={rfDatasetNames}
        redFlagTypes={rfFlagTypes}
      />

      {/* Dataset management */}
      <div className="glass-card p-5" data-testid="dataset-manager">
        <div className="flex items-center justify-between mb-3">
          <h3 className="section-title">Red Flag Datasets</h3>
          <div className="flex gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleFileUpload}
              className="hidden"
              data-testid="dataset-file-input"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="px-3 py-1.5 bg-primary-600 text-white rounded-lg text-xs font-medium hover:bg-primary-700 transition-colors shadow-sm"
              data-testid="upload-dataset-btn"
            >
              📁 Load Dataset JSON
            </button>
          </div>
        </div>

        {datasets.length === 0 ? (
          <p className="text-sm text-slate-400">
            No datasets loaded. Evaluate rules below to create a dataset, or upload a JSON file.
          </p>
        ) : (
          <div className="space-y-2" data-testid="dataset-list">
            {datasets.map((ds) => (
              <div
                key={ds.dataset_name}
                className="flex items-center justify-between glass-card p-3 text-sm"
                data-testid={`dataset-item-${ds.dataset_name}`}
              >
                <div className="flex-1">
                  <span className="font-semibold text-slate-800">{ds.dataset_name}</span>
                  <span className="text-slate-500 ml-2">
                    {ds.total_flags} flag{ds.total_flags !== 1 ? 's' : ''}
                  </span>
                  <span className="text-slate-400 ml-2 text-xs">
                    {new Date(ds.created_at).toLocaleString()}
                  </span>
                  {ds.rules_used.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {ds.rules_used.map((r) => (
                        <span
                          key={r.rule_id}
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${severityBgColor(r.severity_label)}`}
                        >
                          {severityEmoji(r.severity_label)} {r.rule_name}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => removeDataset(ds.dataset_name)}
                  className="text-red-500 hover:text-red-700 text-sm ml-3 transition-colors"
                  data-testid={`remove-dataset-${ds.dataset_name}`}
                  title="Remove dataset"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

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
