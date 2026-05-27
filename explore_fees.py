"""
FBA Fee Auditor — Phase 1 exploration script.
Queries Power BI for 16 weeks of fee data and writes a CSV.
Extended by Phase 2 into run_audit.py.
"""

import os

import msal
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Module-level constants (D-07, D-08, D-09)
# ---------------------------------------------------------------------------

WORKSPACE_ID = "47144ee2-02f9-4408-9ed5-57acf6a9f44d"
DATASET_ID   = "a95798aa-a3ec-4a89-9816-63cde534cdd7"
SCOPES       = ["https://analysis.windows.net/powerbi/api/Dataset.Read.All"]
CACHE_PATH   = os.path.expanduser("~/.claude/powerbi_token_cache.json")

# Currency mapping by country prefix (RESEARCH.md Pitfall 6)
COUNTRY_CURRENCY = {
    "US": "USD",
    "CA": "CAD",
    "GB": "GBP",
    "MX": "MXN",
    "DE": "EUR",
    "FR": "EUR",
    "ES": "EUR",
    "IT": "EUR",
}


# ---------------------------------------------------------------------------
# Auth layer (D-09, RESEARCH.md Pattern 1)
# ---------------------------------------------------------------------------

def get_token() -> str:
    """Acquire a Power BI access token via MSAL device-code flow with silent refresh.

    Reads POWERBI_TENANT_ID and POWERBI_CLIENT_ID from environment.
    Persists the token cache to CACHE_PATH after a successful acquire.
    Falls back to interactive device-code flow when the cached refresh token
    is missing or expired (> 90 days idle).

    Returns:
        Bearer access token string.

    Raises:
        SystemExit: if authentication fails.
    """
    tenant_id = os.environ.get("POWERBI_TENANT_ID")
    client_id = os.environ.get("POWERBI_CLIENT_ID")

    if not tenant_id:
        raise SystemExit(
            "POWERBI_TENANT_ID environment variable is not set. "
            "Copy .env.example to .env and fill in your values."
        )
    if not client_id:
        raise SystemExit(
            "POWERBI_CLIENT_ID environment variable is not set. "
            "Copy .env.example to .env and fill in your values."
        )

    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_PATH):
        cache.deserialize(open(CACHE_PATH).read())

    app = msal.PublicClientApplication(
        client_id,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
        token_cache=cache,
    )

    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result or "access_token" not in result:
        # Refresh token expired or no cache — requires user interaction
        flow = app.initiate_device_flow(scopes=SCOPES)
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)

    if "access_token" not in result:
        raise SystemExit(f"Auth failed: {result.get('error_description')}")

    # Persist updated cache (may contain refreshed tokens)
    open(CACHE_PATH, "w").write(cache.serialize())
    return result["access_token"]


# ---------------------------------------------------------------------------
# Query layer (RESEARCH.md Pattern 2)
# ---------------------------------------------------------------------------

def run_dax(dax: str, token: str) -> list[dict]:
    """Execute a DAX query against the Power BI dataset via the group endpoint.

    Uses the /groups/{workspaceId}/datasets/{datasetId}/executeQueries endpoint
    (not the non-group variant — OrganiHaus datasets live in a named workspace).

    After raise_for_status(), checks result.get("error") for soft errors that
    return HTTP 200 but contain truncated or partial data.

    Args:
        dax: DAX query string (must start with EVALUATE).
        token: Bearer access token from get_token().

    Returns:
        List of row dicts from result["tables"][0]["rows"].

    Raises:
        requests.HTTPError: on non-2xx HTTP response.
        RuntimeError: if the API returns a soft error at HTTP 200.
    """
    url = (
        f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE_ID}"
        f"/datasets/{DATASET_ID}/executeQueries"
    )
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        json={
            "queries": [{"query": dax}],
            "serializerSettings": {"includeNulls": True},
        },
        timeout=120,
    )
    r.raise_for_status()
    result = r.json()["results"][0]
    if result.get("error"):
        raise RuntimeError(f"DAX query error: {result['error']}")
    return result["tables"][0].get("rows", [])


# ---------------------------------------------------------------------------
# Value count guard (RESEARCH.md Pitfall 1, T-02-03)
# ---------------------------------------------------------------------------

def validate_value_count(n_keys: int, n_weeks: int, n_cols: int) -> int:
    """Compute the projected DAX query value count and raise if it exceeds the limit.

    The Power BI executeQueries endpoint enforces a hard limit of 1,000,000 values
    per query (rows × columns). Exceeding this produces a silent HTTP 200 with
    partial data and a non-null error field. Call this before executing any query
    to abort early with a clear error.

    Args:
        n_keys: Number of distinct SKU/country keys in the query.
        n_weeks: Number of ISO weeks in the date range.
        n_cols: Number of columns selected in the DAX query.

    Returns:
        Total value count (n_keys * n_weeks * n_cols) if within limit.

    Raises:
        ValueError: if the projected value count is >= 1,000,000.
    """
    total = n_keys * n_weeks * n_cols
    if total >= 1_000_000:
        raise ValueError(
            f"Value count {total:,} exceeds the 1,000,000 Power BI executeQueries limit. "
            f"Reduce n_keys ({n_keys}), n_weeks ({n_weeks}), or n_cols ({n_cols})."
        )
    return total


# ---------------------------------------------------------------------------
# Wave 3 stubs — implemented in Plan 01-03
# ---------------------------------------------------------------------------

def process_pbi_rows(rows: list[dict]) -> pd.DataFrame:
    """Convert raw PBI API rows into a cleaned DataFrame.

    Renames PBI fully-qualified column names (e.g., "fact_fee_preview[col]")
    to bare column names. Derives week_start_date from ISO year + week number.

    Column rename sequence:
      1. Strip bracket qualification: "fact_fee_preview[key_sales_marketplace_sku]" -> "key_sales_marketplace_sku"
      2. Normalise YEAR/WEEKNUM to lowercase snake_case for consistency with test fixtures
      3. Cast year and week_num to int (PBI may return float)
      4. Add week_start_date via iso_to_week_start
    """
    df = pd.DataFrame(rows)
    # RESEARCH.md Pattern 4 — strip PBI column name qualifications FIRST
    df.columns = [c.split("[")[-1].rstrip("]") for c in df.columns]
    # Normalise to snake_case expected by tests
    df = df.rename(columns={"YEAR": "year", "WEEKNUM": "week_num"})
    # Cast to int — PBI may return floats
    df["year"] = df["year"].astype(int)
    df["week_num"] = df["week_num"].astype(int)
    # Ensure avg_fee_per_unit is float
    df["avg_fee_per_unit"] = df["avg_fee_per_unit"].astype(float)
    # Derive Monday date for each ISO year+week
    df["week_start_date"] = df.apply(
        lambda row: iso_to_week_start(row["year"], row["week_num"]), axis=1
    )
    return df


def extract_country(df: pd.DataFrame) -> pd.DataFrame:
    """Parse the 2-letter country code from key_sales_marketplace_sku.

    Format: "<CC> | <CC>-<SKU>" — the prefix before " | " is the country code.
    Adds a 'country' column to the DataFrame.

    For amzn.gr.* keys that lack a " | " separator, the full key becomes
    the country value — currency mapping will return "UNKNOWN" for these.
    """
    df["country"] = df["key_sales_marketplace_sku"].str.split(" | ").str[0]
    return df


def get_currency_for_country(country_code: str) -> str:
    """Map a 2-letter country code to its ISO 4217 currency code.

    Unknown country codes return 'UNKNOWN' rather than raising an exception.
    Uses the module-level COUNTRY_CURRENCY constant (D-11, RESEARCH.md Pitfall 6).
    """
    return COUNTRY_CURRENCY.get(country_code, "UNKNOWN")


def build_output_df(fee_df: pd.DataFrame, sku_df: pd.DataFrame) -> pd.DataFrame:
    """Join the weekly fee DataFrame with the SKU dimension and produce the D-11 output schema.

    Left-joins fee_df to sku_df on key_sales_marketplace_sku. amzn.gr.* keys that
    do not join have NaN for asin, sku, and sales_region — they are preserved, not dropped.

    Implemented in Wave 3 (Plan 01-03).
    """
    raise NotImplementedError("build_output_df is implemented in Wave 3 (Plan 01-03)")


def iso_to_week_start(iso_year: int, iso_week: int) -> pd.Timestamp:
    """Return the Monday date for a given ISO year + week number.

    Uses pd.Timestamp.fromisocalendar(year, week, 1) — day 1 of ISO week is Monday.
    RESEARCH.md: do not hand-roll date arithmetic; fromisocalendar handles year
    boundary correctly (ISO 2026 week 1 Monday = 2025-12-29).

    If iso_week exceeds the number of weeks in iso_year (e.g., week 53 in a 52-week year),
    falls back to week 1 of the following year rather than raising ValueError. This handles
    edge cases in PBI data where the week counter wraps across year boundaries.
    """
    try:
        return pd.Timestamp.fromisocalendar(int(iso_year), int(iso_week), 1)
    except ValueError:
        # iso_week exceeds max weeks for this year — treat as week 1 of next year
        return pd.Timestamp.fromisocalendar(int(iso_year) + 1, 1, 1)


# ---------------------------------------------------------------------------
# CSV writer stub (Wave 3) — schema documented here for Phase 2
# ---------------------------------------------------------------------------

# anomaly_history.csv schema (Phase 2 writer — do not populate in Phase 1):
# key_sales_marketplace_sku, country, sku, asin, sales_region,
# week_start_date, avg_fee_per_unit, baseline_median_fee_per_unit,
# deviation_pct, direction, consecutive_weeks_flagged, run_date
