# Red Flags Advanced Implementation Plan

## Overview

This document outlines the complete implementation plan for integrating advanced red flags functionality across the GovLens application. The implementation covers dataset creation, persistence, filtering, and dashboard visualization.

---

## Phase 1: Red Flags Data Model & Types

**Goal**: Define the TypeScript types and JSON schema for red flag datasets.

### Data Model Design

Each red flag dataset is a JSON file stored in `data/` with the following structure:

```json
{
  "dataset_name": "Analysis Q1 2026",
  "created_at": "2026-03-11T07:00:00.000Z",
  "total_flags": 15,
  "total_contracts_evaluated": 2300,
  "rules_used": [
    {
      "rule_id": "threshold_proximity",
      "rule_name": "Threshold Proximity",
      "severity_label": "moderate",
      "params": { "threshold_eur": 50000, "margin_pct": 5 }
    }
  ],
  "flags": [
    {
      "contract_id": "abc123",
      "contract_title": "IT Services Contract",
      "institution": "Ministry of Finance",
      "vendor": "TechCorp s.r.o.",
      "ico_buyer": "12345678",
      "ico_supplier": "87654321",
      "price_numeric_eur": 49500,
      "date_published": "2026-03-01",
      "category": "IT",
      "award_type": "direct_award",
      "red_flag_type": "threshold_proximity",
      "red_flag_name": "Threshold Proximity",
      "severity": "moderate",
      "description": "Contract value €49,500 is within 5% of €50,000 threshold"
    }
  ]
}
```

**Severity Levels**:
- 🟡 `mild` — Low concern, worth noting
- 🟠 `moderate` — Medium concern, needs review
- 🔴 `severe` — High concern, requires investigation

### Unit Tests (Phase 1)
- Validate `RedFlagDataset` type structure
- Validate `RedFlagOccurrence` field completeness
- Test severity label validation (mild/moderate/severe)
- Test dataset name defaults to datetime when empty

---

## Phase 2: Red Flags View Enhancement

**Goal**: Enhance the Red Flags View with severity selectors, dataset naming, and download capability.

### Changes
1. **Severity selector per rule**: Each rule in `RulePanel` gets a dropdown to choose severity (🟡 Mild, 🟠 Moderate, 🔴 Severe)
2. **Dataset name field**: Text input next to the "Evaluate Rules" button for naming the dataset
3. **Download button**: After evaluation, a "Download Dataset" button exports the red flags as JSON
4. **Existing functionality preserved**: Flags still display below the evaluate button

### Unit Tests (Phase 2)
- Test severity selector renders for each rule
- Test severity defaults to "moderate"
- Test dataset name input field renders
- Test dataset name defaults to datetime when empty
- Test download button appears after evaluation
- Test downloaded JSON structure matches data model
- Test existing flag display still works

---

## Phase 3: Red Flags Dataset Store

**Goal**: Create a client-side store that loads red flag dataset JSON files from the `data/` folder.

### Architecture
- New API endpoint or static file loading for red flag datasets
- `RedFlagStore` context that loads and manages multiple datasets
- Datasets are loaded from `data/red_flags_*.json` files
- Store provides merged view across selected datasets

### Unit Tests (Phase 3)
- Test loading a single dataset
- Test loading multiple datasets
- Test merging flags across datasets
- Test computing vendor/institution flag counts
- Test handling empty/missing datasets

---

## Phase 4: Filter Bar Integration

**Goal**: Add four new filter fields to the FilterBar for red flags.

### New Filter Fields
1. **Red Flag Datasets** (multi-select): Choose which datasets to use. Filters to show ALL vendors/institutions that appear in selected datasets
2. **Red Flag Type** (multi-select): Filter to show ONLY contracts with specific red flag types. Contracts without flags get "no red flag"
3. **Institution Red Flag Count** (min/max range): Filter institutions by their count of flagged contracts
4. **Vendor Red Flag Count** (min/max range): Filter vendors by their count of flagged contracts

### Filter Interaction Logic
- Dataset filter affects which vendors/institutions are available
- Red flag type filter narrows to specific flagged contracts
- Count filters work on aggregated flag counts per entity
- All filters persist in URL state and FilterContext

### Unit Tests (Phase 4)
- Test dataset filter multi-select renders
- Test dataset filter shows vendors/institutions from selected datasets
- Test red flag type filter renders types from selected datasets
- Test red flag type shows "no red flag" for unflagged contracts
- Test institution count filter with min/max
- Test vendor count filter with min/max
- Test filter persistence in URL state
- Test cross-filter interactions

---

## Phase 5: Dashboard Integration

**Goal**: Add red flag information to Dashboard charts and aggregation tables.

### Changes
1. **GroupBy option**: Add `red_flag_type` to treemap and bar chart GroupBy control
2. **Aggregation tables**: Add red flag count column next to existing sum column
3. **Red flag type column**: Add column showing red flag types with severity color coding
4. **Contracts without flags**: Show as "no red flag" in aggregations

### Unit Tests (Phase 5)
- Test red_flag_type appears in GroupBy options
- Test treemap renders with red flag type grouping
- Test bar chart renders with red flag type grouping
- Test aggregation table shows red flag count column
- Test red flag type column renders with correct colors
- Test "no red flag" label for unflagged contracts

---

## Phase 6: Integration Testing

**Goal**: Verify all components work together without conflicts.

### Tests
- End-to-end filter flow: select dataset → see filtered vendors → drill down
- Dashboard + filters: red flag filters affect dashboard visualizations
- URL state round-trip: all new filter fields persist correctly
- Multiple datasets: same contract flagged in different datasets
- Run full test suite and fix any regressions

---

## Implementation Order

1. Types & data model (Phase 1)
2. Red Flags View enhancement (Phase 2)
3. Dataset store & loader (Phase 3)
4. Filter bar integration (Phase 4)
5. Dashboard integration (Phase 5)
6. Integration testing (Phase 6)
