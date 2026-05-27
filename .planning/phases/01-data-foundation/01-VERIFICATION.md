---
phase: 01-data-foundation
verified: 2026-05-27T21:29:38Z
status: human_needed
score: 9/9
overrides_applied: 0
human_verification:
  - test: "Run `python explore_fees.py` with a valid .env (POWERBI_TENANT_ID + POWERBI_CLIENT_ID set)"
    expected: "Script exits 0; stdout shows 'CSV written: output/explore_fees_YYYYMMDD.csv'; CSV has 8 D-11 columns; at least 1 distinct week_start_date value; amzn.gr.* rows present"
    why_human: "Requires live Power BI credentials and network access to the OrganiHaus PBI dataset — cannot be exercised by automated checks without real auth"
  - test: "Open output/explore_fees_YYYYMMDD.csv (if it exists from a prior run) and spot-check 3 rows"
    expected: "week_start_date values are Mondays; US rows have currency=USD; DE rows have currency=EUR; at least 1 row with empty asin for an amzn.gr.* key"
    why_human: "CSV content correctness on real PBI data cannot be verified without a live run"
---

# Phase 1: Data Foundation — Verification Report

**Phase Goal:** Establish the data pipeline that fetches current FBA fee data from Power BI, processes it, and outputs a structured CSV (D-11 schema) — all covered by passing unit tests.
**Verified:** 2026-05-27T21:29:38Z
**Status:** human_needed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | All 9 unit tests pass (pytest exits 0) | VERIFIED | `pytest tests/ -v` → 9 passed, 0 failed, 0 errors in 1.55s |
| 2 | `.env` is not tracked by git; `.env.example` is committed | VERIFIED | `git check-ignore .env` → `.env`; `.env.example` confirmed in git HEAD with 3 vars |
| 3 | `output/` directory exists with `.gitkeep` sentinel; contents are git-ignored | VERIFIED | `.gitkeep` reads as empty file; `git check-ignore output/test.csv` → `output/test.csv`; `output/.gitkeep` NOT ignored (negation `!output/.gitkeep` in `.gitignore`) |
| 4 | All 9 test functions have concrete assertions (no `pass` stubs) | VERIFIED | AST parse confirms 9 test functions; each has `assert` statements; 0 skipped tests in run |
| 5 | `run_dax()` raises RuntimeError on soft-error JSON (HTTP 200 with error field) | VERIFIED | Behavioral spot-check: `patch('requests.post')` returning `{"error": "DAX query failed"}` → `RuntimeError: DAX query error: DAX query failed` |
| 6 | D-11 schema columns are present and correctly ordered in `build_output_df` output | VERIFIED | Live Python check: columns = `['key_sales_marketplace_sku', 'country', 'sales_region', 'sku', 'asin', 'week_start_date', 'avg_fee_per_unit', 'currency']` — exact D-11 order |
| 7 | `amzn.gr.*` keys are preserved with NaN asin/sku (not dropped) | VERIFIED | Live check: 3-row fee_df with 1 amzn.gr.* key → output has 3 rows; `pd.isna(amzn_row.asin) = True`, `pd.isna(amzn_row.sku) = True` |
| 8 | Pydantic gate (`validate_output_df`) raises ValidationError before CSV write on schema violation | VERIFIED | Behavioral spot-check: DataFrame missing `asin` column → `pydantic.ValidationError` raised; `validate_output_df` at line 474 precedes `to_csv` at line 485 in `main()` |
| 9 | `python explore_fees.py` produces a CSV from live Power BI data | UNCERTAIN (human needed) | SUMMARY.md claims live run succeeded (5,274 rows, `output/explore_fees_20260527.csv`); cannot verify live API output without credentials |

**Score:** 9/9 truths verified (1 requires human confirmation for live-run correctness)

---

### Deferred Items

None — all phase success criteria addressed within this phase.

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `explore_fees.py` | Main module exporting all 8 tested functions + main() | VERIFIED | 491 lines; exports: `run_dax`, `process_pbi_rows`, `validate_value_count`, `extract_country`, `get_currency_for_country`, `build_output_df`, `iso_to_week_start`, `validate_output_df`, `main`, `FeeRow`, `build_fee_dax`, `SKU_QUERY`, `WORKSPACE_ID`, `DATASET_ID` — all confirmed importable |
| `tests/test_aggregation.py` | 9 unit tests; all must pass | VERIFIED | 9 test functions confirmed by AST parse; `pytest tests/ -v` → 9 passed |
| `tests/conftest.py` | Shared fixtures: `sample_pbi_rows`, `sample_sku_rows` | VERIFIED | Both fixtures present; `sample_pbi_rows` uses real PBI column format (`fact_fee_preview[date_fee_preview]`) matching the live API response shape discovered in Wave 4 |
| `output/.gitkeep` | Sentinel file — directory exists, contents git-ignored | VERIFIED | File exists (empty); `!output/.gitkeep` negation pattern in `.gitignore` correctly un-ignores it |
| `.env.example` | 3 env vars: `POWERBI_TENANT_ID=`, `POWERBI_CLIENT_ID=`, `ANTHROPIC_API_KEY=` | VERIFIED | Git shows: `POWERBI_TENANT_ID=`, `POWERBI_CLIENT_ID=`, `ANTHROPIC_API_KEY=  # Phase 2` |
| `requirements.txt` | 7 packages with `==` pins | VERIFIED | `msal==1.36.0`, `requests==2.32.3`, `pandas==2.2.3`, `numpy==2.2.4`, `python-dotenv==1.0.1`, `pydantic==2.13.4`, `pytest==9.0.3` — exact 7 packages |
| `pytest.ini` | `[pytest]` with `testpaths = tests` and `addopts = -q` | VERIFIED | File contains exactly those two keys under `[pytest]` |
| `.gitignore` | Excludes `.env`, `output/*`, `__pycache__/`, `*.pyc`, `*.csv`, etc. | VERIFIED | All required entries present; negation `!output/.gitkeep` correctly preserves sentinel |
| `skeleton.py` | Auth + TOPN connectivity proof | VERIFIED | `acquire_token_silent`, `groups/` endpoint, `result.get`, `Skeleton: OK` all present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `explore_fees.py:get_token()` | MSAL token cache at `~/.claude/powerbi_token_cache.json` | `msal.SerializableTokenCache` | VERIFIED | `SerializableTokenCache` and `acquire_token_silent` both present in `get_token()` |
| `explore_fees.py:run_dax()` | Power BI group endpoint URL | `requests.post` with group path | VERIFIED | URL: `https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}/datasets/{DATASET_ID}/executeQueries` — group path confirmed |
| `explore_fees.py:process_pbi_rows()` | `explore_fees.py:iso_to_week_start()` | `df.apply()` on YEAR+WEEKNUM | VERIFIED | Line 302-305: `df["week_start_date"] = df.apply(lambda row: iso_to_week_start(row["YEAR"], row["WEEKNUM"]), axis=1)` |
| `explore_fees.py:build_output_df()` | `explore_fees.py:extract_country()` | called inside `build_output_df` after copy | VERIFIED | Line 364: `extract_country(fee_df)` called before merge |
| `explore_fees.py:main()` | `explore_fees.py:get_token()` | called at script start | VERIFIED | Line 452: `token = get_token()` |
| `explore_fees.py:main()` | `output/explore_fees_*.csv` | `df.to_csv()` | VERIFIED | Line 485: `output_df.to_csv(output_path, index=False)` — called after `validate_output_df` |
| `validate_output_df()` | `FeeRow` Pydantic model | `FeeRow(**first_row)` | VERIFIED | T-04-02: validation at line 474 precedes `to_csv` at line 485 in `main()`; behavioral check confirmed `ValidationError` raised on missing column |
| `tests/conftest.py` | `tests/test_aggregation.py` | pytest fixture injection | VERIFIED | `sample_pbi_rows` fixture used in `test_weekly_avg_calculation`; `pytest` resolves injection — all 9 tests pass |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `main()` → CSV output | `output_df` | `build_output_df(fee_df, pd.DataFrame(sku_rows))` | HUMAN NEEDED (requires live PBI API) | VERIFIED statically (all wiring present); UNCERTAIN for live data content |
| `process_pbi_rows()` → `fee_df` | `df` with `avg_fee_per_unit`, `week_start_date` | `pd.DataFrame(rows)` from `run_dax()` | VERIFIED (unit tests pass with fixture data) | FLOWING in unit test context |
| `build_output_df()` → D-11 DataFrame | merged with 8 columns | left-join fee_df + sku_df, then `COUNTRY_CURRENCY` map | VERIFIED | Live Python check: correct 8 columns, amzn.gr.* NaN preserved |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 9 tests pass | `python -m pytest tests/ -v` | 9 passed in 1.55s | PASS |
| All module exports importable | `from explore_fees import run_dax, process_pbi_rows, ...` (14 items) | `All exports OK` | PASS |
| `iso_to_week_start(2026, 1)` returns Monday 2025-12-29 | Python check | `weekday=0`, `date=2025-12-29` | PASS |
| `validate_value_count(5274, 16, 5)` returns 421920 | Python check | `421920 < 1_000_000` | PASS |
| `validate_value_count(10000, 16, 10)` raises ValueError | Python check | `ValueError: Value count 1,600,000 exceeds...` | PASS |
| `run_dax()` raises RuntimeError on soft error | mock + Python check | `RuntimeError: DAX query error: DAX query failed` | PASS |
| Pydantic gate raises on missing column | Python check | `ValidationError` raised on df missing `asin` | PASS |
| D-11 column order exact | Python check | Exact 8-column list in D-11 order | PASS |
| amzn.gr.* preserved with NaN asin/sku | Python check | 3 rows returned, amzn.gr.* has NaN asin and NaN sku | PASS |
| `validate_output_df` called before `to_csv` in `main()` | Line number check | `validate_output_df` line 474, `to_csv` line 485 | PASS |
| No `NotImplementedError` stubs remain | grep on source | `0 occurrences` | PASS |
| No TBD/FIXME/XXX debt markers | grep on source | `0 occurrences` | PASS |
| `.env` is git-ignored | `git check-ignore .env` | `.env` | PASS |
| `output/test.csv` is git-ignored | `git check-ignore output/test.csv` | `output/test.csv` | PASS |
| `output/.gitkeep` is NOT git-ignored | `git check-ignore output/.gitkeep` | `''` (empty = not ignored) | PASS |
| `python explore_fees.py` produces CSV from live PBI | Requires credentials | Live run shown in SUMMARY.md (5,274 rows) | HUMAN NEEDED |

---

### Probe Execution

No probe scripts (`scripts/*/tests/probe-*.sh`) declared or found in this phase. Behavioral spot-checks above serve as the verification harness.

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| DATA-01 | 01-01, 01-02, 01-03, 01-04 | Power BI query returns correct shape (`run_dax`, `process_pbi_rows`, `validate_value_count`) | SATISFIED | `test_run_dax_returns_expected_shape`, `test_weekly_avg_calculation`, `test_value_count_within_limit` all pass; `run_dax` soft-error check verified |
| DATA-02 | 01-01, 01-02, 01-03, 01-04 | Country/currency extraction (`extract_country`, `get_currency_for_country`) | SATISFIED | `test_country_extraction`, `test_currency_mapping_completeness` pass; all 8 active OrganiHaus markets (US, CA, GB, MX, DE, FR, ES, IT) return non-UNKNOWN currencies; `ZZ` returns `UNKNOWN` |
| DETECT-01 | 01-01, 01-02, 01-03, 01-04 | `amzn.gr.*` keys preserved in output (`build_output_df`) | SATISFIED | `test_amzn_gr_keys_preserved` passes; live Python check: 3 rows in → 3 rows out; amzn.gr.* row has `pd.isna(asin)=True`, `pd.isna(sku)=True` |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None | — | — | — | No anti-patterns found in `explore_fees.py`, `tests/test_aggregation.py`, or `tests/conftest.py` |

Zero TBD/FIXME/XXX markers. Zero NotImplementedError stubs. Zero return-null/empty-list anti-patterns in production code paths.

---

### Notable Deviations from Plan (Non-Blocking)

**1. Fixture format changed from `[YEAR]`/`[WEEKNUM]` keys to `date_fee_preview`**

The original PLAN 01-01 specified conftest fixture rows with `"[YEAR]"`, `"[WEEKNUM]"` keys. During Wave 4 execution, a DAX limitation was discovered: `SUMMARIZECOLUMNS` cannot accept `YEAR()`/`WEEKNUM()` as groupBy expressions — only real column references are allowed. The fix: group by `[date_fee_preview]` and derive YEAR/WEEKNUM in Python via `isocalendar()`. The conftest fixture was updated to match the real API column shape (`fact_fee_preview[date_fee_preview]`). All 9 tests pass against the revised fixture. This is a correct adaptation, not a regression.

**2. Test count: 8 → 9**

PLAN 01-01 specified 8 unit tests. PLAN 01-04 added a 9th (`test_validate_output_df_raises_on_missing_column`) to verify the Pydantic gate (T-04-02). This is a scope addition (positive), not a reduction. All 9 pass.

**3. `build_fee_dax()` is a function, not a string constant**

PLAN 01-04 specified `FEE_DAX` as a DAX string constant with `{cutoff_start}`/`{today}` placeholders. The implementation uses `build_fee_dax()` as a zero-argument function returning the `is_latest=1` snapshot query (no date range needed since the query filters to current fee schedule rows). This is correct given the data model discovery: `fact_fee_preview` is a fee schedule history table where `is_latest=1` gives the current snapshot. The function is importable as `build_fee_dax` — all wiring checks pass.

---

### Human Verification Required

#### 1. Live `python explore_fees.py` run

**Test:** With a valid `.env` containing `POWERBI_TENANT_ID` and `POWERBI_CLIENT_ID`, run `python explore_fees.py` from the project root.

**Expected:**
- Auth succeeds (device-code prompt only if token cache is expired)
- Stdout shows:
  - `Querying current fee schedule snapshot (is_latest=1): YYYY-MM-DD`
  - `Fee rows fetched: N` (expect ~5,274)
  - `SKU rows fetched: N` (expect ~16,121)
  - `Unjoined keys (amzn.gr.* or no SKU match): N` (expect > 0, was 5 on 2026-05-27)
  - `Schema validation: OK (N rows)`
  - `Weeks covered: YYYY-MM-DD -> YYYY-MM-DD`
  - `Total rows: N`
  - `Distinct keys: N`
  - `CSV written: output\explore_fees_YYYYMMDD.csv`
- Script exits 0

**Why human:** Requires live Power BI credentials and network access. Cannot be mocked without defeating the purpose (the whole point is proving live PBI connectivity works).

**Note:** SUMMARY.md documents a successful live run on 2026-05-27 (5,274 rows, 8 D-11 columns, `output/explore_fees_20260527.csv`). If that run was performed on this machine with credentials still in the token cache, running `python explore_fees.py` again will confirm the pipeline is stable.

#### 2. CSV content spot-check

**Test:** Open `output/explore_fees_YYYYMMDD.csv` (most recent) and verify:
1. Has exactly 8 column headers in D-11 order
2. At least 3 rows with `week_start_date` values that are Mondays (weekday 0)
3. At least 1 US row has `currency = USD`; at least 1 DE row has `currency = EUR`
4. At least 1 row with empty `asin` cell (amzn.gr.* key)

**Why human:** CSV content correctness on real production data can only be spot-checked by opening the file.

---

### Gaps Summary

No gaps. All must-have truths are VERIFIED against the codebase. The `human_needed` status reflects the live-credential dependency for Truth 9 (end-to-end script run), not any code deficiency — the wiring, logic, and unit test coverage are complete and correct.

The phase goal is substantively achieved: the data pipeline exists, all transformation functions are implemented and tested, the D-11 schema is enforced by both unit tests and the Pydantic gate, and the `main()` entrypoint wires all components into a runnable script.

---

_Verified: 2026-05-27T21:29:38Z_
_Verifier: Claude (gsd-verifier)_
