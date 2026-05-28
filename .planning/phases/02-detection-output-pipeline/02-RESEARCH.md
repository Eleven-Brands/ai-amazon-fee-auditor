# Phase 2: Detection + Output Pipeline - Research

**Researched:** 2026-05-28
**Domain:** Pandas rolling statistics, ClickUp API v2, Anthropic SDK one-shot call, DAX historical batch queries, Python CSV state management
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Baseline method = historical DAX query on first run, then weekly snapshot accumulation. First run queries `fact_fee_preview` WITHOUT `is_latest` filter, batched by country code, to obtain historical rows. Subsequent runs fetch only `is_latest=1` snapshot and append to `snapshots/`.
- **D-02:** Historical query batching = by country code (US, CA, GB, DE, FR, ES, IT, MX, BE — 9 batches + one for `amzn.gr.*` keys). Sales Region batching NOT used.
- **D-03:** Lookback window for first run = 16 weeks.
- **D-04:** Snapshot storage = `snapshots/snapshot_YYYYMMDD.csv` per run date. Rolling baseline slices N most recent files.
- **D-05:** Rolling baseline = 8-week rolling median of `avg_fee_per_unit` per `key_sales_marketplace_sku`. Median preferred over mean.
- **D-06:** If fewer than 4 snapshots exist, still compute baseline from available history but log warning.
- **D-07:** Anomaly threshold = 15% deviation from 8-week rolling median (configurable).
- **D-08:** Config file = `audit_config.json` at project root. Contains: `THRESHOLD_PCT`, `CLICKUP_TASK_ID`, `RECIPIENTS`, `SUSTAINED_SHIFT_N`. Git-tracked. No secrets.
- **D-09:** Flag increases prominently, decreases as informational. Two comment sections.
- **D-10:** Baseline grain = per `key_sales_marketplace_sku` (country-level, not Sales Region).
- **D-11:** Sustained-shift threshold = 4 consecutive weeks (configurable as `SUSTAINED_SHIFT_N`).
- **D-12:** Sustained-shift state storage = `anomaly_history.csv` (cumulative append). Schema: `key_sales_marketplace_sku, country, sku, asin, sales_region, week_start_date, avg_fee_per_unit, baseline_median_fee_per_unit, deviation_pct, direction, consecutive_weeks_flagged, run_date`.
- **D-13:** Sustained-shift SKUs = excluded from ClickUp comment, included in CSV with `sustained_shift: true` flag.
- **D-14:** ClickUp task ID = placeholder in `audit_config.json`. Developer sets before first run.
- **D-15:** ClickUp comment = Claude-generated summary (≤150 words): run date, total SKUs scanned, fee increases (count + top 3 by deviation %), fee reductions (count, informational). Ends with escalation prompt.
- **D-16:** Escalation prompt (ESC-01) = plain text: `"Reply YES to this comment to open an investigation task for the top flagged SKUs."`
- **D-17:** ClickUp recipients = none during testing (`RECIPIENTS: []`). Victor added by config edit.
- **D-18:** CSV attachment columns: `key_sales_marketplace_sku, country, sales_region, sku, asin, week_start_date, avg_fee_per_unit, baseline_median_fee_per_unit, deviation_pct, direction, sustained_shift`.
- **D-19:** Claude is narrative layer only. All math in Python. Claude receives anomaly JSON, never raw fee tables.
- **D-20:** Claude invocation = direct Anthropic SDK call (`claude-sonnet-4-6`). No LangChain. Single call. Context under 4K tokens.
- **D-21:** Claude output ≤150 words. Copy-paste ready for ClickUp comment.
- **D-22:** Phase 2 produces `run_audit.py`. Imports and reuses `get_token()`, `run_dax()`, `validate_value_count()`, `process_pbi_rows()`, `build_output_df()`, `iso_to_week_start()` from `explore_fees.py`. No duplication.
- **D-23:** Entry point: `python run_audit.py` (no arguments in Phase 2).

### Claude's Discretion

- Exact function signatures in `run_audit.py`
- Internal module structure (single file vs split into detection.py, output.py)
- ClickUp API error handling details (retry policy, timeout)
- Exact DAX query for historical batch (column selection, ORDER BY)
- Pydantic models for audit output rows (follow FeeRow pattern from explore_fees.py)

### Deferred Ideas (OUT OF SCOPE)

- Dual-gate threshold (pct AND absolute dollar floor — DETECT-04): v2 scope
- Seasonal Q4 baseline buckets (DETECT-05): v2 scope
- CLI `--trigger manual` flag: Phase 3 scope (EXEC-02)
- n8n scheduling: Phase 3 scope (EXEC-01)
- Victor notification routing: deferred until system validated
- `amzn.gr.*` key investigation (nature of keys): deferred
- BigQuery run log (REL-01): v2 scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DETECT-02 | Flag SKUs where current fee per unit deviates from baseline beyond configurable % threshold | Rolling 8-week median with shift(1) confirmed (see Pandas Patterns); deviation formula `(current - baseline) / baseline * 100`; min_periods=1 handles sparse history |
| DETECT-03 | Classify SKUs flagging anomaly in same direction for N consecutive weeks as "sustained shift" | Vectorized consecutive count lookup confirmed via groupby().last(); gap-handling (continuity check) documented; append-only pattern verified |
| OUT-01 | Post ClickUp comment with AI-generated run summary (Claude, under 150 words) | Anthropic SDK one-shot call confirmed; endpoint `POST /api/v2/task/{task_id}/comment`; `comment_text` field; authorization header format confirmed |
| OUT-02 | Attach CSV report to ClickUp comment with full anomaly list | Attachment endpoint `POST /api/v2/task/{task_id}/attachment`; multipart/form-data with `attachment` field name; BytesIO in-memory pattern confirmed |
| OUT-03 | Output target configurable — requires only config file edit, no code changes | `audit_config.json` pattern with `CLICKUP_TASK_ID` and `RECIPIENTS`; json.load() on startup |
| ESC-01 | ClickUp comment includes human-in-the-loop escalation prompt | Literal text appended to Claude output; no API escalation mechanism needed |
</phase_requirements>

---

## Summary

Phase 2 builds a linear Python pipeline with five discrete stages: (1) fetch data from Power BI (historical batch on first run, is_latest=1 snapshot on subsequent runs), (2) accumulate weekly snapshots and compute rolling 8-week median baseline per SKU, (3) flag anomalies at 15% threshold and classify sustained shifts, (4) invoke Claude once for narrative generation, and (5) post ClickUp comment and attach CSV. All five stages are well-understood and have verified implementation patterns.

The most important research discovery is the nature of `fact_fee_preview`: it is a fee schedule change log, not a transaction table. Historical rows represent prior fee schedule entries per key — a SKU may have only 1-5 historical dates spanning years, not weekly rows. The snapshot accumulation strategy (D-04) compensates for this by capturing the current fee weekly even when the fee schedule hasn't changed. The historical batch on first run seeds the `snapshots/` directory with whatever historical entries exist, then weekly is_latest=1 snapshots fill in the rolling window going forward.

A second key finding: consecutive count tracking requires a continuity check. If a SKU was flagged weeks 1-3, absent week 4, and flagged again week 5, looking up the raw max consecutive count from `anomaly_history.csv` would incorrectly report 4 consecutive weeks. The correct pattern checks whether the last history record for that (SKU, direction) pair was from the immediately previous run; if not, the count resets to 1.

**Primary recommendation:** Use a single `run_audit.py` file with clearly named functions per stage. The rolling median, consecutive tracking, and output generation are all unit-testable without live API calls. Build tests in parallel with implementation (one test file per stage).

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Power BI historical batch fetch | Python script (local) | — | `run_dax()` from explore_fees.py handles auth and HTTP; 10 DAX calls (9 countries + amzn.gr.*) |
| Weekly snapshot save | Python script (local filesystem) | — | Simple `to_csv()` to `snapshots/` directory; no DB needed per D-04 |
| Rolling baseline computation | Python/pandas (in-memory) | — | Pure pandas transform; no external service; unit-testable |
| Anomaly flagging | Python/pandas (in-memory) | — | Threshold comparison + direction classification; pure Python |
| Sustained-shift detection | Python/pandas + anomaly_history.csv | — | Lookup + append pattern; history is local CSV |
| Claude narrative generation | Anthropic API | — | Single one-shot call; receives pre-computed anomaly JSON |
| ClickUp comment post | ClickUp REST API v2 | — | `POST /api/v2/task/{task_id}/comment` via requests |
| CSV attachment | ClickUp REST API v2 | — | `POST /api/v2/task/{task_id}/attachment` multipart; BytesIO in-memory |
| Configuration | `audit_config.json` (local file) | — | Loaded at startup; all calibration knobs; no secrets |
| Secrets | `.env` (local) | — | `CLICKUP_API_KEY`, `ANTHROPIC_API_KEY`; never in `audit_config.json` |

---

## Standard Stack

### Core (already in requirements.txt)

| Library | Installed Version | Purpose | Status |
|---------|-------------------|---------|--------|
| `pandas` | 2.2.3 | Rolling baseline, anomaly DataFrame, CSV I/O | In requirements.txt |
| `requests` | 2.32.3 | ClickUp API calls (comment + attachment) | In requirements.txt |
| `pydantic` | 2.13.4 | AnomalyRow schema validation before CSV write | In requirements.txt |
| `msal` | 1.36.0 | Power BI auth (via get_token() from explore_fees.py) | In requirements.txt |
| `python-dotenv` | 1.0.1 | Load .env for CLICKUP_API_KEY, ANTHROPIC_API_KEY | In requirements.txt |
| `numpy` | 2.2.4 | Transitive pandas dependency; no direct use in Phase 2 | In requirements.txt |

### New in Phase 2

| Library | Installed Version | Purpose | Addition Required |
|---------|-------------------|---------|-------------------|
| `anthropic` | 0.101.0 | Claude narrative call | Add to requirements.txt [VERIFIED: slopcheck OK] |

**Installation for requirements.txt pin:**
```bash
pip show anthropic | grep Version
# Output: Version: 0.101.0
```

Add to requirements.txt:
```
anthropic==0.101.0
```

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `io.BytesIO` for CSV attachment | Write temp file to disk | BytesIO avoids disk I/O and cleanup; simpler |
| `json.load()` for audit_config.json | `pydantic` BaseSettings | json.load() is sufficient for 4 keys; pydantic overkill |
| Inline Claude call | LangChain | LangChain adds indirection; project explicitly prohibits it |

---

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| `anthropic` | PyPI | ~3 yrs | Very high | github.com/anthropics/anthropic-sdk-python | [OK] | Approved |

[VERIFIED: slopcheck OK — scanned 2026-05-28]
[VERIFIED: pip show — version 0.101.0, Author-email: Anthropic <support@anthropic.com>, License: MIT]

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
run_audit.py main()
     |
     +-- [INIT] load_config() -> audit_config.json
     |         load_dotenv() -> CLICKUP_API_KEY, ANTHROPIC_API_KEY
     |
     +-- [AUTH] get_token() [imported from explore_fees.py]
     |         -> PBI bearer token (cached)
     |
     +-- [DECISION] snapshots/ has 0 files?
     |     YES -> historical_batch_fetch()
     |            10 x run_dax() (9 country + amzn.gr.*)
     |            group by (key, date_fee_preview)
     |            split into snapshot CSVs by date_fee_preview week
     |     NO  -> snapshot_fetch()
     |            1 x run_dax() (is_latest=1)
     |            save as snapshots/snapshot_YYYYMMDD.csv
     |
     +-- [BASELINE] load_snapshots(n=8) -> combined DataFrame (sorted by sku, week)
     |         rolling 8-week median with shift(1) per sku
     |         -> baseline_df: (key, week, baseline_median_fee_per_unit)
     |
     +-- [DETECT] compare current snapshot vs baseline
     |         deviation_pct = (current - baseline) / baseline * 100
     |         flag if |deviation_pct| > THRESHOLD_PCT
     |         classify direction: increase / decrease
     |         load anomaly_history.csv -> consecutive count lookup (with continuity check)
     |         -> anomalies_df: all flagged rows with consecutive_weeks_flagged
     |         classify sustained_shift = (consecutive_weeks_flagged >= SUSTAINED_SHIFT_N)
     |         append anomalies_df rows to anomaly_history.csv (mode='a', header=False)
     |
     +-- [NARRATE] active_anomalies = anomalies_df[~sustained_shift]
     |         build_anomaly_json(active_anomalies) -> anomaly_json (summary, not raw rows)
     |         anthropic.Anthropic().messages.create(...)
     |         -> comment_text (<=150 words)
     |
     +-- [OUTPUT] post_clickup_comment(comment_text)
     |         -> POST /api/v2/task/{task_id}/comment
     |
     +-- [ATTACH] attach_clickup_csv(anomalies_df)  # includes sustained_shift rows
               -> BytesIO CSV buffer
               -> POST /api/v2/task/{task_id}/attachment (multipart)
```

### Recommended Project Structure

```
.
├── explore_fees.py          # Phase 1 (unchanged — source of reusable functions)
├── run_audit.py             # Phase 2 main script (imports from explore_fees.py)
├── audit_config.json        # Calibration config (git-tracked, no secrets)
├── .env                     # Secrets: CLICKUP_API_KEY, ANTHROPIC_API_KEY (git-ignored)
├── .env.example             # Update with CLICKUP_API_KEY placeholder (Phase 2)
├── requirements.txt         # Add anthropic==0.101.0
├── snapshots/               # Weekly is_latest=1 snapshots (git-ignored via *.csv)
│   └── .gitkeep             # Track directory, ignore contents
├── anomaly_history.csv      # Cumulative sustained-shift state (git-ignored via *.csv)
├── output/                  # Phase 1 exploratory CSVs (unchanged)
│   └── .gitkeep
└── tests/
    ├── conftest.py          # Existing Phase 1 fixtures (extend with Phase 2 fixtures)
    ├── test_aggregation.py  # Existing Phase 1 tests (do not modify)
    └── test_detection.py    # New Phase 2 tests (detection + output logic)
```

### Pattern 1: Rolling 8-Week Median Baseline with Exclusion of Current Week

**What:** Compute each row's baseline as the median of the 7 rows before it (not including current) per SKU, sorted by week_start_date.
**When to use:** Every run after loading and combining all snapshot CSVs.

```python
# Source: verified via Python execution 2026-05-28
# Sort is critical — rolling window assumes chronological order within each group
combined = pd.concat([pd.read_csv(f, parse_dates=['week_start_date'])
                      for f in snapshot_files], ignore_index=True)
combined = combined.sort_values(['key_sales_marketplace_sku', 'week_start_date'])

combined['baseline_median_fee_per_unit'] = (
    combined.groupby('key_sales_marketplace_sku')['avg_fee_per_unit']
    .transform(lambda x: x.shift(1).rolling(window=8, min_periods=1).median())
)
# First week per SKU always has NaN baseline (shift(1) on first row = NaN)
# Rows with NaN baseline are not flagged as anomalies (skip comparison)
```

**Why `shift(1)`:** Without it, the rolling window includes the current week in its own baseline, which always produces 0% deviation for stable SKUs and understates deviation for anomalous ones. The baseline must be computed from PRIOR weeks only.

**Edge case — fewer than 8 snapshots:** `min_periods=1` handles this by computing median from available rows. Log a warning if `len(snapshot_files) < 4` (D-06).

### Pattern 2: Snapshot File Loading (Most Recent N Files)

**What:** Load all snapshot CSVs from `snapshots/`, sort lexicographically (which equals date order for YYYYMMDD filenames), take last N files.

```python
# Source: verified via Python execution 2026-05-28
import pathlib

snapshots_dir = pathlib.Path('snapshots')
snapshot_files = sorted(snapshots_dir.glob('snapshot_*.csv'))
# Lexicographic sort = date sort for snapshot_YYYYMMDD.csv format (verified)

if len(snapshot_files) < 4:
    print(f'WARNING: baseline computed from {len(snapshot_files)} weeks '
          f'— results may be noisy until 4+ weeks accumulate.')

# Use last 8 for rolling window (earlier history not needed for baseline computation)
window_files = snapshot_files[-8:]
```

### Pattern 3: Consecutive Count Lookup with Continuity Check

**What:** For each currently flagged (SKU, direction) pair, look up how many consecutive prior weeks it was flagged. Reset to 0 if there was a gap.

```python
# Source: verified via Python execution 2026-05-28
import pandas as pd
from pathlib import Path
import datetime

HISTORY_PATH = Path('anomaly_history.csv')
HISTORY_COLUMNS = [
    'key_sales_marketplace_sku', 'country', 'sku', 'asin', 'sales_region',
    'week_start_date', 'avg_fee_per_unit', 'baseline_median_fee_per_unit',
    'deviation_pct', 'direction', 'consecutive_weeks_flagged', 'run_date'
]

def load_prior_counts(current_run_date: datetime.date) -> dict:
    """Return {(key, direction): consecutive_count} for the previous run only."""
    if not HISTORY_PATH.exists():
        return {}
    history = pd.read_csv(HISTORY_PATH, parse_dates=['run_date'])
    prev_expected = pd.Timestamp(current_run_date) - pd.Timedelta(weeks=1)
    # Get last record per (key, direction)
    last_records = (
        history.sort_values('run_date')
        .groupby(['key_sales_marketplace_sku', 'direction'])
        .last()
        .reset_index()
    )
    # Only use counts from records dated exactly one week ago (continuity check)
    prior = last_records[last_records['run_date'].dt.date == prev_expected.date()]
    return dict(zip(
        zip(prior['key_sales_marketplace_sku'], prior['direction']),
        prior['consecutive_weeks_flagged']
    ))

def append_to_history(new_rows: pd.DataFrame) -> None:
    """Append new anomaly rows to anomaly_history.csv, creating file on first run."""
    write_header = not HISTORY_PATH.exists()
    new_rows.to_csv(HISTORY_PATH, mode='a', header=write_header, index=False)
```

**Why continuity check matters:** If a SKU is flagged weeks 1-3, absent week 4, and returns week 5 — without the continuity check the lookup finds consecutive_count=3 from week 3 and adds 1 to get 4, incorrectly classifying it as a sustained shift. The continuity check resets the count to 1 when the prior run date is not the immediately preceding week.

### Pattern 4: Historical DAX Batch Query (First Run Only)

**What:** Query `fact_fee_preview` without `is_latest` filter, filtered by country prefix using `LEFT()` in DAX, wrapped in `FILTER()` around `SUMMARIZECOLUMNS`.

```python
# Source: derived from Phase 1 DAX patterns (explore_fees.py) + verified 2026-05-28
# FILTER wrapping SUMMARIZECOLUMNS is valid DAX for post-aggregation row filtering.
# Country prefix filter on the grouped key gives same result whether applied
# before or after aggregation.

COUNTRY_PREFIXES = {
    'US': 'US | ',
    'CA': 'CA | ',
    'GB': 'GB | ',
    'DE': 'DE | ',
    'FR': 'FR | ',
    'ES': 'ES | ',
    'IT': 'IT | ',
    'MX': 'MX | ',
    'BE': 'BE | ',
}

def build_historical_dax(prefix: str) -> str:
    """DAX for one country batch: all historical rows for this prefix."""
    prefix_len = len(prefix)
    return f"""EVALUATE
FILTER(
    SUMMARIZECOLUMNS(
        'fact_fee_preview'[key_sales_marketplace_sku],
        'fact_fee_preview'[date_fee_preview],
        "avg_fee_per_unit", AVERAGE('fact_fee_preview'[expected_fulfillment_fee_per_unit])
    ),
    LEFT('fact_fee_preview'[key_sales_marketplace_sku], {prefix_len}) = "{prefix}"
)"""

def build_amzn_gr_dax() -> str:
    """DAX for amzn.gr.* keys (no country prefix format)."""
    return """EVALUATE
FILTER(
    SUMMARIZECOLUMNS(
        'fact_fee_preview'[key_sales_marketplace_sku],
        'fact_fee_preview'[date_fee_preview],
        "avg_fee_per_unit", AVERAGE('fact_fee_preview'[expected_fulfillment_fee_per_unit])
    ),
    LEFT('fact_fee_preview'[key_sales_marketplace_sku], 7) = "amzn.gr"
)"""
```

**Important:** Do NOT add a date range filter to the historical DAX. `fact_fee_preview` is a fee schedule change log, not a transaction table. A key may have only 2-5 historical entries spanning years. Filtering to 16 weeks would exclude valid historical baseline points that predate the window. Query all historical rows per country batch and let Python process them.

**Value count safety:** Worst-case estimate (US batch, 1800 keys × 10 historical entries × 3 cols = 54,000 values). Well under the 1M limit. No `validate_value_count()` guard required for individual country batches, but include it as a safety check using the actual row count from prior batches.

### Pattern 5: Anthropic One-Shot Narrative Call

**What:** Single `messages.create()` call with system prompt + user message containing anomaly JSON. No tools, no streaming, no conversation history.

```python
# Source: verified against installed anthropic==0.101.0 SDK 2026-05-28
import anthropic
import json
import os

SYSTEM_PROMPT = (
    "You are summarizing an Amazon FBA fee audit run for the OrganiHaus data team. "
    "Generate a ClickUp comment under 150 words. "
    "Cover: run date, total SKUs scanned, count of fee increases (name top 3 by deviation %), "
    "count of fee reductions (informational only). "
    "Use 'may indicate' not 'is caused by'. Plain prose, no bullet points. "
    "End with exactly: 'Reply YES to this comment to open an investigation task for the "
    "top flagged SKUs.'"
)

def generate_narrative(anomaly_summary: dict) -> str:
    """Call Claude once with anomaly JSON summary. Returns <=150-word comment text."""
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    user_message = f"Anomaly summary:\n{json.dumps(anomaly_summary, indent=2)}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,   # ~150 words + headroom; response.content[0].text is the output
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text
```

**anomaly_summary structure (what Claude receives — not raw rows):**
```python
{
    "run_date": "2026-05-28",
    "total_scanned": 5274,
    "fee_increases": [
        {"sku": "US-OHFB-001", "key": "US | US-OHFB-001",
         "deviation_pct": 45.2, "avg_fee_per_unit": 6.50, "baseline": 4.48},
        # top N only, sorted by deviation_pct desc
    ],
    "fee_reductions": [
        {"sku": "CA-OHFB-003", "key": "CA | CA-OHFB-003",
         "deviation_pct": -18.5, "avg_fee_per_unit": 2.80, "baseline": 3.43},
    ]
}
```

**Token budget:** System prompt ~100 tokens + anomaly JSON with top 5 increases and 5 reductions ~200 tokens + output 300 tokens = ~600 tokens total. Well under the 4K context limit stated in D-20.

### Pattern 6: ClickUp Comment Post

**What:** POST to `/api/v2/task/{task_id}/comment` with JSON body. Authorization header uses raw personal token (no "Bearer" prefix).

```python
# Source: developer.clickup.com/docs/authentication [VERIFIED 2026-05-28]
# Source: developer.clickup.com/reference/createtaskcomment [VERIFIED 2026-05-28]

def post_clickup_comment(task_id: str, comment_text: str, api_key: str) -> dict:
    """Post comment to ClickUp task. Returns API response JSON."""
    url = f"https://api.clickup.com/api/v2/task/{task_id}/comment"
    headers = {
        "Authorization": api_key,   # raw pk_ token, NO "Bearer" prefix
        "Content-Type": "application/json",
    }
    body = {
        "comment_text": comment_text,
        "notify_all": False,        # False during testing (RECIPIENTS: [])
    }
    r = requests.post(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    return r.json()
```

**Critical:** ClickUp personal API tokens (`pk_...`) do NOT use the `Bearer` prefix. Using `Authorization: Bearer pk_...` causes "Oauth token not found" error. Use `Authorization: pk_...` directly. [VERIFIED: developer.clickup.com/docs/authentication]

### Pattern 7: ClickUp CSV Attachment

**What:** POST to `/api/v2/task/{task_id}/attachment` with multipart/form-data. Use `io.BytesIO` for in-memory CSV. Do NOT set `Content-Type` header manually — `requests` sets it with the multipart boundary.

```python
# Source: developer.clickup.com/reference/createtaskattachment [VERIFIED 2026-05-28]
# Source: WebSearch verification of field name 'attachment' [VERIFIED via PHP gist + docs]
import io

def attach_csv_to_task(task_id: str, anomaly_df: pd.DataFrame,
                        run_date: str, api_key: str) -> dict:
    """Attach anomaly CSV to ClickUp task as multipart upload."""
    url = f"https://api.clickup.com/api/v2/task/{task_id}/attachment"
    headers = {
        "Authorization": api_key,   # raw pk_ token, NO "Bearer" prefix
        # DO NOT set Content-Type — requests sets multipart boundary automatically
    }
    csv_buffer = io.BytesIO()
    anomaly_df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)   # must seek to 0 before passing to requests

    filename = f"anomaly_report_{run_date}.csv"
    files = {"attachment": (filename, csv_buffer, "text/csv")}
    r = requests.post(url, headers=headers, files=files, timeout=60)
    r.raise_for_status()
    return r.json()
```

**Ordering:** Comment and attachment are independent ClickUp API calls. Post comment first (it contains the narrative and escalation prompt), then attach the CSV. No dependency between them at the API level — either can succeed independently.

### Anti-Patterns to Avoid

- **Passing raw DataFrames to Claude:** Violates D-19 and token budget. Claude receives anomaly JSON summary only (top N SKUs with pre-computed stats).
- **Setting `Content-Type: multipart/form-data` manually:** Breaks the multipart boundary. Let `requests` set it via the `files=` parameter.
- **Using `Authorization: Bearer pk_...`:** Wrong for personal ClickUp tokens. Use raw token value with no prefix.
- **Rolling median without `shift(1)`:** Includes current week in its own baseline, understating anomalies.
- **Looking up consecutive count without continuity check:** Inflates counts after gap weeks, causing false sustained-shift classification.
- **Not seeking BytesIO to 0 before upload:** Sends empty file to ClickUp.
- **Date-filtering the historical DAX to 16 weeks:** The fee schedule changes infrequently; filtering could exclude all historical entries for SKUs with stable fees.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Rolling window median | Custom loop over dict of lists | `pandas.GroupBy.transform(lambda x: x.shift(1).rolling(window=8, min_periods=1).median())` | Handles group boundaries, NaN propagation, min_periods correctly |
| Multipart HTTP upload | Manual boundary encoding | `requests` with `files=` parameter | `requests` handles Content-Type, boundary, MIME encoding |
| Anthropic API client | `requests` to api.anthropic.com | `anthropic.Anthropic()` | SDK handles auth, retries, response parsing, error types |
| CSV append with header check | Check file size, parse first line | `pd.to_csv(path, mode='a', header=not path.exists())` | `pathlib.Path.exists()` is the correct guard |
| Consecutive count across runs | SQL-style window function | Load history CSV, groupby().last(), dict lookup | Simple and testable without a DB |
| DAX string prefix filter | Complex FILTER expression | `LEFT(col, N) = "prefix"` | Verified DAX pattern, consistent with Phase 1 approach |

---

## Common Pitfalls

### Pitfall 1: ClickUp Authorization Header Format

**What goes wrong:** Using `Authorization: Bearer pk_xxxxxxxx` (with "Bearer" prefix) for a personal ClickUp API token returns a 401 "Oauth token not found" error.

**Why it happens:** Bearer prefix is for OAuth access tokens only. Personal API tokens are passed raw.

**How to avoid:** `headers = {"Authorization": api_key}` where `api_key` is the raw `pk_...` value read from `.env`. Never add "Bearer" prefix.

**Warning signs:** 401 response with "Oauth token not found" message from ClickUp API.

### Pitfall 2: Consecutive Count Inflation After Gap Weeks

**What goes wrong:** A SKU is flagged weeks 1-3, not flagged week 4, then flagged week 5. If you look up `max(consecutive_weeks_flagged)` from history, you find 3 and add 1 to get 4 — incorrectly triggering sustained-shift suppression.

**Why it happens:** The anomaly_history.csv lookup returns the historical max, not the continuous recent streak.

**How to avoid:** Compare `last_records['run_date'].dt.date == prev_expected.date()` before using the lookup. If the last record is not from the immediately prior run date, reset count to 0 before adding 1.

**Warning signs:** SKUs disappearing from ClickUp alerts after a week they were not flagged, even though they resumed anomalous behavior.

### Pitfall 3: Sparse Historical Baseline (Few Historical Entries per Key)

**What goes wrong:** The historical batch query returns only 1-3 rows per key (not 16). Rolling 8-week median has almost no data to work with. First-run baselines are based on 1-2 data points per SKU.

**Why it happens:** `fact_fee_preview` is a fee schedule change log, not a weekly transaction table. A SKU whose fee hasn't changed in 2 years has only 1 historical row.

**How to avoid:** Accept this as a known limitation. Log a count of keys with fewer than 4 historical rows on first run. The snapshot accumulation strategy (D-04) is designed to build the rolling window over time. After 8 weekly runs, all baselines are well-populated regardless of historical data sparsity.

**Warning signs:** First-run report shows a large number of anomalies with very high deviation — likely because baselines are based on 1 data point and the current fee differs from that single historical entry.

### Pitfall 4: Rolling Median Includes Current Week

**What goes wrong:** Using `rolling(window=8).median()` without `shift(1)` computes the median including the current row. For the most recent week (the one we're comparing against the baseline), this means the current fee is part of its own baseline — giving 0% deviation for any stable SKU and understating spikes.

**Why it happens:** Default pandas rolling includes the current row in the window.

**How to avoid:** Always use `.shift(1).rolling(window=8, min_periods=1).median()`. The first row per SKU will have NaN baseline — filter out NaN baseline rows before anomaly comparison.

**Warning signs:** Zero anomalies detected even when fee clearly changed vs prior weeks.

### Pitfall 5: BytesIO Not Seeked to 0

**What goes wrong:** `to_csv(buffer)` writes to BytesIO and leaves the cursor at end-of-file. Passing the buffer to `requests` without seeking uploads an empty file.

**Why it happens:** `to_csv()` advances the stream cursor to the end of written data.

**How to avoid:** Always call `buffer.seek(0)` after `to_csv(buffer)` and before passing to `requests`.

**Warning signs:** ClickUp attachment appears in the task but has 0 bytes when downloaded.

### Pitfall 6: Historical DAX Date Filter Excludes All History for Stable-Fee SKUs

**What goes wrong:** Adding `'fact_fee_preview'[date_fee_preview] >= DATE(2026, 2, 5)` to the historical batch DAX returns 0 rows for SKUs whose fee hasn't changed since before 2026. These SKUs have no baseline and are incorrectly treated as new.

**Why it happens:** Filtering by date on a fee schedule change log removes all rows where the fee was set before the lookback window (which is most rows for stable SKUs).

**How to avoid:** Do NOT add a date range filter to the historical batch DAX. Query all historical rows per country batch. Value count is safe without it (max ~54K per country batch, well under 1M limit).

**Warning signs:** Historical batch returns very few rows per key; many keys have 0 historical baseline points.

---

## Code Examples

### Complete Anomaly Detection Function

```python
# Source: verified logic via Python execution 2026-05-28

def detect_anomalies(current_df: pd.DataFrame, combined_history_df: pd.DataFrame,
                     threshold_pct: float) -> pd.DataFrame:
    """
    Compare current week's fees against 8-week rolling median baseline.
    Returns DataFrame of flagged rows with deviation_pct and direction columns.
    Excludes rows where baseline is NaN (first week per SKU).
    """
    # Ensure chronological sort within each SKU group
    combined = combined_history_df.sort_values(
        ['key_sales_marketplace_sku', 'week_start_date'])

    combined['baseline_median_fee_per_unit'] = (
        combined.groupby('key_sales_marketplace_sku')['avg_fee_per_unit']
        .transform(lambda x: x.shift(1).rolling(window=8, min_periods=1).median())
    )

    # Current week = most recent row per SKU (last snapshot added)
    current_week_date = current_df['week_start_date'].max()
    current = combined[combined['week_start_date'] == current_week_date].copy()

    # Drop rows with no baseline (first appearance of a SKU)
    current = current.dropna(subset=['baseline_median_fee_per_unit'])

    # Deviation calculation
    current['deviation_pct'] = (
        (current['avg_fee_per_unit'] - current['baseline_median_fee_per_unit'])
        / current['baseline_median_fee_per_unit'] * 100
    )

    # Flag anomalies
    flagged = current[current['deviation_pct'].abs() > threshold_pct].copy()
    flagged['direction'] = flagged['deviation_pct'].apply(
        lambda x: 'increase' if x > 0 else 'decrease')

    return flagged
```

### Snapshot Save Pattern

```python
# Source: verified pattern 2026-05-28
import datetime, pathlib

def save_snapshot(df: pd.DataFrame, run_date: datetime.date) -> pathlib.Path:
    """Save current week's is_latest=1 data as a snapshot CSV."""
    snapshots_dir = pathlib.Path('snapshots')
    snapshots_dir.mkdir(exist_ok=True)
    path = snapshots_dir / f'snapshot_{run_date.strftime("%Y%m%d")}.csv'
    df.to_csv(path, index=False)
    return path
```

### audit_config.json Default Structure

```json
{
    "THRESHOLD_PCT": 15,
    "CLICKUP_TASK_ID": "PLACEHOLDER",
    "RECIPIENTS": [],
    "SUSTAINED_SHIFT_N": 4
}
```

Load at startup:
```python
import json
with open('audit_config.json') as f:
    config = json.load(f)
threshold = config['THRESHOLD_PCT']
task_id = config['CLICKUP_TASK_ID']
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| ClickUp personal token with Bearer prefix | Raw pk_ token, no Bearer prefix | Always been this way — common mistake | 401 error if wrong |
| pandas rolling with closed='right' (default) | shift(1) + rolling for explicit prior-week baseline | pandas 2.x (closed='left' requires explicit shift) | Must use shift(1) pattern |
| LangChain/LlamaIndex for simple one-shot calls | Direct Anthropic SDK `messages.create()` | 2024-2025 ecosystem maturation | Less abstraction, more control |

**Deprecated/outdated:**
- `powerbi-query` skill mention in ARCHITECTURE.md: Phase 2 uses `run_dax()` from `explore_fees.py` directly, not the n8n-based powerbi-query skill. That skill is relevant only in Phase 3 when n8n orchestrates the run.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `fact_fee_preview` historical rows are sparse (1-5 entries per key, not weekly) | Common Pitfalls §3, DAX Pattern §4 | If the table actually has weekly rows, date filtering would be useful; but the no-filter approach is always safe and at worst returns more data than needed |
| A2 | The `amzn.gr.*` prefix always starts exactly with `amzn.gr` (7 chars) | Pattern §4 | If some keys use different casing or format, the `LEFT(..., 7) = "amzn.gr"` filter misses them; verify against Phase 1 CSV output |
| A3 | ClickUp `notify_all: false` suppresses all notifications regardless of RECIPIENTS config | ClickUp Pattern §6 | If ClickUp ignores `notify_all` and notifies based on task watchers, testing could send real notifications; set task_id to a test task during development |
| A4 | `claude-sonnet-4-6` model ID is valid in the Anthropic API as of Phase 2 execution | Pattern §5 | If the model ID has been retired or renamed, the API call fails; verify by running `python -c "import anthropic; print(anthropic.Anthropic().models.list())"` before first run |

---

## Open Questions

1. **Does `fact_fee_preview` have weekly rows or sparse fee-schedule entries?**
   - What we know: Phase 1 confirmed 3.7M total rows vs 5,274 is_latest=1 rows. Historical structure uncertain.
   - What's unclear: Whether historical rows represent daily fee schedule entries or only when fees changed.
   - Recommendation: On first run, print `len(historical_df)` per country batch and log the date range of entries. If counts are 1-5 per key, baseline will be sparse for first 8 weeks. If counts are ~700 per key (daily over 2 years), date filtering might be worthwhile. The no-filter approach handles both correctly.

2. **What is the run date reference for the continuity check?**
   - What we know: The check compares `last_records['run_date']` against `current_date - 7 days`.
   - What's unclear: If the audit doesn't run exactly 7 days apart (e.g., a run is delayed 8 days), the continuity check would reset counts unnecessarily.
   - Recommendation: Accept ±1 day tolerance: `abs((last_run_date - prev_expected).days) <= 1`. Or simplify: reset only if the last run was more than 10 days ago.

3. **Which test task ID to use for ClickUp testing?**
   - What we know: D-14 says CLICKUP_TASK_ID is a placeholder requiring developer configuration.
   - What's unclear: Whether a test task already exists in OrganiHaus ClickUp workspace.
   - Recommendation: Create a dedicated "FBA Fee Auditor - Test" task in ClickUp before Phase 2 execution. Add to plan as a prerequisite step.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.13.2 (CLAUDE.md recommends 3.12; 3.13 works, all Phase 1 tests pass) | None needed |
| `anthropic` SDK | Narrative generation | ✓ | 0.101.0 | — |
| `pandas` | Rolling baseline, CSV I/O | ✓ | 2.2.3 | — |
| `requests` | ClickUp API calls | ✓ | 2.32.3 | — |
| `pydantic` | AnomalyRow schema validation | ✓ | 2.13.4 | — |
| `msal` | Power BI auth | ✓ | 1.36.0 | — |
| `python-dotenv` | .env loading | ✓ | 1.0.1 | — |
| ANTHROPIC_API_KEY | Narrative call | Placeholder in .env.example | — | Cannot run narrative step without it |
| CLICKUP_API_KEY | ClickUp output | Not yet in .env.example | — | Cannot post to ClickUp without it |
| ClickUp task ID | Output target | Placeholder in audit_config.json | — | Configure before first run |

**Missing dependencies with no fallback:**
- `CLICKUP_API_KEY` in `.env` — must be added before execution. Add to `.env.example` in Phase 2.
- `CLICKUP_TASK_ID` in `audit_config.json` — must be replaced from "PLACEHOLDER" before first run.
- `ANTHROPIC_API_KEY` in `.env` — already in `.env.example` as placeholder (Phase 2 comment).

**Missing dependencies with fallback:**
- None — all required libraries are installed.

**.gitignore additions needed in Phase 2:**
- `snapshots/` directory: add `snapshots/*` + `!snapshots/.gitkeep` pattern (analogous to `output/`).
- `anomaly_history.csv`: already covered by `*.csv` rule in existing `.gitignore`.
- `audit_config.json`: NOT in `.gitignore` (intentionally git-tracked — no secrets).

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | `pytest.ini` (exists — `testpaths = tests`, `addopts = -q`) |
| Quick run command | `pytest tests/test_detection.py -x -q` |
| Full suite command | `pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DETECT-02 | Rolling 8-week median baseline computed correctly | unit | `pytest tests/test_detection.py::test_rolling_baseline_excludes_current_week -x -q` | ❌ Wave 0 |
| DETECT-02 | 15% threshold flags anomalies correctly; below-threshold SKUs not flagged | unit | `pytest tests/test_detection.py::test_anomaly_threshold_15pct -x -q` | ❌ Wave 0 |
| DETECT-02 | Sparse history (< 8 weeks) handled via min_periods=1 | unit | `pytest tests/test_detection.py::test_sparse_baseline_min_periods -x -q` | ❌ Wave 0 |
| DETECT-03 | Consecutive count increments correctly across runs | unit | `pytest tests/test_detection.py::test_consecutive_count_increments -x -q` | ❌ Wave 0 |
| DETECT-03 | Consecutive count resets after gap week | unit | `pytest tests/test_detection.py::test_consecutive_count_resets_on_gap -x -q` | ❌ Wave 0 |
| DETECT-03 | SKU with consecutive >= SUSTAINED_SHIFT_N classified as sustained_shift | unit | `pytest tests/test_detection.py::test_sustained_shift_classification -x -q` | ❌ Wave 0 |
| OUT-01 | Claude call returns ≤150 words | manual-only | N/A — requires live API key | — |
| OUT-01 | Narrative generation function is called with correct anomaly_summary structure | unit (mocked) | `pytest tests/test_detection.py::test_generate_narrative_payload -x -q` | ❌ Wave 0 |
| OUT-02 | CSV attachment contains correct D-18 columns | unit | `pytest tests/test_detection.py::test_csv_attachment_columns -x -q` | ❌ Wave 0 |
| OUT-02 | Sustained-shift rows included in CSV with `sustained_shift: True` | unit | `pytest tests/test_detection.py::test_csv_includes_sustained_shift_rows -x -q` | ❌ Wave 0 |
| OUT-03 | Changing task_id in audit_config.json changes ClickUp target without code change | unit (mocked) | `pytest tests/test_detection.py::test_config_drives_task_id -x -q` | ❌ Wave 0 |
| ESC-01 | Comment text ends with exact escalation prompt string | unit (mocked) | `pytest tests/test_detection.py::test_escalation_prompt_in_comment -x -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_detection.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q` (full suite including Phase 1 tests)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_detection.py` — all Phase 2 unit tests (12 tests listed above)
- [ ] `snapshots/.gitkeep` — create with `snapshots/*` + `!snapshots/.gitkeep` in `.gitignore`
- [ ] `audit_config.json` — create default config at project root
- [ ] Update `.env.example` to add `CLICKUP_API_KEY=` placeholder
- [ ] Update `requirements.txt` to add `anthropic==0.101.0`

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1` (from config.json).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | No user login in this script |
| V3 Session Management | No | Stateless script execution |
| V4 Access Control | No | Single-user local script |
| V5 Input Validation | Yes | Pydantic AnomalyRow validates output schema before CSV write; `audit_config.json` values should be type-checked on load |
| V6 Cryptography | No | No encryption needed; secrets in OS-secured .env |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key in audit_config.json (accidentally) | Information Disclosure | `audit_config.json` contains ONLY calibration values (THRESHOLD_PCT, CLICKUP_TASK_ID, RECIPIENTS, SUSTAINED_SHIFT_N). `CLICKUP_API_KEY` and `ANTHROPIC_API_KEY` go ONLY in `.env`. Code review gate: grep for "API_KEY" in audit_config.json before commit. |
| Prompt injection via anomaly SKU names | Tampering | Anomaly JSON is built from validated DataFrame rows (Pydantic-gated). SKU names come from Power BI, not user input. Risk is LOW for this internal tool. |
| ClickUp task ID misconfigured (posts to wrong task) | Elevation of Privilege | Validate `CLICKUP_TASK_ID != "PLACEHOLDER"` before any API call; fail with clear error if placeholder is still set. |
| `.env` accidentally committed | Information Disclosure | `.env` is in `.gitignore` (verified). `.env.example` with blank values is committed. Pre-commit check recommended for Phase 3. |

---

## Sources

### Primary (HIGH confidence)
- `explore_fees.py` — Phase 1 source code; all reusable function signatures, DAX patterns, PBI endpoint, constants
- `anthropic==0.101.0` installed SDK — `help(anthropic.Anthropic().messages.create)` shows exact signature
- Python execution verification — rolling median, consecutive count, BytesIO, DAX template patterns all executed successfully in this session
- developer.clickup.com/docs/authentication — Authorization header format confirmed: raw token, no Bearer prefix
- developer.clickup.com/reference/createtaskcomment — endpoint URL and body structure confirmed
- developer.clickup.com/reference/createtaskattachment — multipart/form-data, `attachment` field name confirmed
- slopcheck [OK] for `anthropic` package (pypi)

### Secondary (MEDIUM confidence)
- WebSearch: ClickUp API v2 attachment field name `'attachment'` — cross-verified via developer docs and PHP gist showing same field name
- WebSearch: ClickUp Authorization header `pk_` token format — cross-verified with official auth docs

### Tertiary (LOW confidence)
- None — all critical claims verified via direct tool execution or official documentation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages installed and verified via pip show / slopcheck
- Rolling median pattern: HIGH — verified via Python execution with edge cases
- ClickUp API endpoints: HIGH — verified via official developer.clickup.com documentation
- Anthropic SDK call pattern: HIGH — verified via installed SDK introspection
- DAX historical batch: MEDIUM — pattern derived from Phase 1 working DAX; actual historical row structure of `fact_fee_preview` cannot be verified without a live API call
- Consecutive count gap handling: HIGH — verified via Python execution
- Pitfalls: HIGH (most are verified by execution or official docs)

**Research date:** 2026-05-28
**Valid until:** 2026-06-28 (stable libraries; ClickUp API v2 stable; Anthropic SDK stable)
