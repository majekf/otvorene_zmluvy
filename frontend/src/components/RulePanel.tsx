/**
 * RulePanel Component (Phase 4)
 *
 * Displays preset rules with param editors (sliders + number inputs)
 * and an "Evaluate" button. Shows results as a list of flags.
 */

import { useState, useCallback, useEffect } from 'react';
import type { RulePreset, RuleConfig, RuleFlagItem, FilterState } from '../types';
import { fetchRulePresets, evaluateRules } from '../api';
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
  const [flags, setFlags] = useState<RuleFlagItem[]>([]);
  const [totalFlags, setTotalFlags] = useState(0);
  const [loading, setLoading] = useState(false);
  const [presetsLoading, setPresetsLoading] = useState(true);

  // Load presets on mount
  useEffect(() => {
    fetchRulePresets()
      .then((res) => {
        setPresets(res.presets);
        // Enable all by default
        setEnabledRules(new Set(res.presets.map((p) => p.id)));
        // Set default params
        const defaults: Record<string, Record<string, number>> = {};
        for (const p of res.presets) {
          defaults[p.id] = { ...p.params };
        }
        setParamOverrides(defaults);
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
      onFlagsChange?.(result.contract_severities, result.flags);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [presets, enabledRules, paramOverrides, filters, onFlagsChange]);

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
                <div className="font-medium text-sm text-slate-800">{preset.name}</div>
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

      {/* Evaluate button */}
      <button
        data-testid="evaluate-btn"
        onClick={handleEvaluate}
        disabled={loading || enabledRules.size === 0}
        className="btn-primary disabled:opacity-50"
      >
        {loading ? 'Evaluating…' : 'Evaluate Rules'}
      </button>

      {/* Results */}
      {totalFlags > 0 && (
        <div data-testid="rule-results" className="space-y-2">
          <h4 className="section-title text-sm">
            {totalFlags} flag{totalFlags !== 1 ? 's' : ''} found
          </h4>
          <div className="max-h-80 overflow-y-auto space-y-1">
            {flags.map((flag, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 text-xs border-b border-slate-100 py-1.5"
                data-testid="rule-flag"
              >
                <SeverityIndicator severity={flag.severity} />
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
