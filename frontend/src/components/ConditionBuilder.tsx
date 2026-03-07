/**
 * ConditionBuilder Component (Phase 4)
 *
 * No-code field / operator / value rows with AND/OR toggle.
 * Produces a ConditionGroupData for the backend API.
 */

import { useState, useCallback } from 'react';
import type { ConditionItem, ConditionGroupData, FilterState, CustomRuleResponse } from '../types';
import { evaluateCustomConditions } from '../api';

const FIELDS = [
  'price_numeric_eur',
  'published_date',
  'contract_title',
  'buyer',
  'supplier',
  'category',
  'award_type',
  'date_concluded',
  'date_published',
  'date_effective',
];

const OPERATORS = [
  { value: 'eq', label: '=' },
  { value: 'ne', label: '≠' },
  { value: 'gt', label: '>' },
  { value: 'ge', label: '≥' },
  { value: 'lt', label: '<' },
  { value: 'le', label: '≤' },
  { value: 'contains', label: 'contains' },
];

function emptyCondition(): ConditionItem {
  return { field: 'price_numeric_eur', operator: 'gt', value: '' };
}

interface ConditionBuilderProps {
  filters: FilterState;
  onResult?: (result: CustomRuleResponse) => void;
}

export default function ConditionBuilder({ filters, onResult }: ConditionBuilderProps) {
  const [logic, setLogic] = useState<'AND' | 'OR'>('AND');
  const [conditions, setConditions] = useState<ConditionItem[]>([emptyCondition()]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CustomRuleResponse | null>(null);

  const addRow = useCallback(() => {
    setConditions((prev) => [...prev, emptyCondition()]);
  }, []);

  const removeRow = useCallback((index: number) => {
    setConditions((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const updateCondition = useCallback(
    (index: number, key: keyof ConditionItem, value: string | number) => {
      setConditions((prev) =>
        prev.map((c, i) => (i === index ? { ...c, [key]: value } : c)),
      );
    },
    [],
  );

  const handleEvaluate = useCallback(async () => {
    setLoading(true);
    try {
      // Coerce numeric values
      const coerced = conditions.map((c) => {
        const numFields = ['price_numeric_eur'];
        if (numFields.includes(c.field) && typeof c.value === 'string') {
          const n = Number(c.value);
          return isNaN(n) ? c : { ...c, value: n };
        }
        return c;
      });

      const group: ConditionGroupData = { logic, conditions: coerced };
      const res = await evaluateCustomConditions(group, filters);
      setResult(res);
      onResult?.(res);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [conditions, logic, filters, onResult]);

  return (
    <div data-testid="condition-builder" className="space-y-3">
      <h3 className="section-title">Custom Condition Builder</h3>

      {/* Logic toggle */}
      <div className="flex items-center gap-2 text-sm">
        <span className="text-slate-600">Match</span>
        <button
          data-testid="logic-toggle"
          onClick={() => setLogic((prev) => (prev === 'AND' ? 'OR' : 'AND'))}
          className={`px-3 py-1 rounded-lg text-xs font-semibold transition-colors ${
            logic === 'AND' ? 'bg-primary-100 text-primary-700' : 'bg-orange-100 text-orange-700'
          }`}
        >
          {logic}
        </button>
        <span className="text-slate-600">of the following conditions:</span>
      </div>

      {/* Condition rows */}
      <div className="space-y-2">
        {conditions.map((cond, idx) => (
          <div key={idx} className="flex items-center gap-2" data-testid="condition-row">
            <select
              value={cond.field}
              onChange={(e) => updateCondition(idx, 'field', e.target.value)}
              className="form-select text-sm"
              data-testid="condition-field"
            >
              {FIELDS.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>

            <select
              value={cond.operator}
              onChange={(e) => updateCondition(idx, 'operator', e.target.value)}
              className="form-select text-sm"
              data-testid="condition-operator"
            >
              {OPERATORS.map((op) => (
                <option key={op.value} value={op.value}>
                  {op.label}
                </option>
              ))}
            </select>

            <input
              type="text"
              value={cond.value}
              onChange={(e) => updateCondition(idx, 'value', e.target.value)}
              placeholder="value"
              className="form-input text-sm flex-1"
              data-testid="condition-value"
            />

            <button
              onClick={() => removeRow(idx)}
              disabled={conditions.length <= 1}
              className="text-red-500 hover:text-red-700 disabled:opacity-30 text-sm transition-colors"
              data-testid="condition-remove"
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {/* Add row button */}
      <button
        onClick={addRow}
        className="text-sm text-primary-600 hover:text-primary-800 font-medium transition-colors"
        data-testid="add-condition"
      >
        + Add condition
      </button>

      {/* Evaluate button */}
      <div>
        <button
          onClick={handleEvaluate}
          disabled={loading || conditions.length === 0}
          className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 shadow-sm transition-colors"
          data-testid="custom-evaluate-btn"
        >
          {loading ? 'Evaluating…' : 'Run Custom Query'}
        </button>
      </div>

      {/* Results */}
      {result && (
        <div data-testid="custom-results" className="text-sm glass-card p-3">
          <span className="font-semibold text-slate-800">{result.total_matched}</span> of{' '}
          <span className="text-slate-600">{result.total_evaluated}</span> contracts matched.
        </div>
      )}
    </div>
  );
}
