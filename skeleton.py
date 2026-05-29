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
