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

- **D-01:** ~~Historical DAX batch on first run~~ → **SUPERSEDED by D-24 + D-25**. Historical batch approach abandoned: `fact_fee_preview` historical data is near-daily (not sparse), causing 15MB+ byte limit violations for US. Snapshot accumulation is kept as secondary mechanism for time-series tracking only.
- **D-02:** ~~Historical batching by country~~ → **SUPERSEDED**. See D-24 for new data acquisition strategy.
- **D-03:** ~~16-week lookback~~ → **SUPERSEDED**. No historical batch needed; 11B expected fee serves as baseline from day one.
- **D-04:** Snapshot storage = **one CSV per run date**: `snapshots/snapshot_YYYYMMDD.csv`. Kept for time-series audit trail. Not used as detection baseline.
- **D-05:** ~~Rolling 8-week median~~ → **SUPERSEDED by D-25**. Rolling median replaced by 11B expected fee comparison as primary detection method.
- **D-06:** ~~Sparse history warning~~ → **SUPERSEDED**. No longer relevant since D-25 uses a static expected fee baseline.

### Anomaly Detection

- **D-07:** ~~15% rolling median threshold~~ → **SUPERSEDED by D-26**. Threshold now applied to absolute overcharge vs `$_unit_last_fba_fee_calculation_expected`.
- **D-08:** Config file = **`audit_config.json`** in project root. Contains: `CLICKUP_TASK_ID`, `RECIPIENTS`, `BACKLOG_WEIGHT`, `MONTHLY_CASE_LIMIT`, `FNSKU_CAP_DAYS`. Updated schema — `THRESHOLD_PCT` and `SUSTAINED_SHIFT_N` removed. Tracked in git (no secrets).
- **D-09:** ~~Increases prominent, decreases informational~~ → **SUPERSEDED by D-31**. Output now organized by Sales Region, not by direction.
- **D-10:** Detection grain = **per `key_sales_marketplace_sku`** (country-level). Unchanged.

### Sustained-Shift Detection (DETECT-03)

- **D-11:** Sustained-shift threshold = **4 consecutive weeks** flagged in the same direction → SKU is reclassified as "sustained shift". Value is stored in `audit_config.json` as `SUSTAINED_SHIFT_N` (default: 4).
- **D-12:** Sustained-shift state storage = **`anomaly_history.csv`** (cumulative append). Schema from explore_fees.py comment (line 424-428): `key_sales_marketplace_sku`, `country`, `sku`, `asin`, `sales_region`, `week_start_date`, `avg_fee_per_unit`, `baseline_median_fee_per_unit`, `deviation_pct`, `direction`, `consecutive_weeks_flagged`, `run_date`. Each run appends new flagged rows; consecutive count is looked up from prior rows for same SKU+direction.
- **D-13:** Sustained-shift behavior = **excluded from ClickUp comment** (not in summary, not in escalation prompt), but **included in attached CSV** with a `sustained_shift: true` flag column. Human can review in CSV if needed. No second section in the comment for sustained shifts.

### ClickUp Output

- **D-14:** ClickUp task ID = **placeholder in `audit_config.json`** (`CLICKUP_TASK_ID: "PLACEHOLDER"`). Developer sets real task ID before first run.
- **D-15:** ~~Claude summary covering increases/decreases~~ → **SUPERSEDED by D-31**. ClickUp comment now has **4 per-region tables** (US, CA, GB, EU) each with top-N SKUs ranked by priority score.
- **D-16:** Escalation prompt (ESC-01) = plain text at end of comment: `"Reply YES to this comment to open an investigation task for the top flagged SKUs."` Unchanged.
- **D-17:** ClickUp recipients = **no notifications during testing** (`RECIPIENTS: []`). Unchanged.
- **D-18:** CSV attachment (OUT-02) = full anomaly list. Updated columns: `key_sales_marketplace_sku`, `country`, `sales_region`, `sku`, `asin`, `fee_preview_current`, `fee_11b_expected`, `overcharge_per_unit`, `velocity_w3`, `impact_4w`, `priority_score`, `consecutive_weeks_flagged`, `days_since_last_case`, `eligible_for_case`, `run_date`.

### Claude Narrative

- **D-19:** Claude is **narrative layer only** — all math (baseline, deviation, classification) in Python. Claude receives a structured JSON summary of anomalies, never raw fee tables.
- **D-20:** Claude invocation = direct Anthropic SDK call (`claude-sonnet-4-6`). No LangChain or agent frameworks. Single call with a concise prompt containing the anomaly JSON summary. Token budget: keep context under 4K tokens (anomaly JSON + system prompt).
- **D-21:** Claude output constraint = ≤150 words for the ClickUp comment body. Claude must produce text that is copy-paste ready for the comment — no post-processing needed.

### Script Structure

- **D-22:** Phase 2 produces **`run_audit.py`** — a new script that imports and reuses `get_token()`, `run_dax()`, `validate_value_count()`, `process_pbi_rows()`, `build_output_df()`, and `iso_to_week_start()` from `explore_fees.py`. No code duplication.
- **D-23:** Entry points: `python run_audit.py` (full audit run). Phase 3 will add `--trigger manual` flag and Windows Task Scheduler integration.

### SKU Validity Filter (NEW — from exploration session 2026-05-28)

- **D-24:** Active SKU filter = **3-part filter** applied before any anomaly detection. All three conditions must be met:
  1. `SKUs[status] = "Active"` — from `fAllListingsReport` merged into SKUs table via `key_country_sku`
  2. `SKUs[Life Cycle] NOT IN ("C", "D")` — Cancelled and Discontinued excluded; M, R, P allowed
  3. Inventory Ledger: `qty_sellable > 0` AND `max(Date) >= today - 90 days` (country-level, not EU-region aggregate) — uses raw `Inventory Ledger[Key Column: Country | SKU]` to avoid EU region inventory bleed-through
- **D-24a:** Two separate PBI queries + Python join:
  - Query A: `SUMMARIZECOLUMNS('SKUs'[Key Column: Country | SKU], 'SKUs'[Life Cycle], 'SKUs'[status])` filtered to Active + valid lifecycle
  - Query B: `SUMMARIZECOLUMNS('Inventory Ledger'[Key Column: Country | SKU], "max_date", MAX(...), "qty_sellable", ...)` filtered to qty > 0
  - Python: inner join of A and B, then filter `max_date >= today - 90 days`
- **D-24b:** Result is ~484 valid SKUs (validated in exploration). Much smaller than 5,274 raw fee preview keys.

### Fee Baseline — 11B Expected (NEW — replaces D-05)

- **D-25:** Detection baseline = **`$_unit_last_fba_fee_calculation_expected`** (PBI measure). Source: `fact_fba_fee_expected` table (standalone Excel: `standalone_files/db_fba_fee_expected.xlsx`). This is the fee we calculate Amazon SHOULD charge based on our own dimensional measurements. Uses `ALL('Calendar'[Date])` internally so no date filter needed.
- **D-26:** Overcharge metric = `fee_preview_current - fee_11b_expected`. Positive = Amazon is overcharging. Only positive overcharges are actioned. Negative overcharges (Amazon charging less than expected) logged to CSV but not alerted.
- **D-26a:** `fee_preview_current` = `$_unit_last_fba_fee_fee_preview` (PBI measure). Uses `MAX('fact_fee_preview'[date_fee_preview])` context.
- **D-26b:** Data query: single `SUMMARIZECOLUMNS` call grouped by `SKUs[Key Column: Country | SKU]` with both measures + `m_sold_prev3` + `'SKUs'[Native Family]` + `'SKUs'[Sales Region]` + `'SKUs'[Country]`.

### Prioritization Engine (NEW)

- **D-27:** Impact score = `overcharge_per_unit × m_sold_prev3 × 4` — dollar overcharge over next 4 weeks at current velocity. `m_sold_prev3` = average weekly units sold over last 3 weeks (PBI measure from `Measurement Table`).
- **D-28:** Priority score = `impact_4w × (1 + consecutive_weeks_flagged × 0.2)`. Weight 0.2 per week of backlog. First run: `consecutive_weeks_flagged = 0` for all SKUs.
- **D-29:** Remeasurement slot limits per Sales Region per calendar month (resets on 1st):
  - US: 10 cases/month
  - CA: 10 cases/month
  - GB: 10 cases/month
  - EU: 10 cases/month
- **D-30:** FNSKU cap = **< 2 cases closed per SKU in last 60 days**. Source: `standalone_files/db_amazon_remeasurement_cases.csv`. Uses `Date Closed` column (not `Date Created`). Also uses `Date Closed` for monthly slot count.
- **D-30a:** Cases CSV schema: `Region`, `SKU`, `ASIN`, `FNSKU`, `Case ID`, `Date Created`, `Date Closed`, `Status`, `Outcome`, `Refunded Amount`, `Currency`, `Lead Time`. `Region` maps directly to Sales Region (US/CA/GB/EU). Encoding: latin-1.
- **D-30b:** `slots_remaining[region] = 10 - COUNT(Date Closed in [month_start, today] WHERE Region = region)`
- **D-30c:** `sku_eligible = COUNT(Date Closed in [today-60, today] WHERE SKU = sku) < 2`

### ClickUp Output Structure (NEW — supersedes D-15)

- **D-31:** ClickUp comment has **4 sections, one per active Sales Region** (US, CA, GB, EU). Each section is a ranked table of up to 10 SKUs with columns: Rank, SKU, Country (EU only), Velocity/week, +$/unit overcharge, Impact/4wk, Days since last case.
- **D-31a:** Sections that have 0 eligible anomalies this run are omitted from comment.
- **D-31b:** Claude generates **one-paragraph summary per region** (≤50 words each), not a single 150-word summary. Total comment ≤ 300 words + 4 tables.
- **D-31c:** Watchlist (beyond top 10 per region) goes in CSV attachment only — not in ClickUp comment.
- **D-32:** EU section includes `Country` column to distinguish DE/FR/ES/IT/PL/etc. Other regions do not (single country per region).

### Claude's Discretion

- Exact function signatures in `run_audit.py`
- Internal module structure (single file vs split into detection.py, output.py)
- ClickUp API error handling details (retry policy, timeout)
- Pydantic models for audit output rows (follow FeeRow pattern from explore_fees.py)
- Exact SUMMARIZECOLUMNS DAX for combined fee + velocity + 11B expected query

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
- `audit_config.json` updated default values: `{"CLICKUP_TASK_ID": "PLACEHOLDER", "RECIPIENTS": [], "BACKLOG_WEIGHT": 0.2, "MONTHLY_CASE_LIMIT": 10, "FNSKU_CAP_DAYS": 60}`.
- ClickUp comment ends with: `"Reply YES to this comment to open an investigation task for the top flagged SKUs."`
- Claude receives one anomaly JSON per region: `{"region": "US", "run_date": "...", "slots_used": 10, "top_skus": [{"sku": "...", "country": "US", "overcharge": 0.51, "impact_4w": 375, "velocity_w3": 184, "days_since_case": 29}]}`.
- Cases CSV path: `standalone_files/db_amazon_remeasurement_cases.csv` (encoding: latin-1). Date columns use `dayfirst=True` parsing.
- Valid SKUs query uses 2 separate PBI DAX calls + Python join (D-24a). Not a single all-in-one DAX.
- `consecutive_weeks_flagged` in `anomaly_history.csv` serves double duty: (1) sustained-shift detection, (2) backlog weight multiplier in priority score.
- Validated data (2026-05-28): ~484 valid SKUs after triple filter, 188 with positive overcharge and velocity > 0, top impact $375/4wk (US-OHFB-3VH-1511L-GYOW).

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
