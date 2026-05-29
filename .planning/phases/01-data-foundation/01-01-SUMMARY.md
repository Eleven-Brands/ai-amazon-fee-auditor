---
phase: 01-data-foundation
plan: "01"
subsystem: scaffold
tags: [scaffold, pytest, tdd, gitignore, dependencies]
dependency_graph:
  requires: []
  provides: [test-harness, dependency-manifest, credential-template, git-safety]
  affects: [tests/test_aggregation.py, explore_fees.py (Wave 2)]
tech_stack:
  added: [pytest==9.0.3, msal==1.36.0, requests==2.32.3, pandas==2.2.3, numpy==2.2.4, python-dotenv==1.0.1, pydantic==2.13.4]
  patterns: [TDD RED phase, pytest fixtures, output/ gitkeep pattern]
key_files:
  created:
    - .gitignore
    - .env.example
    - requirements.txt
    - pytest.ini
    - output/.gitkeep
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_aggregation.py
  modified: []
decisions:
  - "output/* with !output/.gitkeep pattern used (not bare output/) to track empty directory while ignoring CSV contents"
  - "8 tests use natural ImportError red state — no @pytest.mark.skip or xfail decorators"
  - "conftest.py fixtures model PBI fully-qualified column name format (fact_fee_preview[col]) matching live API response"
metrics:
  duration: "~2 minutes"
  completed: "2026-05-27"
  tasks_completed: 2
  tasks_total: 2
  files_created: 8
  files_modified: 0
---

# Phase 01 Plan 01: Project Scaffold and Test Harness Summary

**One-liner:** pytest harness with 8 RED unit tests covering DATA-01/DATA-02/DETECT-01, pinned requirements, and .env/.gitignore safety net.

---

## What Was Built

A complete project scaffold with no production code. Wave 2 will implement `explore_fees.py` to turn all 8 tests GREEN.

### Task 1: Project Scaffold Files

| File | Purpose |
|------|---------|
| `.gitignore` | Excludes `.env`, `output/*`, `__pycache__/`, `*.pyc`, `*.csv`, `*.egg-info/`, `.pytest_cache/`, `dist/` |
| `.env.example` | Credential template: `POWERBI_TENANT_ID=`, `POWERBI_CLIENT_ID=`, `ANTHROPIC_API_KEY=` (Phase 2) |
| `requirements.txt` | 7 packages pinned with `==`: msal, requests, pandas, numpy, python-dotenv, pydantic, pytest |
| `pytest.ini` | `testpaths = tests`, `addopts = -q` |
| `output/.gitkeep` | Creates tracked `output/` directory; CSV contents remain git-ignored via `output/*` pattern |

Security: `.env` is gitignored (T-01-01 mitigated). Verified with `git check-ignore .env`.

### Task 2: Test Fixtures and 8 Unit Tests

**tests/conftest.py** — Two fixtures:
- `sample_pbi_rows`: 4 rows, 2 keys (`US | US-OHFB-001` and `amzn.gr.ABCD1234`), ISO year 2026 weeks 1-2, using PBI fully-qualified column name format
- `sample_sku_rows`: 1 joinable SKU row; `amzn.gr.*` key deliberately absent to test left-join behavior

**tests/test_aggregation.py** — 8 test functions (all RED, ImportError):

| Test | Requirement | What It Validates |
|------|-------------|-------------------|
| `test_run_dax_returns_expected_shape` | DATA-01 | run_dax returns non-empty list[dict]; HTTP mocked |
| `test_weekly_avg_calculation` | DATA-01 | Column rename + float dtype; two rows preserved per key |
| `test_value_count_within_limit` | DATA-01 | 5274×16×5 < 1M passes; 10000×16×10 raises ValueError |
| `test_country_extraction` | DATA-02 | 2-letter country prefix parsed from key_sales_marketplace_sku |
| `test_currency_mapping_completeness` | DATA-02 | US/CA/GB/MX/DE/FR/ES/IT mapped; ZZ → UNKNOWN |
| `test_amzn_gr_keys_preserved` | DETECT-01 | All 3 rows in output; amzn.gr.* has NaN asin+sku |
| `test_csv_schema_columns` | DETECT-01 | All 8 D-11 columns present in build_output_df output |
| `test_week_start_is_monday` | DETECT-01 | iso_to_week_start returns Monday; week 53 boundary OK |

---

## Commits

| Task | Hash | Message |
|------|------|---------|
| 1 — Scaffold | `0939150` | chore(01-01): project scaffold — .gitignore, .env.example, requirements.txt, pytest.ini, output/ |
| 2 — Tests | `0d644ac` | test(01-01): 8 unit tests (RED) + conftest fixtures for explore_fees |

---

## Verification Results

| Check | Result |
|-------|--------|
| `git check-ignore .env` | `.env` — PASS |
| `git check-ignore output/explore_fees_20260527.csv` | path printed — PASS |
| `grep msal requirements.txt` | `msal==1.36.0` — PASS |
| `grep testpaths pytest.ini` | `testpaths = tests` — PASS |
| `pytest tests/ -x -q` | ERROR: ModuleNotFoundError (expected RED state) — PASS |
| 8 test functions in test_aggregation.py | Confirmed via grep — PASS |

---

## Deviations from Plan

None — plan executed exactly as written.

The `.gitignore` uses `output/*` with `!output/.gitkeep` (as specified in context instructions) rather than a bare `output/` entry, which correctly tracks the `.gitkeep` sentinel while ignoring all other output directory contents.

---

## Known Stubs

None. This plan creates no production code. The import stub (`from explore_fees import ...`) is intentional — it is the TDD RED signal, not a stub to be tracked.

---

## Threat Flags

No new threat surface introduced. T-01-01 (`.env` disclosure) is mitigated by `.gitignore` entry, verified with `git check-ignore`.

---

## Self-Check: PASSED

- [x] `.gitignore` exists and contains `.env`
- [x] `.env.example` exists and contains `POWERBI_TENANT_ID=`
- [x] `requirements.txt` exists and contains `msal==1.36.0`
- [x] `pytest.ini` exists and contains `testpaths = tests`
- [x] `output/.gitkeep` exists
- [x] `tests/__init__.py` exists
- [x] `tests/conftest.py` exists and contains `sample_pbi_rows`
- [x] `tests/test_aggregation.py` exists and contains `test_weekly_avg_calculation`
- [x] Commit `0939150` exists (Task 1)
- [x] Commit `0d644ac` exists (Task 2)
