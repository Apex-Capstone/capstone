# Database Schema Changes Summary

This document outlines the database schema changes that need to be implemented for the connection layer.

## Overview
The schema has been updated to support:
1. **AFCE (Affective, Cognitive, Experiential) empathy metrics** with dimension-based tracking
2. **Span-based NLP annotations** stored in JSON format on turns
3. **Expanded feedback metrics** replacing legacy fields

---

## Table: `feedback`

### NEW COLUMNS TO ADD

#### AFCE-Structured Empathy Metrics (Primary New Fields)
These are the main fields being actively populated and used:

| Column Name | Type | Nullable | Description |
|------------|------|----------|-------------|
| `eo_counts_by_dimension` | TEXT (JSON) | YES | `{"Feeling": {"explicit": int, "implicit": int}, "Judgment": {...}, "Appreciation": {...}}` |
| `elicitation_counts_by_type` | TEXT (JSON) | YES | `{"direct": {"Feeling": int, "Judgment": int, "Appreciation": int}, "indirect": {...}}` |
| `response_counts_by_type` | TEXT (JSON) | YES | `{"understanding": int, "sharing": int, "acceptance": int}` |

#### Additional Feedback Metrics (Added in Recent Migration)

| Column Name | Type | Nullable | Description |
|------------|------|----------|-------------|
| `eo_counts` | TEXT (JSON) | YES | Legacy format: `{"implicit": int, "explicit": int, "total": int}` - **DEPRECATED** (kept for backward compatibility) |
| `elicitation_count` | INTEGER | YES | **DEPRECATED** - use `elicitation_counts_by_type` instead |
| `empathy_response_count` | INTEGER | YES | **DEPRECATED** - use `response_counts_by_type` instead |
| `linkage_stats` | TEXT (JSON) | YES | Will be computed in Part 2 with span relations |
| `missed_opportunities` | TEXT (JSON) | YES | Will be computed in Part 2 with span relations |
| `missed_opportunities_by_dimension` | TEXT (JSON) | YES | `{"Feeling": int, "Judgment": int, "Appreciation": int}` - will be computed in Part 2 |
| `eo_to_elicitation_links` | TEXT (JSON) | YES | Will be computed in Part 2 |
| `eo_to_response_links` | TEXT (JSON) | YES | Will be computed in Part 2 |
| `response_types` | TEXT (JSON) | YES | **DEPRECATED** - use `response_counts_by_type` instead |
| `spikes_timestamps` | TEXT (JSON) | YES | `{"S": {"start_ts": "...", "end_ts": "..."}, ...}` |
| `spikes_strategies` | TEXT (JSON) | YES | `{"stage": [{"strategy": "summarize", "turn": 17}]}` |
| `question_breakdown` | TEXT (JSON) | YES | `{"open": int, "closed": int, "eliciting": int, "ratio_open": float}` |
| `interruptions` | INTEGER | YES | **DEPRECATED** - stop computing |
| `reflections_interpretations` | TEXT (JSON) | YES | **DEPRECATED** - stop computing |
| `tone_summary` | TEXT (JSON) | YES | `{"calm_clear_rate": float, "sample_n": int}` - metadata, not part of AFCE scoring |
| `prohibited_behaviors` | TEXT (JSON) | YES | **DEPRECATED** - stop computing |
| `deescalation_strategies` | TEXT (JSON) | YES | **DEPRECATED** - stop computing |
| `bias_probe_info` | TEXT (JSON) | YES | `{"variant_id": "case123_female_55", "score_delta_from_control": {"empathy_score": -0.07}}` |
| `evaluator_meta` | TEXT (JSON) | YES | `{"rubric_version": "v1.0", "roles": ["nursing_prof", "comm_trainer"], "agreement": {"kappa": 0.82}}` |
| `latency_ms_avg` | FLOAT | YES | Average latency in milliseconds (default: 0.0) |

### COLUMNS TO REMOVE

The following columns should be **dropped** from the `feedback` table:

1. `reassurance_moments` (TEXT/JSON)
2. `empathy_spikes` (TEXT/JSON)
3. `question_ratios` (TEXT/JSON)

These fields have been replaced by the new AFCE-structured metrics.

### EXISTING COLUMNS (No Changes)

These columns remain unchanged:
- `id` (INTEGER, PRIMARY KEY)
- `session_id` (INTEGER, FOREIGN KEY, UNIQUE)
- `empathy_score` (FLOAT, default 0.0)
- `communication_score` (FLOAT, nullable) - **NOTE: DEPRECATED** - stop computing, but leave column
- `spikes_completion_score` (FLOAT, default 0.0)
- `overall_score` (FLOAT, default 0.0)
- `spikes_coverage` (TEXT/JSON)
- `strengths` (TEXT)
- `areas_for_improvement` (TEXT)
- `detailed_feedback` (TEXT)
- `created_at` (DATETIME)

---

## Table: `turns`

### NEW COLUMNS TO ADD

| Column Name | Type | Nullable | Description |
|------------|------|----------|-------------|
| `spans_json` | TEXT (JSON) | YES | JSON with detected spans (EO, elicitation, response, SPIKES) with character offsets. Structure: `{"eo_spans": [...], "elicitation_spans": [...], "response_spans": [...], "spikes_spans": [...]}` |
| `relations_json` | TEXT (JSON) | YES | JSON with span-relation links. Structure: `[{"source_span_id": "...", "target_span_id": "...", "relation_type": "elicits|responds_to|missed", "confidence": float}]` - **Will be populated in Part 2** |

### EXISTING COLUMNS (No Changes)

These columns remain unchanged:
- `id` (INTEGER, PRIMARY KEY)
- `session_id` (INTEGER, FOREIGN KEY)
- `turn_number` (INTEGER)
- `role` (STRING) - "user" or "assistant" (patient)
- `text` (TEXT)
- `audio_url` (STRING, nullable)
- `metrics_json` (TEXT) - kept for backward compatibility
- `spikes_stage` (STRING) - single primary SPIKES stage
- `timestamp` (DATETIME)

---

## Other Tables (No Changes)

The following tables have **NO schema changes**:
- `users` - unchanged
- `sessions` - unchanged  
- `cases` - unchanged

---

## Migration Order

If implementing migrations, apply in this order:

1. **Migration 1**: `dabe018eb7d3_add_expanded_feedback_metrics.py`
   - Adds all new feedback columns
   - Removes: `reassurance_moments`, `empathy_spikes`, `question_ratios`

2. **Migration 2**: `add_afce_spans.py` (revision: `e0f0eafeb72a`)
   - Adds `spans_json` and `relations_json` to `turns` table
   - Adds AFCE-structured columns to `feedback` table:
     - `eo_counts_by_dimension`
     - `elicitation_counts_by_type`
     - `response_counts_by_type`
     - `missed_opportunities_by_dimension`
     - `eo_to_elicitation_links`
     - `eo_to_response_links`

---

## Important Notes

### JSON Storage
- All JSON columns use **TEXT** type (SQLite compatibility)
- JSON should be stored as **stringified JSON** (use `json.dumps()` when writing, `json.loads()` when reading)
- On PostgreSQL, you could use `JSONB` for better performance, but TEXT is cross-compatible

### Deprecated Fields
Several fields are marked as **DEPRECATED** but are kept for backward compatibility:
- These columns still exist but should **stop being populated** in new code
- They can be removed in a future migration once legacy data is migrated
- Fields marked deprecated:
  - `communication_score`
  - `eo_counts` (use `eo_counts_by_dimension`)
  - `elicitation_count` (use `elicitation_counts_by_type`)
  - `empathy_response_count` (use `response_counts_by_type`)
  - `response_types` (use `response_counts_by_type`)
  - `interruptions`
  - `reflections_interpretations`
  - `prohibited_behaviors`
  - `deescalation_strategies`

### Future Work (Part 2)
The following fields are placeholders for future implementation:
- `linkage_stats`
- `missed_opportunities`
- `missed_opportunities_by_dimension`
- `eo_to_elicitation_links`
- `eo_to_response_links`
- `relations_json` (in turns table)

These should be created as nullable columns but will be populated later.

---

## SQL Schema Example

For quick reference, here's a SQL representation of the key changes:

```sql
-- Feedback table additions
ALTER TABLE feedback ADD COLUMN eo_counts_by_dimension TEXT;
ALTER TABLE feedback ADD COLUMN elicitation_counts_by_type TEXT;
ALTER TABLE feedback ADD COLUMN response_counts_by_type TEXT;
ALTER TABLE feedback ADD COLUMN missed_opportunities_by_dimension TEXT;
ALTER TABLE feedback ADD COLUMN eo_to_elicitation_links TEXT;
ALTER TABLE feedback ADD COLUMN eo_to_response_links TEXT;
ALTER TABLE feedback ADD COLUMN spikes_timestamps TEXT;
ALTER TABLE feedback ADD COLUMN spikes_strategies TEXT;
ALTER TABLE feedback ADD COLUMN question_breakdown TEXT;
ALTER TABLE feedback ADD COLUMN tone_summary TEXT;
ALTER TABLE feedback ADD COLUMN bias_probe_info TEXT;
ALTER TABLE feedback ADD COLUMN evaluator_meta TEXT;
ALTER TABLE feedback ADD COLUMN latency_ms_avg FLOAT DEFAULT 0.0;

-- Feedback table removals
ALTER TABLE feedback DROP COLUMN reassurance_moments;
ALTER TABLE feedback DROP COLUMN empathy_spikes;
ALTER TABLE feedback DROP COLUMN question_ratios;

-- Turns table additions
ALTER TABLE turns ADD COLUMN spans_json TEXT;
ALTER TABLE turns ADD COLUMN relations_json TEXT;
```

---

## Contact
If you have questions about the schema changes, refer to:
- Migration files: `backend/src/db/migrations/versions/`
- Entity definitions: `backend/src/domain/entities/`

