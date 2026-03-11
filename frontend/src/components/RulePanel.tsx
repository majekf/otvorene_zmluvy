/**
 * RulePanel Component (Phase 4)
 *
 * Displays preset rules with param editors (sliders + number inputs),
 * severity selectors per rule, dataset naming, and an "Evaluate" button.
 * Shows results as a list of flags with download capability.
 */

import { useState, useCallback, useEffect } from 'react';
import type { RulePreset, RuleConfig, RuleFlagItem, FilterState, RedFlagSeverity, RedFlagDataset, RedFlagOccurrence, RedFlagRuleUsed } from '../types';
import { fetchRulePresets, evaluateRules } from '../api';
import { useRedFlagContext, defaultDatasetName, severityEmoji } from '../RedFlagStore';
import RuleBadge from './RuleBadge';
import SeverityIndicator from './SeverityIndicator';

interface RulePanelProps {
  filters: FilterState;
  onFlagsChange?: (severities: Record<string, number>, flags: RuleFlagItem[]) => void;
}

export default function RulePanel({ filters, onFlagsChange }: RulePanelProps) {
  const [presets, setPresets] = useState<RulePreset[]>([]);
  const [enabledRules, setEnabledRules] = useState<Set<string>>(new Set());
  const [paramOverrides, setParamOverrides] = useState<Record<string, Record<string, number>>>({});
  const [severityOverrides, setSeverityOverrides] = useState<Record<string, RedFlagSeverity>>({});
  const [flags, setFlags] = useState<RuleFlagItem[]>([]);
  const [totalFlags, setTotalFlags] = useState(0);
  const [loading, setLoading] = useState(false);
  const [presetsLoading, setPresetsLoading] = useState(true);
  const [datasetName, setDatasetName] = useState('');
  const [lastEvalResult, setLastEvalResult] = useState<{
    flags: RuleFlagItem[];
    totalFlags: number;
    totalEvaluated: number;
  } | null>(null);

  const { addDataset } = useRedFlagContext();

  // Load presets on mount
  useEffect(() => {
    fetchRulePresets()
      .then((res) => {
        setPresets(res.presets);
        // Enable all by default
        setEnabledRules(new Set(res.presets.map((p) => p.id)));
        // Set default params
        const defaults: Record<string, Record<string, number>> = {};
        const defaultSeverities: Record<string, RedFlagSeverity> = {};
        for (const p of res.presets) {
          defaults[p.id] = { ...p.params };
          defaultSeverities[p.id] = 'moderate';
        }
        setParamOverrides(defaults);
        setSeverityOverrides(defaultSeverities);
      })
      .catch(() => {})
      .finally(() => setPresetsLoading(false));
  }, []);

  const toggleRule = useCallback((id: string) => {
    setEnabledRules((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const updateParam = useCallback((ruleId: string, paramKey: string, value: number) => {
    setParamOverrides((prev) => ({
      ...prev,
      [ruleId]: { ...prev[ruleId], [paramKey]: value },
    }));
  }, []);

  const updateSeverity = useCallback((ruleId: string, severity: RedFlagSeverity) => {
    setSeverityOverrides((prev) => ({
      ...prev,
      [ruleId]: severity,
    }));
  }, []);

  const handleEvaluate = useCallback(async () => {
    setLoading(true);
    try {
      const rules: RuleConfig[] = presets
        .filter((p) => enabledRules.has(p.id))
        .map((p) => ({
          id: p.id,
          params: paramOverrides[p.id] || p.params,
        }));

      const result = await evaluateRules(rules.length > 0 ? rules : null, filters);
      setFlags(result.flags);
      setTotalFlags(result.total_flags);
      setLastEvalResult({
        flags: result.flags,
        totalFlags: result.total_flags,
        totalEvaluated: Object.keys(result.contract_severities).length,
      });
      onFlagsChange?.(result.contract_severities, result.flags);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [presets, enabledRules, paramOverrides, filters, onFlagsChange]);

  const buildDataset = useCallback((): RedFlagDataset => {
    const name = datasetName.trim() || defaultDatasetName();
    const now = new Date().toISOString();

    const rulesUsed: RedFlagRuleUsed[] = presets
      .filter((p) => enabledRules.has(p.id))
      .map((p) => ({
        rule_id: p.id,
        rule_name: p.name,
        severity_label: severityOverrides[p.id] || 'moderate',
        params: paramOverrides[p.id] || p.params,
      }));

    const flagOccurrences: RedFlagOccurrence[] = (lastEvalResult?.flags || []).map((f) => ({
      contract_id: f.contract_id || '',
      contract_title: (f.details?.contract_title as string) || '',
      institution: f.institution || '',
      vendor: f.vendor || '',
      ico_buyer: (f.details?.ico_buyer as string) || null,
      ico_supplier: (f.details?.ico_supplier as string) || null,
      price_numeric_eur: (f.details?.price_numeric_eur as number) || null,
      date_published: (f.details?.date_published as string) || null,
      category: (f.details?.category as string) || '',
      award_type: (f.details?.award_type as string) || '',
      red_flag_type: f.rule_id,
      red_flag_name: f.rule_name,
      severity: severityOverrides[f.rule_id] || 'moderate',
      description: f.description,
    }));

    return {
      dataset_name: name,
      created_at: now,
      total_flags: lastEvalResult?.totalFlags || 0,
      total_contracts_evaluated: lastEvalResult?.totalEvaluated || 0,
      rules_used: rulesUsed,
      flags: flagOccurrences,
    };
  }, [datasetName, presets, enabledRules, severityOverrides, paramOverrides, lastEvalResult]);

  const handleDownload = useCallback(() => {
    const dataset = buildDataset();
    const json = JSON.stringify(dataset, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `red_flags_${dataset.dataset_name.replace(/\s+/g, '_')}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [buildDataset]);

  const handleAddToStore = useCallback(() => {
    const dataset = buildDataset();
    addDataset(dataset);
  }, [buildDataset, addDataset]);

  if (presetsLoading) {
    return <div data-testid="rule-panel" className="text-sm text-slate-500">Loading rules…</div>;
  }

  return (
    <div data-testid="rule-panel" className="space-y-4">
      <h3 className="section-title">Pattern Detection Rules</h3>

      {/* Preset rules list */}
      <div className="space-y-3">
        {presets.map((preset) => (
          <div
            key={preset.id}
            className="glass-card p-4"
            data-testid={`rule-${preset.id}`}
          >
            <div className="flex items-start gap-2">
              <input
                type="checkbox"
                checked={enabledRules.has(preset.id)}
                onChange={() => toggleRule(preset.id)}
                data-testid={`rule-toggle-${preset.id}`}
                className="mt-0.5 rounded border-slate-300 text-primary-600 focus:ring-primary-500"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm text-slate-800">{preset.name}</span>
                  {/* Severity selector */}
                  <select
                    value={severityOverrides[preset.id] || 'moderate'}
                    onChange={(e) => updateSeverity(preset.id, e.target.value as RedFlagSeverity)}
                    className="form-select text-xs py-0.5 px-1.5 w-auto"
                    data-testid={`severity-select-${preset.id}`}
                  >
                    <option value="mild">🟡 Mild</option>
                    <option value="moderate">🟠 Moderate</option>
                    <option value="severe">🔴 Severe</option>
                  </select>
                </div>
                <div className="text-xs text-slate-500 mt-0.5">{preset.description}</div>

                {/* Param editors */}
                {enabledRules.has(preset.id) && (
                  <div className="mt-3 space-y-2">
                    {Object.entries(paramOverrides[preset.id] || preset.params).map(
                      ([key, val]) => (
                        <div key={key} className="flex items-center gap-2 text-xs">
                          <label className="w-32 text-slate-600 font-medium">{key}</label>
                          <input
                            type="range"
                            min={0}
                            max={key.includes('pct') ? 100 : key.includes('hours') ? 168 : 1_000_000}
                            step={key.includes('pct') ? 1 : key.includes('hours') ? 1 : key.includes('contracts') ? 1 : 1000}
                            value={val}
                            onChange={(e) => updateParam(preset.id, key, Number(e.target.value))}
                            className="flex-1 accent-primary-600"
                            data-testid={`param-${preset.id}-${key}`}
                          />
                          <input
                            type="number"
                            value={val}
                            onChange={(e) => updateParam(preset.id, key, Number(e.target.value))}
                            className="form-input w-24 text-right text-xs"
                          />
                        </div>
                      ),
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Dataset name + Evaluate button */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col">
          <label className="text-xs font-semibold text-slate-500 mb-1 tracking-wide uppercase">
            Dataset Name
          </label>
          <input
            type="text"
            value={datasetName}
            onChange={(e) => setDatasetName(e.target.value)}
            placeholder="Auto-generated from datetime"
            className="form-input text-sm w-64"
            data-testid="dataset-name-input"
          />
        </div>
        <button
          data-testid="evaluate-btn"
          onClick={handleEvaluate}
          disabled={loading || enabledRules.size === 0}
          className="btn-primary disabled:opacity-50"
        >
          {loading ? 'Evaluating…' : 'Evaluate Rules'}
        </button>
      </div>

      {/* Results */}
      {totalFlags > 0 && (
        <div data-testid="rule-results" className="space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="section-title text-sm">
              {totalFlags} flag{totalFlags !== 1 ? 's' : ''} found
            </h4>
            <div className="flex gap-2">
              <button
                onClick={handleAddToStore}
                className="px-3 py-1.5 bg-primary-600 text-white rounded-lg text-xs font-medium hover:bg-primary-700 transition-colors shadow-sm"
                data-testid="add-to-store-btn"
              >
                Add to Active Datasets
              </button>
              <button
                onClick={handleDownload}
                className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-xs font-medium hover:bg-green-700 transition-colors shadow-sm"
                data-testid="download-dataset-btn"
              >
                ⬇ Download JSON
              </button>
            </div>
          </div>
          <div className="max-h-80 overflow-y-auto space-y-1">
            {flags.map((flag, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 text-xs border-b border-slate-100 py-1.5"
                data-testid="rule-flag"
              >
                <SeverityIndicator severity={flag.severity} />
                <span className="text-sm" title={severityOverrides[flag.rule_id] || 'moderate'}>
                  {severityEmoji(severityOverrides[flag.rule_id] || 'moderate')}
                </span>
                <RuleBadge ruleId={flag.rule_id} ruleName={flag.rule_name} />
                <span className="text-slate-600 flex-1">{flag.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
