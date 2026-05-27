# Architecture Patterns: AI Amazon Fee Auditor

**Domain:** AI agent system for data auditing / anomaly detection
**Researched:** 2026-05-27
**Confidence:** MEDIUM — external verification blocked; patterns drawn from established practices for this stack

---

## Recommended Architecture

### System Overview

```
n8n (scheduler/trigger)
        |
        | HTTP POST (webhook or direct Python invocation)
        v
[Fee Auditor Agent — Python orchestrator]
        |
    +-------+-------+
    |               |
    v               v
PowerBI          BigQuery
(raw query)      (state: baselines,
                  run log,
                  acknowledged anomalies)
        |
        v
[Statistical Engine — pure Python]
(baseline calc, anomaly detection, volume normalization)
        |
        v (anomaly list only — no raw rows)
[Claude claude-sonnet-4-6 — Narrative layer only]
(formats findings into human-readable ClickUp comment)
        |
        v
[ClickUp API]
(post comment + attach report file)
```

---

## Component Boundaries

| Component | Responsibility | Communicates With | Does NOT Own |
|---|---|---|---|
| n8n Workflow | Schedule trigger, retry, error alert, pass run metadata | Fee Auditor Agent (HTTP) | Business logic, data |
| Fee Auditor Agent (Python) | Orchestration: coordinates all components, owns run lifecycle | Power BI, BigQuery, Statistical Engine, Claude API, ClickUp API | Statistical math, narrative text |
| powerbi-query skill | Fetch FBA Fee + Storage Fee by SKU/ASIN for date range | Power BI data model | Anomaly logic |
| Statistical Engine (Python module) | Rolling baseline, deviation computation, anomaly flagging | Called by Fee Auditor Agent | Formatting, storage, API calls |
| BigQuery (state store) | Persist run log, anomaly archive, acknowledged anomalies | Written/read by Fee Auditor Agent | Business logic |
| Claude claude-sonnet-4-6 | Convert structured anomaly list into concise ClickUp comment | Called by Fee Auditor Agent after detection | Data fetching, math, decisions |
| ClickUp API | Receive comment + file attachment | Fee Auditor Agent | Everything else |

**Critical design principle:** Claude never sees raw data rows. It receives only a structured summary (JSON of flagged SKUs with deviation %, period, magnitude). Token budget is bounded this way.

---

## Data Flow Direction

```
TRIGGER
  n8n weekly cron OR manual HTTP trigger
      |
      v (HTTP POST: run_id, date_range, trigger_type)
INGEST
  powerbi-query skill → raw FBA Fee + Storage Fee rows (SKU, ASIN, fee_type, amount, period)
      |
      v
ENRICH
  BigQuery state read → load baselines per SKU (rolling median from prior N periods)
      |
      v
DETECT
  Statistical Engine → compare current fees to baseline → anomaly list
  [{sku, asin, fee_type, current_amount, baseline_amount, deviation_pct, severity}]
      |
      v (anomaly list only — no raw rows)
NARRATE
  Claude claude-sonnet-4-6 → produce concise ClickUp comment text + pattern observations
      |
      v
REPORT
  Generate detailed CSV report from anomaly list (pure Python, no AI)
      |
      v
OUTPUT
  ClickUp API: post comment, attach CSV report
      |
      v
PERSIST
  BigQuery: update run log, store anomaly archive, update baselines
```

**Rule:** Data only flows downstream. No component queries a component upstream of it. BigQuery is the only component accessed twice (read before detect, write after output).

---

## 1. Agent Orchestration Pattern

**Recommendation: Single orchestrator agent with tool-use (NOT multi-agent)**

Rationale:
- The task is a linear pipeline with a single decision point (anomaly threshold)
- Claude is used only for narrative generation — no planning or routing requiring a second agent
- Multi-agent introduces coordination overhead before complexity is proven necessary

**Decomposition triggers (when to split later):**
- Multiple marketplaces need independent parallel processing per run
- A separate "investigation agent" queries Seller Central to root-cause anomalies
- SKU count grows to thousands and batching requires parallel workers

**Pattern:** A single Python function `run_audit()` calls each step sequentially. Claude is invoked as a single API call, not as an agent with tools. The Python script IS the orchestrator.

---

## 2. Anomaly Detection: Statistical Logic vs AI Logic

**Firm rule: Statistical logic lives entirely in Python. Claude never does math.**

Statistical Engine (pure Python):
- Rolling baseline: compute **median** (not mean — more robust to outliers) of fee amounts per SKU over configurable lookback (default: 4 prior periods)
- Deviation calculation: `(current - baseline) / baseline * 100` as signed percentage
- Threshold comparison: flag if `|deviation_pct| > threshold_config`
- Severity tier: 10-25% = WARNING, 25-50% = ELEVATED, >50% = CRITICAL (calibrate after first run)
- New SKU handling: flag as `NEW_SKU` if fewer than N prior periods — no threshold applied

Claude's only role:
- **Input:** `{run_date, flagged_count, sku_anomalies: [{sku, deviation_pct, severity, fee_type}], clean_count}`
- **Output:** 3-5 sentence ClickUp comment + optional pattern observation
- Claude does NOT decide what is an anomaly. That decision is made by threshold config before Claude is called.

Why this separation:
- **Reproducibility:** same data → same anomaly flags regardless of LLM temperature
- **Auditability:** Lucca/Gustavo can inspect threshold logic without reasoning about Claude's output
- **Cost:** Claude called once per run with small payload, not per-SKU or per-row
- **Token constraint:** passing raw rows to Claude violates PROJECT.md "summaries and structured outputs only" rule

---

## 3. Data Ingestion: Power BI to Python

**Pattern: powerbi-query skill as abstraction**

Design:
- Fee Auditor Agent calls `powerbi-query` with explicit params: `{dataset, measures: ["FBA Fee", "Storage Fee"], dimensions: ["SKU", "ASIN", "Period"], date_range: {start, end}, marketplace: "US"}`
- Response: flat table (list of dicts or pandas DataFrame)
- Agent validates response schema before passing to Statistical Engine — fail fast if columns missing
- Power BI is read-only from this agent's perspective

**What to fetch per run:**
- Pull last N+1 periods from Power BI and recompute baseline locally each run
- Avoids baseline drift from stale BigQuery cache
- Performance cost acceptable at OrganiHaus SKU counts

**Fallback:** If Power BI query fails → log error, skip run, post ClickUp comment indicating missed run. Do not silently fail.

---

## 4. State Management: What to Persist Between Runs

**Store: BigQuery (already in stack)**

| Table | Key Columns | Purpose | Update Frequency |
|---|---|---|---|
| `fee_audit_runs` | run_id, trigger_type, run_date, status, anomaly_count, sku_count, error_message | Run log for debugging and trend | Every run |
| `fee_anomalies` | run_id, sku, asin, fee_type, period, current_amount, baseline_amount, deviation_pct, severity | Audit trail of all flagged anomalies | Every run |
| `fee_acknowledged` | sku, asin, fee_type, acknowledged_at, acknowledged_by, reason, expires_at | Suppress confirmed-expected anomalies | Written via manual entry; read at detect-time |

**For MVP:** Skip `fee_acknowledged` logic; just log all anomalies. Add suppression after team has seen real data.

**What NOT to persist:**
- Raw Power BI rows — query fresh each run
- Claude's narrative text — ClickUp comment is the record
- Threshold config — keep in config file or env var

---

## 5. Output: ClickUp Comments + File Attachments

**Pattern: Two-step ClickUp API sequence**

Step 1 — Post comment (Claude-generated):
```
POST /task/{task_id}/comment
Body: {"comment_text": "[3-5 sentence summary]\n\nFlagged: N SKUs | Run: YYYY-MM-DD", "notify_all": true}
```

Step 2 — Attach report:
```
POST /task/{task_id}/attachment
Body: multipart/form-data with CSV file
```

**File format:** CSV for MVP (simple to generate, opens in Sheets/Excel). HTML report for v2 if stakeholder presentation needed.

**ClickUp task targeting:** Hardcode `task_id` in config for MVP; parameterize when multi-task scenarios emerge.

**Claude prompt template:**
```
You are summarizing an Amazon FBA fee audit run for the OrganiHaus data team.

Run date: {run_date}
SKUs audited: {sku_count}
Anomalies detected: {anomaly_count}
Top anomalies (by absolute dollar impact):
{json_of_top_5_anomalies}

Write a concise ClickUp comment (3-5 sentences, under 150 words) that:
1. States the run outcome
2. Highlights the most significant anomaly if any
3. Notes any pattern (multiple SKUs, same fee type)
4. Ends with "Full report attached."

Use "this may indicate" not "this is caused by". Plain prose, no bullets. End with "Full report attached."
```

---

## 6. n8n Integration Pattern

**Pattern: n8n calls Python HTTP endpoint**

| Approach | Reliability | Recommendation |
|---|---|---|
| n8n Execute Command (local subprocess) | LOW — violates no-local-machine constraint | Do not use |
| n8n HTTP Request → Python FastAPI endpoint | HIGH — decoupled, cloud-compatible | **Use this** |
| n8n → Cloud Run / Lambda | HIGH — serverless | Overkill for MVP |

**Recommended:** Minimal FastAPI app exposing:
```
POST /run-audit
Body: {"trigger_type": "scheduled|manual", "date_range": {"start": "...", "end": "..."}}
Response: 202 Accepted + {"run_id": "..."}
```

Returns 202 immediately (n8n marks success). Avoids n8n timeout on long-running audit runs.

**n8n workflow (minimal):**
```
[Schedule: weekly Mon 09:00] → [HTTP POST /run-audit] → [IF error] → [ClickUp: "Audit trigger failed"]
```

n8n owns trigger and failure alert only. Python app handles retry and job logic.

**Fallback:** `python run_audit.py --trigger manual` — same `run_audit()` function as FastAPI endpoint.

---

## Suggested Build Order

1. **Data Access Layer** — Power BI integration + schema validation (highest uncertainty integration)
2. **Statistical Engine** — baseline + anomaly detection (pure Python, unit-testable without APIs)
3. **State Persistence** — BigQuery run log + anomaly archive (write-only first; add acknowledged suppression later)
4. **Output Layer** — ClickUp comment + CSV attachment + Claude narrative call
5. **Orchestrator** — `run_audit()` function connecting 1-4; integration test end-to-end
6. **n8n Trigger** — FastAPI endpoint + n8n HTTP node (deployment concern, not logic concern)

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Correct Approach |
|---|---|---|
| Passing raw rows to Claude | Token budget violation; non-deterministic | Claude receives pre-computed anomaly list only |
| Claude as the anomaly detector | Inconsistent results; not auditable; not unit-testable | Threshold logic in Python; Claude narrates only |
| BigQuery as baseline source without refresh | Stale baselines → false positives on seasonal variation | Recompute from Power BI every run |
| n8n waiting synchronously for completion | Timeout risk on 30-120s audit runs | FastAPI returns 202 immediately |
| Hardcoding thresholds before calibration | Floods alerts or misses anomalies | Config file with default conservative value (30%) |
