# Phase 1 Walking Skeleton

**Goal:** Thinnest end-to-end slice that proves the full data path works before building the full exploration script

---

## What the Skeleton Proves

- MSAL device-code auth works on this machine (token cache at `~/.claude/powerbi_token_cache.json` is valid)
- Group executeQueries endpoint URL is correct: workspace `47144ee2-02f9-4408-9ed5-57acf6a9f44d` + dataset `a95798aa-a3ec-4a89-9816-63cde534cdd7`
- `fact_fee_preview` is queryable via DAX (`EVALUATE TOPN(5, 'fact_fee_preview')` returns rows)
- Column names match what CONTEXT.md and RESEARCH.md expect: `key_sales_marketplace_sku`, `date_fee_preview`, `expected_fulfillment_fee_per_unit`
- Assumption A2 resolved: confirms whether a currency column exists in the table

## Skeleton Implementation

```python
# skeleton.py — run this FIRST, before explore_fees.py
# If this file runs without error and prints >= 1 row: auth and connectivity are confirmed.
# Do NOT modify explore_fees.py until this file exits 0.

from dotenv import load_dotenv
import msal, os, requests, json

load_dotenv()

TENANT_ID   = os.environ["POWERBI_TENANT_ID"]
CLIENT_ID   = os.environ["POWERBI_CLIENT_ID"]
WORKSPACE   = "47144ee2-02f9-4408-9ed5-57acf6a9f44d"
DATASET     = "a95798aa-a3ec-4a89-9816-63cde534cdd7"
SCOPES      = ["https://analysis.windows.net/powerbi/api/Dataset.Read.All"]
CACHE_PATH  = os.path.expanduser("~/.claude/powerbi_token_cache.json")

# --- Auth (verbatim from powerbi-query skill) ---
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
    flow = app.initiate_device_flow(scopes=SCOPES)
    print(flow["message"])
    result = app.acquire_token_by_device_flow(flow)

if "access_token" not in result:
    raise SystemExit(f"Auth failed: {result.get('error_description')}")

open(CACHE_PATH, "w").write(cache.serialize())
token = result["access_token"]
print("Auth: OK")

# --- Schema Inspection Query ---
url = (
    f"https://api.powerbi.com/v1.0/myorg/groups/{WORKSPACE}"
    f"/datasets/{DATASET}/executeQueries"
)
body = {
    "queries": [{"query": "EVALUATE TOPN(5, 'fact_fee_preview')"}],
    "serializerSettings": {"includeNulls": True},
}
r = requests.post(
    url,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json=body,
    timeout=60,
)
r.raise_for_status()

payload = r.json()["results"][0]
if payload.get("error"):
    raise RuntimeError(f"DAX soft error: {payload['error']}")

rows = payload["tables"][0].get("rows", [])
if not rows:
    raise RuntimeError("Query returned 0 rows — check dataset/table name")

print(f"\nColumns returned ({len(rows[0])} total):")
for col in rows[0].keys():
    print(f"  {col}")

print(f"\nFirst row:")
print(json.dumps(rows[0], indent=2, default=str))
print(f"\nSkeleton: OK — {len(rows)} rows returned")
```

## Sequence

1. Ensure `.env` exists with `POWERBI_TENANT_ID` and `POWERBI_CLIENT_ID` set
2. Run `python skeleton.py` from the project root
3. If auth prompt appears: complete device-code login at `https://microsoft.com/devicelogin` using the printed code
4. Confirm output: at least 1 row printed with column names
5. Check for `key_sales_marketplace_sku`, `date_fee_preview`, `expected_fulfillment_fee_per_unit` in the column list
6. Note whether a currency column appears (resolves RESEARCH.md Assumption A2)
7. If confirmed: proceed to `explore_fees.py` development (PLAN 02 task 2)

## Architectural Decisions This Skeleton Records

| Decision | Value | Source |
|----------|-------|--------|
| Auth method | MSAL device-code + token cache | D-09, powerbi-query skill |
| Group endpoint URL | `/v1.0/myorg/groups/{workspaceId}/datasets/{datasetId}/executeQueries` | D-07, D-08, RESEARCH Pitfall 2 |
| Workspace ID | `47144ee2-02f9-4408-9ed5-57acf6a9f44d` | D-07 |
| Dataset ID | `a95798aa-a3ec-4a89-9816-63cde534cdd7` | D-08 |
| Token cache path | `~/.claude/powerbi_token_cache.json` | D-09 |
| Soft-error check | `result.get("error")` after `raise_for_status()` | RESEARCH Pattern 2 |
| Data source | `fact_fee_preview` table | D-01, D-02, D-03 |
| No BigQuery | Local CSV files only | D-17, D-18 |
| No `powerbiclient` package | raw `requests` + `msal` | CLAUDE.md constraint |

## Done When

- [ ] `python skeleton.py` prints "Skeleton: OK" without error
- [ ] Output contains at least 1 row
- [ ] Column names include `key_sales_marketplace_sku`, `date_fee_preview`, `expected_fulfillment_fee_per_unit`
- [ ] Whether a currency column exists is logged (yes/no) — resolves Assumption A2
