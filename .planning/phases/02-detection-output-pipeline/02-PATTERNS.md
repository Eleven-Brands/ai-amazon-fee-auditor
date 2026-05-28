# Phase 2: Detection + Output Pipeline - Pattern Map

**Mapped:** 2026-05-28
**Files analyzed:** 6 new/modified files
**Analogs found:** 5 / 6

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `run_audit.py` | script (orchestrator) | batch, request-response | `explore_fees.py` | exact — same stack, same auth+DAX+CSV pipeline shape |
| `tests/test_detection.py` | test | batch (unit) | `tests/test_aggregation.py` | exact — same framework, same mock pattern, same import style |
| `tests/conftest.py` | test fixture | — | `tests/conftest.py` (extend existing) | exact — add fixtures to existing file |
| `audit_config.json` | config | — | `.planning/config.json` (structure reference only) | no analog — new pattern |
| `snapshots/.gitkeep` | directory marker | — | `output/.gitkeep` + `.gitignore` | exact — copy `.gitignore` pattern verbatim |
| `requirements.txt` | config | — | `requirements.txt` (modify existing) | exact — append one line |

---

## Pattern Assignments

### `run_audit.py` (script, batch + request-response)

**Analog:** `explore_fees.py`

**Imports pattern** (`explore_fees.py` lines 1–17):
```python
"""
FBA Fee Auditor — Phase 1 exploration script.
...
"""

import datetime
import os
import pathlib
from typing import Optional

import msal
import pandas as pd
import requests
from dotenv import load_dotenv
from pydantic import BaseModel
```

For Phase 2, extend with:
```python
import anthropic
import io
import json
```

**Module-level constants pattern** (`explore_fees.py` lines 19–37):
```python
WORKSPACE_ID = "47144ee2-02f9-4408-9ed5-57acf6a9f44d"
DATASET_ID   = "a95798aa-a3ec-4a89-9816-63cde534cdd7"
SCOPES       = ["https://analysis.windows.net/powerbi/api/Dataset.Read.All"]
CACHE_PATH   = os.path.expanduser("~/.claude/powerbi_token_cache.json")

COUNTRY_CURRENCY = {
    "US": "USD",
    "CA": "CAD",
    ...
}
```

For Phase 2, add after imports:
```python
HISTORY_PATH = pathlib.Path("anomaly_history.csv")
SNAPSHOTS_DIR = pathlib.Path("snapshots")
HISTORY_COLUMNS = [
    "key_sales_marketplace_sku", "country", "sku", "asin", "sales_region",
    "week_start_date", "avg_fee_per_unit", "baseline_median_fee_per_unit",
    "deviation_pct", "direction", "consecutive_weeks_flagged", "run_date",
]
COUNTRY_PREFIXES = {
    "US": "US | ", "CA": "CA | ", "GB": "GB | ", "DE": "DE | ",
    "FR": "FR | ", "ES": "ES | ", "IT": "IT | ", "MX": "MX | ", "BE": "BE | ",
}
```

**Pydantic model pattern** (`explore_fees.py` lines 79–103):
```python
class FeeRow(BaseModel):
    """Pydantic v2 model for a single output row matching D-11 column schema."""
    key_sales_marketplace_sku: str
    country: str
    sales_region: Optional[str]
    sku: Optional[str]
    asin: Optional[str]
    week_start_date: datetime.date
    avg_fee_per_unit: float
    currency: str
```

For Phase 2, define `AnomalyRow` following the same pattern — one field per D-18 column, `Optional` where NaN is possible (sku, asin, sales_region for amzn.gr.* keys), `sustained_shift: bool`.

**Auth import pattern** (`explore_fees.py` lines 139–193):
```python
# run_audit.py imports get_token() directly — do not copy the implementation
from explore_fees import get_token, run_dax, validate_value_count, process_pbi_rows, build_output_df, iso_to_week_start
```

**Main entrypoint pattern** (`explore_fees.py` lines 434–490):
```python
def main() -> None:
    """Run the Phase 1 fee exploration: authenticate, query PBI, transform, validate, write CSV."""
    load_dotenv()
    token = get_token()

    today = datetime.date.today()

    # Step 1...
    # Step 2...
    ...

if __name__ == "__main__":
    main()
```

Copy this shape verbatim for `run_audit.py`. The `main()` stages map to the architecture diagram in RESEARCH.md (INIT → AUTH → DECISION → BASELINE → DETECT → NARRATE → OUTPUT → ATTACH). Each stage is a named function call; `main()` orchestrates in sequence.

**DAX function pattern** (`explore_fees.py` lines 52–72):
```python
def build_fee_dax() -> str:
    """Return the DAX query that fetches the current fee schedule snapshot (is_latest = 1)."""
    return """EVALUATE
SUMMARIZECOLUMNS(
    'fact_fee_preview'[key_sales_marketplace_sku],
    'fact_fee_preview'[date_fee_preview],
    FILTER(ALL('fact_fee_preview'), 'fact_fee_preview'[is_latest] = 1),
    "avg_fee_per_unit", AVERAGE('fact_fee_preview'[expected_fulfillment_fee_per_unit])
)
ORDER BY 'fact_fee_preview'[key_sales_marketplace_sku]"""
```

For Phase 2, define `build_snapshot_dax()` (same structure, same is_latest filter) and `build_historical_dax(prefix: str)` (drops the is_latest filter, adds a LEFT() FILTER around SUMMARIZECOLUMNS — see RESEARCH.md Pattern 4 for exact DAX).

**CSV write pattern** (`explore_fees.py` lines 482–486):
```python
output_dir = pathlib.Path("output")
output_dir.mkdir(exist_ok=True)
output_path = output_dir / f"explore_fees_{today.strftime('%Y%m%d')}.csv"
output_df.to_csv(output_path, index=False)
print(f"CSV written: {output_path}")
```

For snapshot saves in `run_audit.py`:
```python
SNAPSHOTS_DIR.mkdir(exist_ok=True)
path = SNAPSHOTS_DIR / f"snapshot_{run_date.strftime('%Y%m%d')}.csv"
df.to_csv(path, index=False)
```

For append to `anomaly_history.csv`:
```python
write_header = not HISTORY_PATH.exists()
new_rows.to_csv(HISTORY_PATH, mode="a", header=write_header, index=False)
```

**Error handling pattern** (`explore_fees.py` lines 154–166, 186–189):
```python
if not tenant_id:
    raise SystemExit(
        "POWERBI_TENANT_ID environment variable is not set. "
        "Copy .env.example to .env and fill in your values."
    )
...
if "access_token" not in result:
    raise SystemExit(f"Auth failed: {result.get('error_description')}")
```

For Phase 2, add a guard at the start of `main()`:
```python
if config["CLICKUP_TASK_ID"] == "PLACEHOLDER":
    raise SystemExit(
        "CLICKUP_TASK_ID is not configured. "
        "Edit audit_config.json and replace 'PLACEHOLDER' with a real task ID."
    )
```

HTTP errors from ClickUp: call `r.raise_for_status()` — same pattern as `run_dax()` (`explore_fees.py` line 228).

**Validation pattern** (`explore_fees.py` lines 106–132):
```python
def validate_output_df(df: pd.DataFrame) -> None:
    """Validate the output DataFrame schema against FeeRow before writing CSV."""
    if df.empty:
        print("WARNING: Output DataFrame is empty — skipping schema validation.")
        return
    first_row = df.iloc[0].where(df.iloc[0].notna(), other=None).to_dict()
    if hasattr(first_row.get("week_start_date"), "date"):
        first_row["week_start_date"] = first_row["week_start_date"].date()
    FeeRow(**first_row)
    print(f"Schema validation: OK ({len(df)} rows)")
```

For Phase 2, create `validate_anomaly_df(df)` using `AnomalyRow` in place of `FeeRow`. Call before writing `anomaly_history.csv` rows (same T-04-02 gate principle).

---

### `tests/test_detection.py` (test, batch unit)

**Analog:** `tests/test_aggregation.py`

**File header and imports pattern** (`tests/test_aggregation.py` lines 1–26):
```python
"""
Unit tests for explore_fees.py — all 8 tests mapped in VALIDATION.md.

These tests are intentionally RED (ImportError) until Wave 2 creates explore_fees.py.
Do NOT skip or mark xfail — the tests must fail naturally to enforce TDD discipline.

Requirements covered: DATA-01, DATA-02, DETECT-01
"""
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

import datetime

from pydantic import ValidationError

from explore_fees import (
    run_dax,
    process_pbi_rows,
    ...
)
```

For `test_detection.py`, change the docstring header to reference Phase 2 requirements (DETECT-02, DETECT-03, OUT-01, OUT-02, OUT-03, ESC-01) and import from `run_audit`:
```python
from run_audit import (
    detect_anomalies,
    load_prior_counts,
    append_to_history,
    build_anomaly_json,
    generate_narrative,
    post_clickup_comment,
    attach_csv_to_task,
    load_config,
)
```

**Mock pattern** (`tests/test_aggregation.py` lines 34–77):
```python
mock_resp = MagicMock()
mock_resp.status_code = 200
mock_resp.json.return_value = mock_response_json

with patch("requests.post", return_value=mock_resp):
    result = run_dax(
        dax="EVALUATE TOPN(2, 'fact_fee_preview')",
        token="fake-bearer-token",
    )
```

For Phase 2 ClickUp tests, patch `requests.post` the same way. For Claude narrative tests, patch `anthropic.Anthropic` to return a `MagicMock` whose `.messages.create()` returns a mock with `.content[0].text = "fake narrative text"`.

**Assertion pattern** (`tests/test_aggregation.py` lines 78–80, 94–115):
```python
assert isinstance(result, list), "run_dax must return a list"
assert len(result) > 0, "run_dax must return at least one row"
assert isinstance(result[0], dict), "Each row must be a dict"
```

Use the same inline assertion message style: `"<function> must <expected behavior>"`. Include the actual value in the message where it adds debugging value (e.g., `f"got {len(result)}"` or `f"got {result.weekday()}"`).

**DataFrame construction in tests** (`tests/test_aggregation.py` lines 194–218):
```python
fee_df = pd.DataFrame({
    "key_sales_marketplace_sku": [
        "US | US-OHFB-001",
        "US | US-OHFB-002",
        "amzn.gr.ABCD1234",
    ],
    "year": [2026, 2026, 2026],
    "week_num": [1, 1, 1],
    "avg_fee_per_unit": [1.50, 2.00, 3.00],
})
```

For Phase 2 baseline tests, construct multi-week DataFrames with `week_start_date` as `pd.Timestamp` values:
```python
pd.DataFrame({
    "key_sales_marketplace_sku": ["US | US-OHFB-001"] * 8,
    "week_start_date": pd.date_range("2026-01-05", periods=8, freq="7D"),
    "avg_fee_per_unit": [3.0, 3.1, 2.9, 3.0, 3.05, 2.95, 3.0, 4.5],  # last row = anomaly
})
```

**temp file / tmp_path pattern** (new for Phase 2 — not in Phase 1 tests):

The consecutive count and history append tests need an isolated `anomaly_history.csv`. Use pytest's built-in `tmp_path` fixture — no additional setup needed:
```python
def test_consecutive_count_resets_on_gap(tmp_path, monkeypatch):
    monkeypatch.setattr("run_audit.HISTORY_PATH", tmp_path / "anomaly_history.csv")
    # write history CSV with a gap, then assert count resets to 1
```

**Section grouping pattern** (`tests/test_aggregation.py` lines 29–32, 118–121, 187–191, 298–303):
```python
# ---------------------------------------------------------------------------
# DATA-01: Power BI query shape and column contract
# ---------------------------------------------------------------------------
```

Mirror this for `test_detection.py`:
```python
# ---------------------------------------------------------------------------
# DETECT-02: Rolling baseline and anomaly threshold
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# DETECT-03: Consecutive count and sustained-shift classification
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# OUT-01 / ESC-01: Narrative generation and escalation prompt
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# OUT-02 / OUT-03: CSV attachment columns and config-driven task ID
# ---------------------------------------------------------------------------
```

---

### `tests/conftest.py` (extend existing, test fixture)

**Analog:** `tests/conftest.py` (the file itself — add fixtures without removing existing ones)

**Existing fixture structure** (`tests/conftest.py` lines 1–61):
```python
"""Shared pytest fixtures for AI Amazon Fee Auditor tests."""
import pytest

@pytest.fixture
def sample_pbi_rows():
    """..."""
    return [...]

@pytest.fixture
def sample_sku_rows():
    """..."""
    return [...]
```

Append new Phase 2 fixtures at the bottom of the file. Do not modify the existing fixtures. New fixtures to add:

```python
@pytest.fixture
def sample_snapshot_df():
    """8-week snapshot DataFrame for rolling baseline tests.

    Key: "US | US-OHFB-001". Weeks 1-7 have stable fee ~3.00;
    week 8 spikes to 4.50 — a 47% deviation, well above 15% threshold.
    """
    import pandas as pd
    return pd.DataFrame({
        "key_sales_marketplace_sku": ["US | US-OHFB-001"] * 8,
        "week_start_date": pd.date_range("2026-01-05", periods=8, freq="7D"),
        "avg_fee_per_unit": [3.0, 3.1, 2.9, 3.0, 3.05, 2.95, 3.0, 4.5],
    })


@pytest.fixture
def sample_audit_config(tmp_path):
    """Write a temporary audit_config.json and return its path and parsed dict."""
    import json, pathlib
    config = {
        "THRESHOLD_PCT": 15,
        "CLICKUP_TASK_ID": "TEST_TASK_123",
        "RECIPIENTS": [],
        "SUSTAINED_SHIFT_N": 4,
    }
    cfg_path = tmp_path / "audit_config.json"
    cfg_path.write_text(json.dumps(config))
    return cfg_path, config


@pytest.fixture
def sample_anomaly_df():
    """Minimal anomaly DataFrame matching D-18 columns for CSV attachment tests."""
    import pandas as pd
    import datetime
    return pd.DataFrame([{
        "key_sales_marketplace_sku": "US | US-OHFB-001",
        "country": "US",
        "sales_region": "US",
        "sku": "US-OHFB-001",
        "asin": "B0EXAMPLE01",
        "week_start_date": datetime.date(2026, 5, 26),
        "avg_fee_per_unit": 4.50,
        "baseline_median_fee_per_unit": 3.00,
        "deviation_pct": 50.0,
        "direction": "increase",
        "sustained_shift": False,
    }])
```

---

### `audit_config.json` (config, no analog)

No close analog exists in the codebase. The `.planning/config.json` is a GSD workflow config, not a runtime app config — do not use it as a pattern.

Use the exact default structure from RESEARCH.md (Code Examples section):
```json
{
    "THRESHOLD_PCT": 15,
    "CLICKUP_TASK_ID": "PLACEHOLDER",
    "RECIPIENTS": [],
    "SUSTAINED_SHIFT_N": 4
}
```

Load pattern in `run_audit.py` (also from RESEARCH.md):
```python
import json
with open("audit_config.json") as f:
    config = json.load(f)
```

Type-check on load for security (ASVS V5):
```python
assert isinstance(config["THRESHOLD_PCT"], (int, float)), "THRESHOLD_PCT must be numeric"
assert isinstance(config["SUSTAINED_SHIFT_N"], int), "SUSTAINED_SHIFT_N must be int"
assert isinstance(config["CLICKUP_TASK_ID"], str), "CLICKUP_TASK_ID must be str"
assert isinstance(config["RECIPIENTS"], list), "RECIPIENTS must be list"
```

---

### `snapshots/.gitkeep` + `.gitignore` additions (directory marker, config)

**Analog:** `output/.gitkeep` + `.gitignore` lines 2–3

Existing `.gitignore` pattern to copy (`.gitignore` lines 2–3):
```
output/*
!output/.gitkeep
```

Add the equivalent for snapshots:
```
snapshots/*
!snapshots/.gitkeep
```

The `snapshots/.gitkeep` file itself is empty — same as `output/.gitkeep`. Create it as an empty file. `anomaly_history.csv` is already covered by the existing `*.csv` rule (`.gitignore` line 7).

---

### `requirements.txt` (config, modify existing)

**Analog:** `requirements.txt` itself — append one line following the existing pin format.

Existing format (`requirements.txt` lines 1–7):
```
msal==1.36.0
requests==2.32.3
pandas==2.2.3
numpy==2.2.4
python-dotenv==1.0.1
pydantic==2.13.4
pytest==9.0.3
```

Append:
```
anthropic==0.101.0
```

---

## Shared Patterns

### Auth — load_dotenv + env var guard
**Source:** `explore_fees.py` lines 139–166 (`get_token()`)
**Apply to:** `run_audit.py` `main()` and any function that reads `CLICKUP_API_KEY` or `ANTHROPIC_API_KEY`

Pattern: call `load_dotenv()` once at the top of `main()`, then use `os.environ.get()` with a `raise SystemExit(...)` guard for missing required values. Never use `os.environ["KEY"]` directly without a guard.

```python
load_dotenv()
clickup_key = os.environ.get("CLICKUP_API_KEY")
if not clickup_key:
    raise SystemExit(
        "CLICKUP_API_KEY environment variable is not set. "
        "Copy .env.example to .env and fill in your values."
    )
```

### HTTP error handling — raise_for_status
**Source:** `explore_fees.py` line 228 (`run_dax()`), `skeleton.py` line 58
**Apply to:** `post_clickup_comment()`, `attach_csv_to_task()` in `run_audit.py`

```python
r = requests.post(url, headers=headers, json=body, timeout=30)
r.raise_for_status()
return r.json()
```

Always include `timeout=` (30s for comment, 60s for file attachment). Never call `.json()` before `.raise_for_status()`.

### Pydantic schema gate before file write
**Source:** `explore_fees.py` lines 106–132 (`validate_output_df()`)
**Apply to:** `run_audit.py` before writing `anomaly_history.csv` rows and before building the CSV attachment buffer

Pattern: instantiate the Pydantic model with the first row's dict. If `ValidationError` is raised, halt before any file is written. Replace `NaN` with `None` for `Optional` fields (see `explore_fees.py` line 127 for the `.where(df.iloc[0].notna(), other=None)` idiom).

### stdout progress printing
**Source:** `explore_fees.py` lines 459–486
**Apply to:** All stages in `run_audit.py main()`

Each stage prints a one-line progress message before and/or after its key operation:
```python
print(f"Querying current fee schedule snapshot (is_latest=1): {today}")
print(f"Fee rows fetched: {len(fee_df)}")
print(f"CSV written: {output_path}")
```

For Phase 2, follow the same pattern per stage (e.g., `"Snapshot saved: snapshots/snapshot_20260528.csv"`, `"Anomalies detected: 12 increases, 3 reductions"`, `"ClickUp comment posted: task TEST_TASK_123"`).

### pathlib.Path for all filesystem operations
**Source:** `explore_fees.py` lines 9, 483–486
**Apply to:** `snapshots/` directory creation, `anomaly_history.csv` path, `audit_config.json` open

Never use string concatenation for file paths. Always use `pathlib.Path`:
```python
output_dir = pathlib.Path("output")
output_dir.mkdir(exist_ok=True)
output_path = output_dir / f"explore_fees_{today.strftime('%Y%m%d')}.csv"
```

### Mocking pattern for external API calls in tests
**Source:** `tests/test_aggregation.py` lines 34–77
**Apply to:** All tests in `tests/test_detection.py` that touch ClickUp API or Anthropic API

```python
mock_resp = MagicMock()
mock_resp.status_code = 200
mock_resp.json.return_value = {"id": "comment_123"}

with patch("requests.post", return_value=mock_resp):
    result = post_clickup_comment("TEST_TASK_123", "comment text", "pk_fake")

assert result["id"] == "comment_123"
```

For Anthropic mock:
```python
mock_message = MagicMock()
mock_message.content = [MagicMock(text="Fake narrative. Reply YES to this comment to open an investigation task for the top flagged SKUs.")]

with patch("anthropic.Anthropic") as mock_client:
    mock_client.return_value.messages.create.return_value = mock_message
    result = generate_narrative({"run_date": "2026-05-28", "total_scanned": 100, ...})

assert "Reply YES" in result
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `audit_config.json` | config | — | No runtime JSON config exists in the codebase; `.planning/config.json` is a GSD tool config, not an app runtime config — unrelated pattern |

---

## Metadata

**Analog search scope:** project root, `tests/`, `.planning/` (config only)
**Files scanned:** `explore_fees.py`, `tests/test_aggregation.py`, `tests/conftest.py`, `skeleton.py`, `requirements.txt`, `.gitignore`, `.planning/config.json`
**Pattern extraction date:** 2026-05-28
