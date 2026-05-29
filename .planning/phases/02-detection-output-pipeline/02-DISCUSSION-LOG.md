# Phase 2: Detection + Output Pipeline - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-28
**Phase:** 02-detection-output-pipeline
**Areas discussed:** Baseline bootstrap, Threshold & detection rules, ClickUp setup, Sustained-shift detection

---

## Baseline Bootstrap

| Option | Description | Selected |
|--------|-------------|----------|
| Accumulate silently | Run weekly, no alerts until N >= 4 snapshots | |
| Alert from snapshot 2 | Alert from second week onwards with thin baseline | |
| Bootstrap from historical DAX | Batch-query fact_fee_preview without is_latest filter | ✓ |

**User's choice:** Bootstrap from historical DAX

**Follow-up — Lookback window:**

| Option | Description | Selected |
|--------|-------------|----------|
| 8 weeks | Minimum for rolling median | |
| 16 weeks | More robust, still within PBI limits with batching | ✓ |
| Configurable only | No default, must set LOOKBACK_WEEKS before running | |

**User's choice:** 16 weeks

**Follow-up — Snapshot storage:**

| Option | Description | Selected |
|--------|-------------|----------|
| One CSV per run date in snapshots/ | snapshots/snapshot_YYYYMMDD.csv per run | ✓ |
| Single cumulative snapshots.csv | Append all rows to one file | |
| Separate baseline.csv + weekly files | Two tiers of files | |

**User's choice:** One CSV per run date

**Follow-up — Batch strategy:**

| Option | Description | Selected |
|--------|-------------|----------|
| By country code | 9 batches (US, CA, GB, DE, FR, ES, IT, MX, BE) | ✓ |
| By Sales Region | 5 batches (US, CA, UK, MX, EU) | |
| Single query with date filter | All keys, one query — known to exceed 1M limit | |

**User's choice:** By country code

---

## Threshold & Detection Rules

| Option | Description | Selected |
|--------|-------------|----------|
| 15% hardcoded to start | Middle of 10-20% expected range | ✓ |
| 10% hardcoded to start | More sensitive, likely more false positives early | |
| Config file only, no hardcode | Must be set before first run | |

**User's choice:** 15% hardcoded as default in audit_config.json

**Follow-up — Config location:**

| Option | Description | Selected |
|--------|-------------|----------|
| audit_config.json in project root | Single place for THRESHOLD_PCT, CLICKUP_TASK_ID, RECIPIENTS, SUSTAINED_SHIFT_N | ✓ |
| .env only | Alongside API keys, not git-tracked | |
| Both config.json (thresholds) and .env (secrets) | Clean separation | |

**User's choice:** audit_config.json (single config file for all calibration knobs)

**Follow-up — Direction handling:**

| Option | Description | Selected |
|--------|-------------|----------|
| Flag both directions, label them | Both in output, labeled up/down | |
| Flag increases only | Decreases never investigated | |
| Flag increases prominently, decreases as info | Two sections in comment; both in CSV | ✓ |

**User's choice:** Flag increases prominently, decreases as informational (two sections in ClickUp comment)

---

## ClickUp Setup

| Option | Description | Selected |
|--------|-------------|----------|
| Provide task ID now | Lock real task ID in CONTEXT.md | |
| Use a placeholder | Hardcode PLACEHOLDER, configure before first run | ✓ |
| Create a dedicated task | Create new ClickUp task via MCP | |

**User's choice:** Placeholder — developer sets real task ID before first run

**Follow-up — Escalation prompt:**

| Option | Description | Selected |
|--------|-------------|----------|
| Simple yes/no ask | "Reply YES to open investigation task" | ✓ |
| Named-SKU prompt | List top 3-5 SKUs by deviation % | |
| Checkbox-style in comment | ClickUp checklist items per flagged SKU | |

**User's choice:** Simple yes/no: "Reply YES to this comment to open an investigation task for the top flagged SKUs."

**Follow-up — Recipients:**

| Option | Description | Selected |
|--------|-------------|----------|
| Lucca only for now | Testing phase, Victor added when validated | |
| Lucca + Victor from day 1 | Both receive every notification | |
| No notifications until calibrated | Post comment, don't tag anyone yet | ✓ |

**User's choice:** No notifications until calibrated (RECIPIENTS: [] in audit_config.json)

---

## Sustained-Shift Detection (DETECT-03)

| Option | Description | Selected |
|--------|-------------|----------|
| 3 consecutive weeks | Faster reclassification | |
| 4 consecutive weeks | One month before silencing — more conservative | ✓ |
| Configurable only, no default | Must be set before running | |

**User's choice:** 4 consecutive weeks (SUSTAINED_SHIFT_N: 4 in audit_config.json)

**Follow-up — State tracking:**

| Option | Description | Selected |
|--------|-------------|----------|
| anomaly_history.csv with consecutive_weeks_flagged | Cumulative append; schema pre-designed in explore_fees.py | ✓ |
| Separate sustained_shifts.csv | Dedicated suppression list | |
| Both files (raw log + active suppression) | Most complete but more files to manage | |

**User's choice:** anomaly_history.csv (single cumulative file with consecutive_weeks_flagged column)

**Follow-up — Behavior when classified:**

| Option | Description | Selected |
|--------|-------------|----------|
| Remove from active alerts, still in CSV | Excluded from comment; in CSV with sustained_shift flag | ✓ |
| Remove completely from output | Clean comment but no visibility into ongoing changes | |
| Separate section in ClickUp comment | "Sustained shifts not re-alerting (M SKUs)" | |

**User's choice:** Excluded from ClickUp comment, included in attached CSV with sustained_shift: true flag

---

## Claude's Discretion

- Internal module structure of run_audit.py (single file vs split into detection.py, output.py)
- Exact function signatures
- ClickUp API error handling details (retry policy, timeout)
- Exact DAX query structure for historical batch queries
- Pydantic models for audit output rows (extend FeeRow or create AnomalyRow)

## Deferred Ideas

- Dual-gate threshold (pct AND absolute dollar floor) — DETECT-04, v2 scope
- Seasonal Q4 baseline buckets — DETECT-05, v2 scope
- CLI `--trigger manual` flag — Phase 3 (EXEC-02)
- n8n scheduling — Phase 3 (EXEC-01)
- Victor notification routing — deferred until system validated by Lucca
- amzn.gr.* key investigation (what they represent) — ongoing deferral from Phase 1
- BigQuery run log (REL-01) — v2 scope
