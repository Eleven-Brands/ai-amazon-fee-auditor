# Phase 1: Data Foundation - Research

**Researched:** 2026-05-27
**Domain:** Power BI REST API + MSAL device-code auth + pandas weekly aggregation
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- D-01: Data access = Power BI REST API with custom DAX on `fact_fee_preview`. BigQuery direct query is NOT the approach.
- D-02: Date column = `fact_fee_preview[date_fee_preview]` (daily granularity, range confirmed as 2023-07-01 → present).
- D-03: Fee metric = `fact_fee_preview[expected_fulfillment_fee_per_unit]` — already per-unit.
- D-04: Weekly baseline granularity = average of all daily fee values within each calendar week per SKU/country key.
- D-05: Include all 5,274 distinct keys (including `amzn.gr.*` prefixed keys). Do not filter.
- D-06: ASIN lookup via join `fact_fee_preview[key_sales_marketplace_sku]` → `SKUs[Key Column: Country | SKU]`. ASIN = `SKUs[ASIN]`. Sales Region = `SKUs[Sales Region]`. `amzn.gr.*` keys do NOT join — count and log, do not fail.
- D-07: Workspace ID = `47144ee2-02f9-4408-9ed5-57acf6a9f44d`
- D-08: Dataset ID = `a95798aa-a3ec-4a89-9816-63cde534cdd7`
- D-09: Auth = MSAL device-code flow. Env vars `POWERBI_TENANT_ID` and `POWERBI_CLIENT_ID` already set. Token cached at `~/.claude/powerbi_token_cache.json`.
- D-10: Deliverable = `explore_fees.py` + one exploration CSV. No Jupyter notebook.
- D-11: CSV columns: `key_sales_marketplace_sku`, `country`, `sales_region`, `sku`, `asin` (null for unjoined), `week_start_date`, `avg_fee_per_unit`, `currency`.
- D-13: 16-week lookback window for the exploration CSV.
- D-17/D-18: No BigQuery. State = local CSV files only (`run_YYYYMMDD.csv`, `anomaly_history.csv`).

### Claude's Discretion

- DAX query structure (SUMMARIZECOLUMNS vs CALCULATETABLE, ISO week vs calendar week).
- File naming convention for output CSVs.
- Python package choices within the approved stack (pandas, requests, msal).

### Deferred Ideas (OUT OF SCOPE)

- Sales Region-level vs country-level baseline grouping for EU SKUs — Phase 2 calibration.
- Understanding what `amzn.gr.*` keys represent.
- Dual-gate threshold (pct AND absolute dollar floor) — v2 scope.
- Seasonal Q4 baseline — v2 scope.

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Agent queries Power BI for FBA Fulfillment Fee by SKU/ASIN (weekly granularity, rolling 8-12 week window) via `powerbi-query` skill | DAX SUMMARIZECOLUMNS pattern with WEEKNUM(date,21) produces weekly averages per key; `executeQueries` row limit math confirms single-query feasibility for 16-week window at 5,274 keys |
| DATA-02 | Queries segment data by Sales Region (US, UK, CA, EU, MX) | `SKUs[Sales Region]` dimension confirmed in schema; join key is `SKUs[Key Column: Country | SKU]`; country-level granularity preserved in `fact_fee_preview` |
| DETECT-01 | System calculates rolling 8-week median baseline per SKU per Sales Region, normalized by units shipped (fee per unit) | `fact_fee_preview[expected_fulfillment_fee_per_unit]` is already per-unit — no units-sold normalization needed; pandas `rolling(8).median()` on weekly grouped data delivers the baseline; 16-week CSV provides the calibration input Phase 2 needs |

</phase_requirements>

---

## Summary

Phase 1 produces a single Python script (`explore_fees.py`) that authenticates against the Power BI REST API, queries `fact_fee_preview` for 16 weeks of daily fee data, aggregates it to weekly averages per SKU/country, joins the `SKUs` dimension for ASIN and Sales Region labels, and writes the result to a CSV. The script is exploratory — its output is the calibration input for Phase 2's detection threshold.

The critical architectural insight for planning: **the weekly aggregation MUST happen inside the DAX query, not in Python**. Fetching raw daily rows for 5,274 keys × 16 weeks × 7 days would produce ~590K rows × 3 columns = ~1.77M values — exceeding the executeQueries hard limit of 1,000,000 values per query. A SUMMARIZECOLUMNS query that groups by key + ISO week produces ~84,384 rows × 5 columns = ~421,920 values, safely within limits.

The MSAL token cache pattern from the `powerbi-query` skill works as-is. `acquire_token_silent` handles automatic refresh from the cached refresh token. The only scenario requiring user interaction is when the refresh token itself expires (inactive for 90 days), which is handled by falling back to device-code flow. The script must detect this case and print a clear re-auth instruction rather than crashing silently.

**Primary recommendation:** Use a single DAX SUMMARIZECOLUMNS query with WEEKNUM(..., 21) for ISO week grouping and AVERAGE aggregation on `expected_fulfillment_fee_per_unit`. Use the `/groups/{groupId}/datasets/{datasetId}/executeQueries` endpoint (not the non-group variant) since the dataset lives in a workspace.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Authentication (MSAL token acquire/refresh) | Python script | — | Delegated auth flow runs locally; no server needed |
| DAX query construction and pagination | Python script | Power BI DAX engine | Script builds the DAX string; PBI engine evaluates it |
| Weekly aggregation (daily rows → weekly avg) | Power BI DAX engine | — | Must happen in DAX to avoid row limit violation; DAX WEEKNUM inside SUMMARIZECOLUMNS |
| SKU/ASIN dimension join | Python (pandas) | Power BI DAX engine (join available) | Two-query approach in Python: avoids value-count blowup; SUMMARIZECOLUMNS with joined SKUs adds 3+ columns pushing total values ~60% higher; Pattern 5 documents this decision |
| Currency extraction per key | Power BI DAX engine | — | Currency is a property of the key/country; DAX can include it as a dimension column |
| ISO week → week_start_date mapping | Python (pandas) | — | Convert ISO year + week number to Monday date after data lands in pandas |
| `amzn.gr.*` key detection and logging | Python script | — | Simple string prefix check on the key column after the join |
| CSV output writing | Python (pandas) | — | `df.to_csv()` is sufficient; no external dependency |
| Rolling median baseline (Phase 2 preview) | Python (pandas) | — | `groupby().rolling().median()` — not implemented in Phase 1, but CSV schema must support it |

---

## Standard Stack

### Core (Phase 1 only)

| Library | Version (installed) | Purpose | Why Standard |
|---------|---------------------|---------|--------------|
| `msal` | `1.36.0` [VERIFIED: pip registry] | Azure AD OAuth2 device-code token acquire + silent refresh | Microsoft-official MSAL for Python; `acquire_token_silent` handles token refresh from cache automatically |
| `requests` | `2.32.3` [VERIFIED: pip registry] | HTTP POST to Power BI executeQueries endpoint | Battle-tested; synchronous calls are sufficient for a sequential exploration script |
| `pandas` | `2.2.3` [VERIFIED: pip registry] | ISO week derivation, data join in Python, CSV write | Installed on this machine; `dt.isocalendar()` gives ISO year + week; team familiarity |
| `python-dotenv` | `1.0.1` [VERIFIED: pip registry] | Load `.env` for local credentials | Keeps credentials out of code; standard local dev pattern |
| `pydantic` | `2.13.4` [VERIFIED: pip registry] | Validate PBI API response schema before processing | Fail fast if columns are missing; prevents silent data corruption downstream |
| `pytest` | `9.0.3` [VERIFIED: pip registry] | Unit tests for aggregation logic and CSV schema validation | Installed fresh this session; baseline calculation logic must be unit-testable without live API |
| `numpy` | `2.2.4` [VERIFIED: pip registry] | Transitive dep of pandas; numerical operations | Pinned for Windows compatibility; already installed |

### Not Needed in Phase 1

| Library | Reason Excluded |
|---------|-----------------|
| `scipy` | Phase 1 is exploratory CSV only — no z-score detection yet |
| `jinja2` | No HTML output in Phase 1 |
| `google-cloud-bigquery` / `pandas-gbq` | Dropped entirely (D-17) |
| `anthropic` SDK | No Claude narrative call in Phase 1 |

**Installation (what is NOT yet installed):**
```bash
pip install pytest==9.0.3
```
Everything else is already installed on this machine.

---

## Package Legitimacy Audit

> slopcheck run: 2026-05-27 (slopcheck 0.6.1)

| Package | Registry | slopcheck | Disposition |
|---------|----------|-----------|-------------|
| `msal` | PyPI | [OK] | Approved — Microsoft-official Azure SDK |
| `requests` | PyPI | [OK] | Approved — 15+ year established package |
| `pandas` | PyPI | [OK] | Approved — standard data library |
| `python-dotenv` | PyPI | [OK] (noted: name looks like LLM bait but is established) | Approved |
| `pydantic` | PyPI | [OK] | Approved |
| `pytest` | PyPI | [OK] | Approved |
| `numpy` | PyPI | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

---

## Architecture Patterns

### System Architecture Diagram

```
[.env / env vars]
    |
    v (TENANT_ID, CLIENT_ID)
[MSAL auth block]
    | acquire_token_silent → token cache read (~/.claude/powerbi_token_cache.json)
    | on miss / expiry → device-code flow (user interaction required once)
    v
[ACCESS TOKEN]
    |
    v
[run_dax(dax_query)] ← DAX string constructed in Python
    | POST /v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/executeQueries
    v
[Power BI DAX Engine]
    | SUMMARIZECOLUMNS on fact_fee_preview + SKUs
    | weekly aggregation via WEEKNUM(date, 21)
    | AVERAGE of expected_fulfillment_fee_per_unit per key+week
    v
[JSON response rows]   (≤ 1M values — within hard limit)
    |
    v (pandas DataFrame)
[derive_week_start_date()]   ISO year + week → Monday date (pandas)
    |
[detect_unjoined_keys()]    flag amzn.gr.* rows; log count
    |
[validate_schema()]          pydantic check required columns exist
    |
    v
[write CSV]   explore_fees_YYYYMMDD.csv
```

### Recommended Project Structure

```
AI Amazon Fee Auditor/
├── explore_fees.py          # Phase 1 deliverable — exploration script
├── .env                     # POWERBI_TENANT_ID, POWERBI_CLIENT_ID (git-ignored)
├── .env.example             # Template — committed to git
├── .gitignore               # .env, *.csv, __pycache__
├── requirements.txt         # Pinned versions
├── tests/
│   ├── __init__.py
│   ├── test_aggregation.py  # Unit tests for weekly avg logic
│   └── conftest.py          # Fixtures: sample daily rows DataFrame
└── output/                  # Git-ignored; CSVs written here
    └── explore_fees_YYYYMMDD.csv
```

### Pattern 1: MSAL Device-Code Auth (verbatim from `powerbi-query` skill)

**What:** Acquire access token with automatic silent refresh. Fall back to device-code only when refresh token is missing or expired.

**When to use:** Every script invocation. The `acquire_token_silent` call handles the common case (token still valid or refresh available). Device-code flow fires only on first use or after 90-day inactivity.

```python
# Source: ~/.claude/commands/powerbi-query.md — Authentication Helper
import msal, os

TENANT_ID  = os.environ["POWERBI_TENANT_ID"]
CLIENT_ID  = os.environ["POWERBI_CLIENT_ID"]
SCOPES     = ["https://analysis.windows.net/powerbi/api/Dataset.Read.All"]
CACHE_PATH = os.path.expanduser("~/.claude/powerbi_token_cache.json")

cache = msal.SerializableTokenCache()
if os.path.exists(CACHE_PATH):
    cache.deserialize(open(CACHE_PATH).read())

app = msal.PublicClientApplication(
    CLIENT_ID,
    authority=f"https://login.microsoftonline.com/{TENANT_ID}",
    token_cache=cache,
)

result = None
accounts = app.get_accounts()
if accounts:
    result = app.acquire_token_silent(SCOPES, account=accounts[0])

if not result or "access_token" not in result:
    # Refresh token expired or no cache — requires user interaction
    flow = app.initiate_device_flow(scopes=SCOPES)
    print(flow["message"])  # "Go to https://microsoft.com/devicelogin and enter code XXXXX"
    result = app.acquire_token_by_device_flow(flow)

if "access_token" not in result:
    raise SystemExit(f"Auth failed: {result.get('error_description')}")

# Persist updated cache (may contain refreshed tokens)
open(CACHE_PATH, "w").write(cache.serialize())
TOKEN = result["access_token"]
```

**Token lifetime facts** [VERIFIED: Microsoft Entra docs]:
- Access token: ~1 hour (short-lived, MSAL refreshes automatically)
- Refresh token: up to 90 days with sliding window on use; `acquire_token_silent` uses it silently
- If the refresh token itself expires (90 days of no use), device-code re-authentication is required

### Pattern 2: executeQueries-in-Group endpoint

**What:** The correct endpoint for datasets that live in a named workspace (not "My Workspace").

**When to use:** Always for OrganiHaus datasets — they live in workspace `47144ee2-...`.

```python
# Source: learn.microsoft.com/en-us/rest/api/power-bi/datasets/execute-queries-in-group
def run_dax(workspace_id: str, dataset_id: str, dax: str, token: str) -> list[dict]:
    url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{workspace_id}"
        f"/datasets/{dataset_id}/executeQueries"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    body = {
        "queries": [{"query": dax}],
        "serializerSettings": {"includeNulls": True},
    }
    r = requests.post(url, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    result = r.json()["results"][0]
    # Check for soft error (200 OK but partial results due to row limit)
    if "error" in result and result["error"]:
        raise RuntimeError(f"DAX query soft error: {result['error']}")
    return result["tables"][0].get("rows", [])
```

**Critical:** The API returns HTTP 200 even when it hits the row limit — but includes an `error` field in the result JSON. Always check `result["error"]` after parsing, not just `r.status_code`.

### Pattern 3: DAX Weekly Aggregation Query

**What:** Single DAX query that aggregates daily `fact_fee_preview` rows into weekly averages per key, with ISO week numbering. Joins `SKUs` dimension inline.

**Decision: ISO week (WEEKNUM type 21) recommended** over calendar week because:
- ISO week is the standard in EU markets (DE, FR, ES, IT) — aligns with how OrganiHaus reports elsewhere
- pandas `dt.isocalendar()` maps directly to ISO year/week with no conversion math
- Prevents week 1 boundary ambiguity at year-end

**Value count calculation** [VERIFIED: Microsoft Learn executeQueries docs]:
- Output columns: `key_sales_marketplace_sku`, `iso_year`, `iso_week`, `avg_fee`, `currency` = 5 columns
- Output rows: 5,274 keys × 16 weeks = 84,384 rows
- Total values: 84,384 × 5 = 421,920 — well within the 1,000,000 value limit
- Estimated response size: ~421K values × ~20 bytes avg = ~8.4MB — within the 15MB limit

```dax
-- Source: [ASSUMED] — based on DAX pattern research and confirmed table/column names from live session
EVALUATE
SUMMARIZECOLUMNS(
    'fact_fee_preview'[key_sales_marketplace_sku],
    WEEKNUM('fact_fee_preview'[date_fee_preview], 21),
    YEAR('fact_fee_preview'[date_fee_preview]),
    "avg_fee_per_unit", AVERAGE('fact_fee_preview'[expected_fulfillment_fee_per_unit])
)
ORDER BY 'fact_fee_preview'[key_sales_marketplace_sku], [YEAR], [WEEKNUM]
```

**Note on WEEKNUM vs ISOWEEKNUM in DAX:** DAX has `WEEKNUM(date, 21)` for ISO 8601 week — this is the `return_type=21` parameter documented in the DAX WEEKNUM function reference. There is no separate `ISOWEEKNUM` function in DAX (unlike Excel which has one). `WEEKNUM(date, 21)` IS the ISO week function.

**Note on currency:** `fact_fee_preview` does not expose a currency column directly based on schema investigation. Currency is implied by the country prefix in `key_sales_marketplace_sku` (e.g., `US | ...` → USD, `GB | ...` → GBP, `DE/FR/ES/IT | ...` → EUR, `CA | ...` → CAD, `MX | ...` → MXN). The `country` column can be derived in Python from the key prefix and mapped to a currency dictionary.

### Pattern 4: Pandas ISO Week Derivation and Weekly Key Construction

**What:** After receiving DAX results, derive `week_start_date` (Monday of each ISO week) and the 2-letter `country` code from the key prefix.

```python
# Source: pandas documentation dt.isocalendar()
import pandas as pd

def process_pbi_rows(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    # Rename PBI column references (e.g., "fact_fee_preview[key_sales_marketplace_sku]")
    df.columns = [c.split("[")[-1].rstrip("]") for c in df.columns]

    # Derive week_start_date from ISO year + week number
    # ISO week Monday = Jan 4 of iso_year + (iso_week - 1) * 7 days, adjusted to Monday
    df["week_start_date"] = df.apply(
        lambda r: pd.Timestamp.fromisocalendar(int(r["YEAR"]), int(r["WEEKNUM"]), 1),
        axis=1,
    )

    # Derive country from key prefix: "US | US-OHFB-..." → "US"
    df["country"] = df["key_sales_marketplace_sku"].str.split(" | ").str[0]

    return df
```

**`pd.Timestamp.fromisocalendar(year, week, 1)`** returns the Monday of a given ISO year+week — this is the canonical way to convert ISO week back to a date in pandas. [ASSUMED — verified against pandas docs behavior but not via Context7 in this session]

### Pattern 5: SKU Dimension Join in Python

**What:** After fetching the weekly aggregated data, join the `SKUs` table (separate DAX query) to get `sku`, `asin`, and `sales_region`.

**Why in Python, not DAX:** Attempting to join two tables inside a single SUMMARIZECOLUMNS DAX is valid but adds column count (increasing value count and hitting the 1M limit faster). Keeping it as two separate queries and joining in pandas is cleaner and more debuggable.

```python
# Query 1: weekly fee aggregation (Pattern 3 above)
# Query 2: SKU dimension — all keys with their ASIN, SKU, Sales Region
SKU_QUERY = """
EVALUATE
SUMMARIZECOLUMNS(
    'SKUs'[Key Column: Country | SKU],
    'SKUs'[SKU],
    'SKUs'[ASIN],
    'SKUs'[Sales Region]
)
"""
# Source: column names confirmed live during context-gathering session
sku_rows = run_dax(WORKSPACE_ID, DATASET_ID, SKU_QUERY, token)
sku_df = pd.DataFrame(sku_rows)

# Join on key
merged = fee_df.merge(
    sku_df,
    left_on="key_sales_marketplace_sku",
    right_on="SKUs[Key Column: Country | SKU]",
    how="left"
)

# amzn.gr.* keys will have NaN for ASIN, SKU, Sales Region after left join
unjoined_mask = merged["SKUs[ASIN]"].isna()
unjoined_count = unjoined_mask.sum()
print(f"Unjoined keys (amzn.gr.*): {unjoined_count}")
```

**SKU query value count:** ~5,274 rows × 4 columns = ~21,096 values — trivially within limits.

### Anti-Patterns to Avoid

- **Fetching raw daily rows into Python:** Would produce ~1.77M values — exceeds the 1M hard limit. The DAX engine must aggregate before returning.
- **Using the non-group executeQueries endpoint** (`/datasets/{id}/executeQueries`): Works only for "My Workspace" datasets. OrganiHaus datasets are in a named workspace — use the group endpoint.
- **Checking only HTTP status code for errors:** The executeQueries API returns HTTP 200 even when it hits the row limit, with an `error` field in the JSON body. Always check `result["error"]`.
- **Ignoring `includeNulls: true`:** Without this, PBI silently drops rows where `expected_fulfillment_fee_per_unit` is NULL. These would be invisible data gaps.
- **Using `dt.week` (deprecated):** `pandas.Series.dt.week` is deprecated in pandas 2.x. Use `dt.isocalendar().week` instead.
- **Inline SKU join inside the main DAX query:** Adds 3+ columns, increasing value count by ~60%. Keep as two separate queries joined in Python.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Token acquisition + refresh | Custom OAuth2 HTTP code | `msal.PublicClientApplication.acquire_token_silent` | MSAL handles token expiry, refresh, and cache serialization; hand-rolled OAuth misses edge cases |
| ISO week-to-date conversion | Date arithmetic from scratch | `pd.Timestamp.fromisocalendar(year, week, 1)` | Year-boundary weeks (week 52/53 → week 1 of next year) are a known source of off-by-one bugs |
| CSV schema validation | Manual column presence checks | `pydantic` BaseModel with field validation | Catches missing columns, wrong types, and null fields in one place; generates clear error messages |
| DAX row limit detection | Counting rows after fetch | Check `result["error"]` field in JSON response | The API soft-fails at 200 OK — you will not know you got truncated data unless you check the error field |

---

## Common Pitfalls

### Pitfall 1: Row/Value Limit Exceeded on Raw Daily Fetch

**What goes wrong:** Script queries `fact_fee_preview` for raw daily rows filtered by date range. Returns HTTP 200 with partial data and a JSON error field. Script silently processes incomplete data, producing an exploration CSV that appears valid but covers fewer than 16 weeks for many SKUs.

**Why it happens:** 5,274 keys × 112 days = 591,088 rows × 3 columns = 1.77M values — 77% over the 1M limit. The API truncates silently at HTTP 200.

**How to avoid:** Aggregate to weekly in DAX (SUMMARIZECOLUMNS with WEEKNUM). Verify value count math before writing the query: `(keys × weeks × columns) < 1,000,000`.

**Warning signs:** `result["error"]` field is non-null after parsing the response JSON; fewer distinct weeks than expected in the output CSV.

---

### Pitfall 2: Wrong executeQueries Endpoint (No Group)

**What goes wrong:** Script uses `/datasets/{datasetId}/executeQueries` (no group). Returns 404 or 403 because the dataset lives in workspace `47144ee2-...`, not "My Workspace".

**Why it happens:** Training data and older examples often show the non-group URL. The `powerbi-query` skill uses the group endpoint correctly — follow it exactly.

**How to avoid:** URL must be: `https://api.powerbi.com/v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/executeQueries`

---

### Pitfall 3: Refresh Token Expiry During Batch Run

**What goes wrong:** Script starts, `acquire_token_silent` returns `None` (refresh token expired after >90 days idle). Script crashes with an unhandled exception or unclear error.

**Why it happens:** Device-code flow tokens have a 90-day inactivity window. If the machine has not run a PBI query in 90+ days, the cached refresh token is invalid.

**How to avoid:** The auth block already handles this correctly (falls back to device-code flow). The issue is the script must be run interactively (not headless via Task Scheduler) to complete the device-code re-auth. Phase 1 is exploratory and always run interactively — this is fine. Add a clear print statement when device-code is triggered: `"Token expired or missing — re-authentication required. Complete the device-code login, then re-run the script."`

---

### Pitfall 4: `dt.week` Deprecation Warning in pandas 2.x

**What goes wrong:** Code uses `df["date"].dt.week` to extract ISO week number. pandas 2.x raises a `FutureWarning` and in pandas 3.x this attribute is removed entirely.

**Why it happens:** Old examples and training data often use `dt.week`.

**How to avoid:** Use `df["date"].dt.isocalendar().week` (returns a Series of int). For year-safe ISO week key: `df["date"].dt.isocalendar()[["year", "week"]]`.

---

### Pitfall 5: DAX Column Name Mangling in Response JSON

**What goes wrong:** PBI API returns columns as `"fact_fee_preview[key_sales_marketplace_sku]"` (fully qualified) or `"[avg_fee_per_unit]"` (computed measures, bracket-only). Accessing `row["key_sales_marketplace_sku"]` raises KeyError.

**Why it happens:** The executeQueries API always uses these name formats. Documented in official Microsoft Learn docs.

**How to avoid:** Strip qualifications after loading into pandas:
```python
df.columns = [c.split("[")[-1].rstrip("]") for c in df.columns]
```
Do this as the first transformation after `pd.DataFrame(rows)`.

---

### Pitfall 6: Currency Heterogeneity — Averaging Across Currencies

**What goes wrong:** Phase 2's baseline comparison makes sense only within a currency. If the CSV mixes EUR and GBP rows for an EU-grouped SKU, a median of EUR and GBP values produces a meaningless number.

**Why it happens:** `fact_fee_preview` is at country level — DE and GB are separate rows with different currencies. Phase 1 preserves country-level granularity (D-16), so this is correctly handled. The risk is in Phase 2 if it groups by `sales_region` instead of `country`.

**How to avoid in Phase 1:** The `country` column in the output CSV makes the currency unambiguous (country → currency is a 1:1 map). Include a `currency` column derived from the country code:
```python
COUNTRY_CURRENCY = {
    "US": "USD", "CA": "CAD", "GB": "GBP", "MX": "MXN",
    "DE": "EUR", "FR": "EUR", "ES": "EUR", "IT": "EUR",
}
df["currency"] = df["country"].map(COUNTRY_CURRENCY).fillna("UNKNOWN")
```
This satisfies D-11 (currency column required) and documents the assumption clearly.

---

### Pitfall 7: `amzn.gr.*` Keys Causing Join Noise

**What goes wrong:** `amzn.gr.*` keys (Amazon bundle/grouping codes) do not join to `SKUs`. A `merge(..., how="left")` leaves `asin`, `sku`, and `sales_region` as NaN for these rows. If code downstream assumes non-null `sku`, it crashes.

**How to avoid:** After the join, explicitly detect and log unjoined rows. Do not drop them — D-05 says audit everything. Write them to the CSV with `asin=null`, `sku=null`, `sales_region=null`. The exploration output should include a summary line: `"X of 5,274 keys are amzn.gr.* (unjoined to SKUs dimension)"`.

---

## Code Examples

### Full Auth + Query Pattern

```python
# Source: ~/.claude/commands/powerbi-query.md (Authentication Helper + DAX Query Execution)
import msal, os, requests
import pandas as pd

WORKSPACE_ID = "47144ee2-02f9-4408-9ed5-57acf6a9f44d"
DATASET_ID   = "a95798aa-a3ec-4a89-9816-63cde534cdd7"
SCOPES       = ["https://analysis.windows.net/powerbi/api/Dataset.Read.All"]
CACHE_PATH   = os.path.expanduser("~/.claude/powerbi_token_cache.json")

def get_token() -> str:
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_PATH):
        cache.deserialize(open(CACHE_PATH).read())

    app = msal.PublicClientApplication(
        os.environ["POWERBI_CLIENT_ID"],
        authority=f"https://login.microsoftonline.com/{os.environ['POWERBI_TENANT_ID']}",
        token_cache=cache,
    )

    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result or "access_token" not in result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise SystemExit(f"Auth failed: {result.get('error_description')}")

    open(CACHE_PATH, "w").write(cache.serialize())
    return result["access_token"]


def run_dax(dax: str, token: str) -> list[dict]:
    url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}"
        f"/datasets/{DATASET_ID}/executeQueries"
    )
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={"queries": [{"query": dax}], "serializerSettings": {"includeNulls": True}},
        timeout=120,
    )
    r.raise_for_status()
    result = r.json()["results"][0]
    if result.get("error"):
        raise RuntimeError(f"DAX query error: {result['error']}")
    return result["tables"][0].get("rows", [])
```

### Weekly Fee DAX Query (recommended)

```dax
-- [ASSUMED] — table and column names confirmed live; WEEKNUM(date,21) is ISO 8601 week
-- Value count: 5274 keys × 16 weeks × 5 cols = ~421,920 — within 1M limit
EVALUATE
SUMMARIZECOLUMNS(
    'fact_fee_preview'[key_sales_marketplace_sku],
    YEAR('fact_fee_preview'[date_fee_preview]),
    WEEKNUM('fact_fee_preview'[date_fee_preview], 21),
    FILTER(
        'fact_fee_preview',
        'fact_fee_preview'[date_fee_preview] >= DATE(2026, 1, 27)
        && 'fact_fee_preview'[date_fee_preview] <= DATE(2026, 5, 27)
    ),
    "avg_fee_per_unit", AVERAGE('fact_fee_preview'[expected_fulfillment_fee_per_unit])
)
ORDER BY
    'fact_fee_preview'[key_sales_marketplace_sku],
    [YEAR],
    [WEEKNUM]
```

Note: Replace date literals with Python-computed `cutoff_start` / `today` strings at script runtime.

### Pandas ISO Week → week_start_date

```python
# Source: [ASSUMED] — pd.Timestamp.fromisocalendar documented in pandas API reference
def iso_to_week_start(iso_year: int, iso_week: int) -> pd.Timestamp:
    """Return the Monday date for a given ISO year+week."""
    return pd.Timestamp.fromisocalendar(int(iso_year), int(iso_week), 1)

df["week_start_date"] = df.apply(
    lambda r: iso_to_week_start(r["YEAR"], r["WEEKNUM"]), axis=1
)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pandas.Series.dt.week` | `dt.isocalendar().week` | pandas 1.1.0 deprecated, 2.x warning, 3.x removed | Use `isocalendar()` to avoid FutureWarning and breakage on pandas 3.x |
| `ISOWEEKNUM` (Excel) | `WEEKNUM(date, 21)` (DAX) | N/A — DAX never had ISOWEEKNUM | DAX uses `return_type=21` in WEEKNUM for ISO 8601 |
| Non-group executeQueries | Group executeQueries (`/groups/{id}/...`) | API has always had both; group required for workspace datasets | Using non-group URL against a workspace dataset → 404/403 |

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `WEEKNUM(date, 21)` in DAX is equivalent to ISO 8601 week numbering | DAX Weekly Aggregation Query | If wrong, week numbers would differ at year boundary — week 52/53 vs week 1 confusion in pandas join |
| A2 | `fact_fee_preview` does not expose a currency column — currency must be derived from country prefix | Pattern 5 (currency mapping) | If a currency column exists in the table, the hard-coded COUNTRY_CURRENCY dict is unnecessary; verify with `EVALUATE TOPN(5, 'fact_fee_preview')` |
| A3 | `pd.Timestamp.fromisocalendar(year, week, 1)` returns the Monday of a given ISO week | Pandas ISO week pattern | If wrong, week_start_date values would be off by days — verify against a known date (e.g., ISO 2026-W01 → 2025-12-29) |
| A4 | The SKU DAX query `SUMMARIZECOLUMNS` on `SKUs` table returns all 5,274+ keys including `amzn.gr.*` | Pattern 5 (SKU join) | If `amzn.gr.*` keys are absent from `SKUs`, this is expected behavior — but if some non-amzn.gr keys are also missing, there's a data gap |
| A5 | Response value count math (84,384 rows × 5 cols = 421,920) is within the 1M limit | Standard Stack — critical architecture insight | If `fact_fee_preview` has more columns returned by SUMMARIZECOLUMNS than expected, value count could be higher; verify with a small date range test first |

---

## Open Questions (RESOLVED)

1. **Does `fact_fee_preview` have a currency column?**
   - What we know: `expected_fulfillment_fee_per_unit` is present; key format is `"COUNTRY | SKU"`.
   - What's unclear: Whether the table stores a currency code column (e.g., `fee_currency`).
   - Recommendation: First task in Wave 1 should be a `EVALUATE TOPN(3, 'fact_fee_preview')` schema inspection query to confirm all column names before writing the main aggregation query.
   - RESOLVED: Assumption A2 — no currency column confirmed; derived from country prefix. Will be verified by skeleton.py run (Plan 01-02 checkpoint). If wrong, explore_fees.py currency mapping reverts to passthrough.

2. **Are there countries beyond the 8 listed in the discussion log?**
   - What we know: US=1706, GB=603, DE=565, MX=360, IT=293, FR=281, ES=278, CA=184 (confirmed live). Total = 4,270. Remaining 1,004 keys are unaccounted.
   - What's unclear: Could be other EU countries (NL, BE, SE, PL) or `amzn.gr.*` keys.
   - Recommendation: Include a diagnostic step: `SELECT DISTINCT country FROM output_df` in the script, log the full country list.
   - RESOLVED: Will be diagnosed by Plan 04 main() stdout — country list printed. No blocker to planning.

3. **Does the `amzn.gr.*` key count match the 1,004 gap?**
   - What we know: 5,274 total − 4,270 country-attributed = 1,004 unaccounted.
   - Recommendation: The Phase 1 script should print the count of unjoined keys. If count ≠ 1,004, there are other unjoined keys beyond `amzn.gr.*`.
   - RESOLVED: Will be answered by Plan 04 unjoined key count. Not a blocker — D-05 says include all keys.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.13.2 [VERIFIED: pip] | — |
| `msal` | Auth | ✓ | 1.36.0 [VERIFIED: pip] | — |
| `requests` | HTTP calls | ✓ | 2.32.3 [VERIFIED: pip] | — |
| `pandas` | Data processing | ✓ | 2.2.3 [VERIFIED: pip] | — |
| `numpy` | Pandas dependency | ✓ | 2.2.4 [VERIFIED: pip] | — |
| `python-dotenv` | Local credentials | ✓ | 1.0.1 [VERIFIED: pip] | — |
| `pydantic` | Schema validation | ✓ | 2.13.4 [VERIFIED: pip] | — |
| `pytest` | Unit tests | ✓ | 9.0.3 [VERIFIED: pip, freshly installed] | — |
| `POWERBI_TENANT_ID` env var | Auth | ✓ | Set (confirmed in powerbi-query skill setup) | — |
| `POWERBI_CLIENT_ID` env var | Auth | ✓ | Set (confirmed in powerbi-query skill setup) | — |
| Token cache at `~/.claude/powerbi_token_cache.json` | Silent auth | ✓ | Present (confirmed live queries during context session) | Device-code re-auth |

**Python version note:** Python 3.13.2 is installed. CLAUDE.md specifies Python 3.12 as the declared runtime. This machine runs 3.13. There is no known compatibility issue with the declared stack for Phase 1. The planner should note this discrepancy but it does not block execution.

**Missing dependencies with no fallback:** None — all required packages are installed.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 |
| Config file | none — Wave 0 creates `pytest.ini` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | `run_dax()` returns list of dicts with expected keys | unit (mock HTTP) | `pytest tests/test_aggregation.py::test_run_dax_returns_expected_shape -x` | Wave 0 |
| DATA-01 | Weekly aggregation produces correct `avg_fee_per_unit` for known input | unit | `pytest tests/test_aggregation.py::test_weekly_avg_calculation -x` | Wave 0 |
| DATA-01 | Value count math passes sanity check before query execution | unit | `pytest tests/test_aggregation.py::test_value_count_within_limit -x` | Wave 0 |
| DATA-02 | Country extraction from key prefix produces expected 2-letter codes | unit | `pytest tests/test_aggregation.py::test_country_extraction -x` | Wave 0 |
| DATA-02 | Currency mapping covers all known countries | unit | `pytest tests/test_aggregation.py::test_currency_mapping_completeness -x` | Wave 0 |
| DETECT-01 | `amzn.gr.*` keys are flagged as unjoined, not dropped | unit | `pytest tests/test_aggregation.py::test_amzn_gr_keys_preserved -x` | Wave 0 |
| DETECT-01 | Output CSV contains all required D-11 columns | unit | `pytest tests/test_aggregation.py::test_csv_schema_columns -x` | Wave 0 |
| DETECT-01 | `week_start_date` is always a Monday | unit | `pytest tests/test_aggregation.py::test_week_start_is_monday -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/__init__.py` — marks tests as package
- [ ] `tests/conftest.py` — fixture: sample daily rows mimicking PBI API JSON response; fixture: expected output CSV rows
- [ ] `tests/test_aggregation.py` — all 8 test cases above
- [ ] `pytest.ini` — minimal config (testpaths = tests, addopts = -q)
- [ ] `.env.example` — template with `POWERBI_TENANT_ID=` and `POWERBI_CLIENT_ID=` placeholders
- [ ] `.gitignore` — `.env`, `output/`, `__pycache__/`, `*.csv`

---

## Security Domain

> `security_enforcement: true`, `security_asvs_level: 1`

### Applicable ASVS Categories (Level 1)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | MSAL device-code with token cache; no password storage |
| V3 Session Management | No | No session state — script is stateless between runs |
| V4 Access Control | No | Script is single-user, local execution |
| V5 Input Validation | Yes (LOW) | DAX date range parameters from Python variables — no user input in Phase 1 |
| V6 Cryptography | No | No custom crypto; token cache uses MSAL's own serialization |
| V7 Error Handling | Yes | Auth failures, HTTP errors, and DAX soft-errors must be caught and printed, not swallowed |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Credentials in source code | Information Disclosure | `.env` file + `.gitignore`; env vars only; `.env.example` committed with no values |
| Token cache file readable by other users | Information Disclosure | Cache at `~/.claude/powerbi_token_cache.json` — verify file permissions are user-only (chmod 600 equivalent); note: Windows ACL may need explicit check |
| DAX injection via dynamic query construction | Tampering | Phase 1 only uses Python-constructed date literals (not user input) — low risk; document for Phase 2 when filter parameters may become user-configurable |
| Partial result silently accepted as complete | Denial of Service (data integrity) | Always check `result["error"]` field after executeQueries; raise exception on non-null error |

**Security note specific to this phase:** The token cache file at `~/.claude/powerbi_token_cache.json` contains refresh tokens granting access to all Power BI datasets the authenticated user can access — not just the fee dataset. The planner should include a task to verify file permissions on this cache file.

---

## Project Constraints (from CLAUDE.md)

| Constraint | Directive | Planner Action |
|------------|-----------|---------------|
| Data access | Power BI only via `powerbi-query` skill pattern — no direct DB to Amazon Seller Central | Use MSAL + requests pattern exactly as documented in skill |
| Token budget | No large data dumps in prompts | Phase 1 has no LLM calls — N/A |
| Output format | ClickUp comments concise, verbose in CSV | Phase 1 produces no ClickUp output — N/A |
| Anthropic SDK | Direct SDK only — no LangChain/LlamaIndex | Phase 1 has no LLM calls — N/A |
| `powerbiclient` PyPI package | Explicitly forbidden — unofficial, sparse maintenance | Do NOT import `powerbiclient`; use raw `requests` + `msal` |
| Python version | 3.12 declared; 3.13 installed on this machine | No action needed for Phase 1 stack; flag for Phase 3 container builds |
| No hardcoded credentials | `.env` + `.gitignore` | Wave 0 includes `.env.example` and `.gitignore` |

---

## Sources

### Primary (HIGH confidence)
- [Microsoft Learn — Datasets Execute Queries In Group](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/execute-queries-in-group) — row limits (100K rows / 1M values / 15MB), rate limits, endpoint URL format
- [Microsoft Learn — Datasets Execute Queries](https://learn.microsoft.com/en-us/rest/api/power-bi/datasets/execute-queries) — same limits, confirmation of soft-error behavior at HTTP 200
- `~/.claude/commands/powerbi-query.md` — auth block, run_dax pattern, known model IDs
- Live schema session (captured in CONTEXT.md / DISCUSSION-LOG.md) — table names, column names, key count, date range confirmed
- `pip index versions` output — all package versions confirmed against PyPI registry
- slopcheck 0.6.1 — all 7 packages scored [OK]

### Secondary (MEDIUM confidence)
- [Microsoft Entra — Refresh tokens](https://learn.microsoft.com/en-us/entra/identity-platform/refresh-tokens) — 90-day sliding window refresh token lifetime
- [pandas dt.isocalendar documentation](https://pandas.pydata.org/pandas-docs/dev/reference/api/pandas.Series.dt.isocalendar.html) — ISO week extraction pattern
- [DataSharkX — Overcoming PBI row limits](https://datasharkx.wordpress.com/2023/03/02/overcoming-data-size-row-limitations-of-power-bi-rest-api-for-automated-data-extraction-from-dataset/) — batch pagination pattern (not needed if aggregating in DAX)
- [MSAL Python — Acquiring tokens](https://learn.microsoft.com/en-us/entra/msal/python/getting-started/acquiring-tokens) — silent acquisition behavior

### Tertiary (LOW confidence)
- WEEKNUM(date, 21) = ISO 8601 week: verified from [DAX WEEKNUM docs](https://learn.microsoft.com/en-us/dax/weeknum-function-dax) which documents return_type=21, but live DAX execution against `fact_fee_preview` has not been done for the weekly aggregation query specifically

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages verified via pip registry and slopcheck; versions confirmed installed
- DAX query pattern: MEDIUM — column names confirmed live; WEEKNUM(date,21) is documented but the exact SUMMARIZECOLUMNS syntax on `fact_fee_preview` has not been executed
- Row limit math: HIGH — limits verified against official Microsoft Learn docs
- MSAL auth pattern: HIGH — verbatim from `powerbi-query` skill, confirmed operational on this machine
- Pandas ISO week patterns: MEDIUM — API documented but not executed in this session

**Research date:** 2026-05-27
**Valid until:** 2026-06-27 (stable APIs; pandas 3.x migration note valid until team upgrades)
