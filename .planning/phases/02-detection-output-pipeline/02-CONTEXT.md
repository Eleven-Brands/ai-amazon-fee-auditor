# Phase 2: Detection + Output Pipeline - Context

**Gathered:** 2026-05-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Build the full audit pipeline end-to-end: pull 16 weeks of historical FBA fee data from Power BI (or weekly snapshot thereafter), calculate rolling 8-week median baselines per SKU per country, flag anomalies, generate a Claude narrative, and post a ClickUp comment with a CSV attachment. Phase 2 produces `run_audit.py` — a locally executable script. No scheduling, no n8n (those are Phase 3).

</domain>

<decisions>
## Implementation Decisions

### Baseline Strategy

- **D-01:** Baseline method = **historical DAX query on first run**, then weekly snapshot accumulation. First run queries `fact_fee_preview` WITHOUT `is_latest` filter, batched by country code, to obtain 16 weeks of historical rows. Subsequent runs fetch only the current `is_latest=1` snapshot and append it to `snapshots/`.
- **D-02:** Historical query batching = **by country code** (US, CA, GB, DE, FR, ES, IT, MX, BE — 9 batches + one batch for `amzn.gr.*` keys). Each batch stays well under the 1M PBI value limit. Sales Region-level batching is NOT used (EU bundle would be too large).
- **D-03:** Lookback window for first run = **16 weeks**. Enough for a robust 8-week rolling median with 8 weeks of margin.
- **D-04:** Snapshot storage = **one CSV per run date**: `snapshots/snapshot_YYYYMMDD.csv`. Rolling baseline window slices the N most recent files. Simple, auditable, each week individually reprocessable.
- **D-05:** Rolling baseline = **8-week rolling median** of `avg_fee_per_unit` per `key_sales_marketplace_sku`. Median is preferred over mean (more robust to outliers — confirmed Phase 1 decision).
- **D-06:** First-run detection: if fewer than 4 snapshots exist when the script runs, the system still computes baselines from whatever history is available but logs a warning ("baseline computed from N weeks — results may be noisy until 4+ weeks accumulate").

### Anomaly Detection

- **D-07:** Anomaly threshold = **15%** deviation from 8-week rolling median baseline (initial value — calibrate empirically after first real run).
- **D-08:** Config file = **`audit_config.json`** in project root. Contains: `THRESHOLD_PCT`, `CLICKUP_TASK_ID`, `RECIPIENTS`, `SUSTAINED_SHIFT_N`. All calibration knobs in one place. Tracked in git (no secrets).
- **D-09:** Anomaly direction handling = **flag increases prominently, decreases as informational**. ClickUp comment has two sections: "Fee increases — action needed (N SKUs)" and "Fee reductions — informational (M SKUs)". Both categories appear in the attached CSV.
- **D-10:** Baseline grain = **per `key_sales_marketplace_sku`** (country-level key, not Sales Region-level). EU countries (DE, FR, ES, IT) have separate baselines per country. Sales Region grouping is preserved in the output CSV for reference (via `SKUs[Sales Region]` join from Phase 1) but detection runs at country level.

### Sustained-Shift Detection (DETECT-03)

- **D-11:** Sustained-shift threshold = **4 consecutive weeks** flagged in the same direction → SKU is reclassified as "sustained shift". Value is stored in `audit_config.json` as `SUSTAINED_SHIFT_N` (default: 4).
- **D-12:** Sustained-shift state storage = **`anomaly_history.csv`** (cumulative append). Schema from explore_fees.py comment (line 424-428): `key_sales_marketplace_sku`, `country`, `sku`, `asin`, `sales_region`, `week_start_date`, `avg_fee_per_unit`, `baseline_median_fee_per_unit`, `deviation_pct`, `direction`, `consecutive_weeks_flagged`, `run_date`. Each run appends new flagged rows; consecutive count is looked up from prior rows for same SKU+direction.
- **D-13:** Sustained-shift behavior = **excluded from ClickUp comment** (not in summary, not in escalation prompt), but **included in attached CSV** with a `sustained_shift: true` flag column. Human can review in CSV if needed. No second section in the comment for sustained shifts.

### ClickUp Output

- **D-14:** ClickUp task ID = **placeholder in `audit_config.json`** (`CLICKUP_TASK_ID: "PLACEHOLDER"`). Developer sets real task ID before first run. Phase 2 plan must include a note: "configure `CLICKUP_TASK_ID` before executing."
- **D-15:** ClickUp comment structure = Claude-generated summary (≤150 words) covering: run date, total SKUs scanned, fee increases (count + top 3 by deviation %), fee reductions (count, informational). Comment ends with escalation prompt.
- **D-16:** Escalation prompt (ESC-01) = plain text at end of comment: `"Reply YES to this comment to open an investigation task for the top flagged SKUs."` No form, no options — human replies manually and creates the task themselves.
- **D-17:** ClickUp recipients = **no notifications during testing** (`RECIPIENTS: []` in `audit_config.json`). Victor added when system is validated by updating config — no code changes.
- **D-18:** CSV attachment (OUT-02) = attached to the same ClickUp comment. Columns: `key_sales_marketplace_sku`, `country`, `sales_region`, `sku`, `asin`, `week_start_date`, `avg_fee_per_unit`, `baseline_median_fee_per_unit`, `deviation_pct`, `direction`, `sustained_shift`. Includes both increase and decrease rows; sustained-shift rows marked with flag but included.

### Claude Narrative

- **D-19:** Claude is **narrative layer only** — all math (baseline, deviation, classification) in Python. Claude receives a structured JSON summary of anomalies, never raw fee tables.
- **D-20:** Claude invocation = direct Anthropic SDK call (`claude-sonnet-4-6`). No LangChain or agent frameworks. Single call with a concise prompt containing the anomaly JSON summary. Token budget: keep context under 4K tokens (anomaly JSON + system prompt).
- **D-21:** Claude output constraint = ≤150 words for the ClickUp comment body. Claude must produce text that is copy-paste ready for the comment — no post-processing needed.

### Script Structure

- **D-22:** Phase 2 produces **`run_audit.py`** — a new script that imports and reuses `get_token()`, `run_dax()`, `validate_value_count()`, `process_pbi_rows()`, `build_output_df()`, and `iso_to_week_start()` from `explore_fees.py`. No code duplication.
- **D-23:** Entry points: `python run_audit.py` (full audit run). Phase 3 will add `--trigger manual` flag and Windows Task Scheduler integration.

### Claude's Discretion

- Exact function signatures in `run_audit.py`
- Internal module structure (single file vs split into detection.py, output.py)
- ClickUp API error handling details (retry policy, timeout)
- Exact DAX query for historical batch (column selection, ORDER BY)
- Pydantic models for audit output rows (follow FeeRow pattern from explore_fees.py)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Foundations
- `.planning/PROJECT.md` — Core constraints, stack, ClickUp output format, token budget rules
- `.planning/REQUIREMENTS.md` — DETECT-02, DETECT-03, OUT-01, OUT-02, OUT-03, ESC-01 (all Phase 2 requirements)
- `.planning/ROADMAP.md` — Phase 2 success criteria (5 measurable outcomes)
- `.planning/STATE.md` — Key decisions, open questions, known pitfalls from Phase 1

### Phase 1 Artifacts
- `.planning/phases/01-data-foundation/01-CONTEXT.md` — D-01 through D-22: all Phase 1 locked decisions (data source, auth, schema, state persistence)
- `explore_fees.py` — Phase 1 output: reusable functions (`get_token`, `run_dax`, `validate_value_count`, `process_pbi_rows`, `build_output_df`, `iso_to_week_start`, `FeeRow`, `WORKSPACE_ID`, `DATASET_ID`). Read before planning any DAX or auth tasks.

### Research
- `.planning/research/STACK.md` — Approved library stack and rationale
- `.planning/research/ARCHITECTURE.md` — Component boundaries, data flow, anti-patterns
- `.planning/research/PITFALLS.md` — Token budget, uncalibrated threshold, LLM hallucination mitigations

### Power BI Model
- `fact_fee_preview` table: `key_sales_marketplace_sku`, `date_fee_preview`, `expected_fulfillment_fee_per_unit`, `is_latest`, `currency`
- `SKUs` table: `Key Column: Country | SKU`, `SKU`, `ASIN`, `Sales Region`
- Workspace ID: `47144ee2-02f9-4408-9ed5-57acf6a9f44d` | Dataset ID: `a95798aa-a3ec-4a89-9816-63cde534cdd7`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets from explore_fees.py
- `get_token()` — MSAL device-code auth with token cache. Use verbatim.
- `run_dax(dax, token)` — PBI executeQueries wrapper. Handles soft errors, timeout=120s.
- `validate_value_count(n_keys, n_weeks, n_cols)` — Pre-query guard for 1M PBI limit. MUST call before any historical batch query.
- `process_pbi_rows(rows)` — Strips PBI bracket column names, derives YEAR/WEEKNUM/week_start_date from date_fee_preview.
- `build_output_df(fee_df, sku_df)` — Left-join fee to SKU dimension; preserves amzn.gr.* keys with NaN for sku/asin.
- `iso_to_week_start(year, week)` — Returns Monday Timestamp for ISO year+week. Handles week 53 edge case.
- `FeeRow` (Pydantic v2) — D-11 schema. Extend or create `AnomalyRow` for Phase 2 output.
- `WORKSPACE_ID`, `DATASET_ID`, `SCOPES`, `CACHE_PATH`, `COUNTRY_CURRENCY` — All reusable constants.

### Established Patterns
- DAX groupBy constraint: `SUMMARIZECOLUMNS` requires real column references (not `YEAR()` or `WEEKNUM()` expressions). Derive year/week in Python via `isocalendar()`.
- PBI value limit: 1M values per query (rows × cols). With 5,274 total keys, a 16-week all-keys query = ~1.77M values → must batch by country.
- `amzn.gr.*` keys: preserved in output with NaN for sku/asin. Anomaly detection runs on them too.
- Snapshot schema: see `anomaly_history.csv` schema comment in explore_fees.py (line 424-428).

### Integration Points
- `run_audit.py` imports from `explore_fees.py` — Phase 2 must not break Phase 1 imports.
- `snapshots/` directory: create with same `.gitkeep` pattern as `output/` (snapshots are local state, git-ignored).
- `audit_config.json`: new file at project root. Must be git-tracked (contains thresholds, not secrets).

</code_context>

<specifics>
## Specific Ideas

- The `anomaly_history.csv` schema was pre-designed in Phase 1 (explore_fees.py line 424-428) — use it as-is.
- `audit_config.json` default values: `{"THRESHOLD_PCT": 15, "CLICKUP_TASK_ID": "PLACEHOLDER", "RECIPIENTS": [], "SUSTAINED_SHIFT_N": 4}`.
- ClickUp comment ends with the literal text: `"Reply YES to this comment to open an investigation task for the top flagged SKUs."`
- Claude receives anomaly JSON summary (not raw rows). Format: `{"run_date": "...", "total_scanned": N, "fee_increases": [{"sku": "...", "deviation_pct": X, ...}], "fee_reductions": [...]}`.
- Historical batch query: one `run_dax()` call per country code (9 calls + 1 for amzn.gr.*). Filter `fact_fee_preview` by country prefix in DAX using `FILTER` on `key_sales_marketplace_sku`.
- The attached CSV must include ALL anomalies (both increases and decreases, including sustained-shift rows flagged). Sustained-shift rows have `sustained_shift: true`.

</specifics>

<deferred>
## Deferred Ideas

- **Dual-gate threshold** (`pct AND absolute dollar floor` — DETECT-04) — v2 scope. Phase 2 uses pct-only.
- **Seasonal Q4 baseline buckets** (DETECT-05) — v2 scope.
- **CLI `--trigger manual` flag** — Phase 3 scope (EXEC-02). Phase 2 script runs with no arguments.
- **n8n scheduling** — Phase 3 scope (EXEC-01).
- **Victor notification routing** — deferred until system is validated by Lucca. Add to `RECIPIENTS` in audit_config.json when ready.
- **`amzn.gr.*` key investigation** — understanding what these represent (bundles? virtual ASINs?). Deferred from Phase 1; still deferred. Phase 2 includes them in anomaly detection but doesn't investigate their nature.
- **BigQuery run log** (REL-01) — v2 scope. Phase 2 logs to stdout + anomaly_history.csv only.

</deferred>

---

*Phase: 2-Detection-Output-Pipeline*
*Context gathered: 2026-05-28*
