# Phase 1: Data Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-27
**Phase:** 1-Data-Foundation
**Areas discussed:** Historical data source, Exploratory output form, Marketplace scope, Credentials & auth

---

## Historical Data Source

| Option | Description | Selected |
|--------|-------------|----------|
| BigQuery direct | Query `vw_full_fee_preview` directly from Python | |
| PBI REST API with custom DAX | Custom DAX on `fact_fee_preview` via executeQueries endpoint | ✓ |
| Try both — decide from results | Test both paths in Phase 1 | |

**User's choice:** PBI REST API with custom DAX

**Schema investigation (live queries run during session):**
- `fact_fee_preview` confirmed: daily rows, date column = `date_fee_preview`, fee column = `expected_fulfillment_fee_per_unit`, `is_latest` flag exists
- Date range confirmed: 2023-07-01 → 2026-05-27 (nearly 3 years)
- 5,274 distinct `key_sales_marketplace_sku` keys; each date has 5,274 rows
- Key format: `"COUNTRY | SKU"` (e.g., `"US | US-OHFB-1VH-1613X-PKOW"`)
- US = 1,706 keys; GB = 603; DE = 565; MX = 360; IT = 293; FR = 281; ES = 278; CA = 184
- `SKUs` dimension table: confirmed ASIN column, Sales Region column, join key = `SKUs[Key Column: Country | SKU]`
- Workspace ID: `47144ee2-02f9-4408-9ed5-57acf6a9f44d`; Dataset ID (Operations): `a95798aa-a3ec-4a89-9816-63cde534cdd7`

**On date dimension question:** User responded "ask the skill" — Claude queried live and confirmed `date_fee_preview` is the date column.

**On dataset IDs:** User initially said "I'll provide it" → deferred to live API discovery which succeeded.

**Weekly granularity:**
| Option | Description | Selected |
|--------|-------------|----------|
| Last day of each calendar week | One data point per week, simple DAX | |
| Average across the week | Average all daily fee values within each week | ✓ |
| Any change in the week | Change-detection approach | |

**amzn.gr. keys:**
| Option | Description | Selected |
|--------|-------------|----------|
| Exclude — standard SKUs only | Filter out `amzn.gr.*` keys | |
| Include — audit all keys | Audit everything in the table | ✓ |

---

## Exploratory Output Form

| Option | Description | Selected |
|--------|-------------|----------|
| Python script + CSV output | Runnable `explore_fees.py` producing a CSV | ✓ |
| Jupyter notebook | Interactive `.ipynb` with charts | |
| Script + ClickUp comment (draft) | First end-to-end output test | |

**User's choice:** Python script + CSV output

**Reviewer:**
| Option | Selected |
|--------|----------|
| Just Lucca | ✓ |
| Lucca + Gustavo | |
| Lucca + Victor | |

**Notes:** User confirmed Lucca reviews alone — no review gate before Phase 2.

**CSV content:**
| Option | Selected |
|--------|----------|
| Per-SKU weekly fee history (time series) | ✓ |
| Summary stats per SKU (min/max/std_dev) | |
| Both: summary + raw weekly | |

---

## Marketplace Scope

| Option | Description | Selected |
|--------|-------------|----------|
| US only | 1,706 keys, cleanest data for calibration | |
| US + UK + CA (core markets) | ~2,493 keys | |
| All marketplaces from the start | 5,274 keys | ✓ |

**User's choice:** All marketplaces from the start

**Sales Region label:**
| Option | Selected |
|--------|----------|
| 2-letter country code (US, GB, DE...) | ✓ |
| Full marketplace name | |
| PBI Sales Region label | |

**ASIN mapping:** User confirmed: "ASIN está na tabela SKUs, que é a tabela de dimensão de SKUs" — confirmed live via query.

---

## Credentials & Auth

| Option | Description | Selected |
|--------|-------------|----------|
| BigQuery service account already exists | Use existing service account JSON | (N/A — BQ dropped) |
| Need to create new service account | Set up GCP auth from scratch | (N/A) |
| gcloud CLI auth (ADC) | `gcloud auth application-default login` | (N/A) |

**User's decision:** **No BigQuery at all.** "Não quero criar tabelas no big query. Crie esses arquivos localmente como csv ou xlsx." This overrides the original roadmap success criterion #5 (BigQuery tables).

**State persistence:**
| Option | Selected |
|--------|----------|
| CSV per run + running anomaly history CSV | ✓ |
| Single Excel workbook with multiple sheets | |
| Phase 1 doesn't need persistent state | |

**Correction logged:** User pushed back on repeated references to Gustavo as schema owner. This assumption came from STATE.md and SUMMARY.md research docs that labeled those questions "Owner: Gustavo." User demonstrated direct schema knowledge and PBI querying capability throughout this session. Dependency assumption was incorrect and has been removed from CONTEXT.md.

---

## Claude's Discretion

- DAX query structure (SUMMARIZECOLUMNS vs CALCULATETABLE, ISO week vs calendar week)
- File naming convention for output CSVs beyond `explore_fees.py`
- Python package choices within the approved stack

## Deferred Ideas

- Sales Region-level vs country-level baseline grouping for EU SKUs
- Understanding what `amzn.gr.*` keys represent
- Dual-gate threshold (pct AND absolute dollar floor) — v2 scope
- Seasonal Q4 baseline — v2 scope
