---
phase: 1
slug: data-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-27
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pytest.ini` — Wave 0 creates it |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| run_dax shape | 01 | 1 | DATA-01 | — | HTTP 200 with soft-error check: `result["error"]` must be inspected, not just `raise_for_status()` | unit (mock HTTP) | `pytest tests/test_aggregation.py::test_run_dax_returns_expected_shape -x` | ❌ W0 | ⬜ pending |
| weekly avg calc | 01 | 1 | DATA-01 | — | N/A | unit | `pytest tests/test_aggregation.py::test_weekly_avg_calculation -x` | ❌ W0 | ⬜ pending |
| value count math | 01 | 1 | DATA-01 | — | Query must abort before execution if value count > 1,000,000 | unit | `pytest tests/test_aggregation.py::test_value_count_within_limit -x` | ❌ W0 | ⬜ pending |
| country extraction | 01 | 1 | DATA-02 | — | N/A | unit | `pytest tests/test_aggregation.py::test_country_extraction -x` | ❌ W0 | ⬜ pending |
| currency mapping | 01 | 1 | DATA-02 | — | N/A | unit | `pytest tests/test_aggregation.py::test_currency_mapping_completeness -x` | ❌ W0 | ⬜ pending |
| amzn.gr.* handling | 01 | 1 | DETECT-01 | — | Unjoined keys preserved in output with null asin/sku fields | unit | `pytest tests/test_aggregation.py::test_amzn_gr_keys_preserved -x` | ❌ W0 | ⬜ pending |
| CSV schema | 01 | 1 | DETECT-01 | — | All D-11 columns present | unit | `pytest tests/test_aggregation.py::test_csv_schema_columns -x` | ❌ W0 | ⬜ pending |
| week_start Monday | 01 | 1 | DETECT-01 | — | N/A | unit | `pytest tests/test_aggregation.py::test_week_start_is_monday -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/__init__.py` — marks tests directory as package
- [ ] `tests/conftest.py` — fixtures: sample daily rows mimicking PBI API JSON response; sample expected output CSV rows
- [ ] `tests/test_aggregation.py` — all 8 test cases mapped above
- [ ] `pytest.ini` — minimal config: `testpaths = tests`, `addopts = -q`
- [ ] `.env.example` — template with `POWERBI_TENANT_ID=` and `POWERBI_CLIENT_ID=` placeholders
- [ ] `.gitignore` — `.env`, `output/`, `__pycache__/`, `*.csv`, `*.pyc`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live PBI query returns non-empty fee data | DATA-01 | Requires live Power BI credentials and network access | Run `python explore_fees.py` and verify CSV has ≥ 4 weeks of data for at least 1 SKU |
| 16-week history present in output CSV | DATA-01 | Depends on live PBI data availability | Inspect `output/explore_fees_YYYYMMDD.csv` — confirm `week_start_date` spans ≥ 16 distinct weeks |
| `amzn.gr.*` unjoined count logged to stdout | DETECT-01 | Output is a print statement, not a test assertion | Run script and verify log line: `"Unjoined keys (amzn.gr.*): N"` where N > 0 |
| Token cache file permissions | Security | ACL check requires OS-level inspection | Verify `~/.claude/powerbi_token_cache.json` is readable only by current user (Windows: check Security tab, no other users listed) |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
