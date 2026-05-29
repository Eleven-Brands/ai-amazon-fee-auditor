## Standing Instructions

- **SEMPRE usar a skill `/dashboard-guide`** para qualquer pergunta sobre dashboards, modelos Power BI, tabelas, colunas, medidas DAX ou estrutura de dados da OrganiHaus. Nunca ler os arquivos de referência diretamente via PowerShell ou Bash — usar o skill.

---

<!-- GSD:project-start source:PROJECT.md -->

## Project

**AI Amazon Fee Auditor**

An AI agent system that automatically audits Amazon FBA fees for OrganiHaus, detecting anomalies in FBA Fulfillment Fee at the SKU/ASIN level by comparing current charges against historical baselines. It runs weekly via Windows Task Scheduler (and on-demand via CLI), posts findings to ClickUp, and escalates unusual charges for human investigation.

**Core Value:** Detect fee anomalies faster than manual review — alert the right people before unexpected charges accumulate unnoticed.

### Constraints

- **Execution:** Windows Task Scheduler on local machine — simple, no additional infrastructure. Requires machine to be on at scheduled time.
- **Data access:** Power BI only via `powerbi-query` skill — no direct DB connection to Amazon Seller Central
- **Token budget:** Each agent must receive only the context it needs — no large data dumps in prompts; summaries and structured outputs only
- **Output format:** ClickUp comments must be concise; verbose detail in attached CSV only

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Recommended Stack

### AI / Agent Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `anthropic` Python SDK | `>=0.28.0` | LLM calls, tool-use loop, structured outputs | First-party SDK for Claude; supports tool_use natively for agent loops; `claude-sonnet-4-6` is the declared model. Do NOT use LangChain or LlamaIndex wrappers — they add indirection over a simple tool loop and the project explicitly calls out direct Anthropic API usage. |
| `claude-sonnet-4-6` | — (model ID, not versioned) | Primary inference | Declared in project system prompt; best balance of reasoning quality and cost for structured analysis tasks. claude-opus-* is overkill for fee comparison; claude-haiku-* lacks reasoning depth for anomaly rationale generation. |

### Data Retrieval Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Power BI REST API (via `requests`) | REST API v1.0 | Query FBA/Storage Fee datasets via DAX | Power BI is declared source of truth; no direct DB access. Access pattern is Execute Queries endpoint (`POST /datasets/{datasetId}/executeQueries`) with DAX `EVALUATE` statements. MSAL handles OAuth2 token acquisition. |
| `msal` | `>=1.28.0` | Azure AD OAuth2 token for Power BI API | Required for service principal auth against Power BI REST API; handles token refresh automatically. Use app registration with `Dataset.ReadAll` scope. |
| `requests` | `>=2.31.0` | HTTP client for Power BI REST API and ClickUp API | Battle-tested, simple, no async overhead needed for sequential agent calls. `httpx` is acceptable alternative but adds complexity without benefit here. |
| `google-cloud-bigquery` | `>=3.13.0` | Write anomaly results to BigQuery for historical tracking; query historical baseline data if cached there | Declared stack. BigQuery is the persistence layer between runs. Anomaly detection compares current week vs rolling N-week baseline stored in BQ. |
| `pandas` | `>=2.1.0` | In-memory data manipulation, rolling window calculations | Required for baseline calculations. `polars` is faster but pandas is more familiar to the team and has better BigQuery integration via `pandas-gbq`. |
| `pandas-gbq` | `>=0.21.0` | Convenience wrapper for BigQuery read/write from pandas DataFrames | Simpler API than raw `google-cloud-bigquery` for the read/write patterns this project needs. |

### Anomaly Detection Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `pandas` | `>=2.1.0` | Rolling baseline (mean/median), percentage deviation calculation | All anomaly detection for MVP is statistical, not ML-based. Rolling 4-8 week median per SKU is sufficient. Avoid `scikit-learn` IsolationForest for v1 — it adds model management complexity without better results for simple fee-change detection. |
| `scipy` | `>=1.11.0` | Z-score calculation as optional secondary signal | `scipy.stats.zscore` for per-SKU deviation scoring; use only if percentage threshold alone produces too many false positives during calibration. |
| `numpy` | `>=1.26.0` | Numerical operations underlying pandas | Transitive dependency of pandas; listed explicitly because version pinning matters for Windows compatibility. |

- `scikit-learn` IsolationForest or DBSCAN: overkill for threshold-based fee monitoring; requires training data management
- `prophet` (Meta): designed for demand forecasting, not anomaly detection on fee time series; heavy dependency
- `statsmodels` ARIMA: maintenance overhead; the project goal is a threshold alert, not a forecast
- Any cloud ML service (Vertex AI, Azure ML): unnecessary cost and latency for what is essentially a `(current - baseline) / baseline > threshold` calculation

### Output / Integration Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| ClickUp API v2 | REST, no SDK | Post comments, attach files to ClickUp tasks | ClickUp has no official Python SDK. Use raw `requests` with `Authorization: Bearer {CLICKUP_API_KEY}` header. API v2 is the current stable version (v3 announced but not GA as of August 2025). |
| `jinja2` | `>=3.1.0` | HTML template for anomaly report attached to ClickUp task | Cleaner than f-string HTML generation; produces the HTML attachment referenced in PROJECT.md requirements. Use for the detailed report file — not for the ClickUp comment body (keep that plain text/markdown). |

- `POST /task/{task_id}/comment` — post anomaly summary comment
- `POST /task/{task_id}/attachment` — attach CSV or HTML report file
- `GET /task/{task_id}` — read existing task before posting (idempotency check)

### Scheduling / Orchestration Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| n8n (cloud) | `elevenbrands.app.n8n.cloud` | Weekly schedule trigger, on-demand trigger, HTTP call to Python agent | Declared stack. n8n handles cron scheduling and retry logic without requiring a local machine. The Python agent runs as a self-contained script or HTTP endpoint that n8n calls. |
| n8n HTTP Request node | — | Invoke Python agent (webhook or script execution) | Two viable patterns: (a) Python script runs as a Cloud Run / Cloud Function job triggered by n8n HTTP Request; (b) n8n executes Python via Execute Command node if self-hosted. Given cloud n8n, pattern (a) is cleaner — deploy agent as a Cloud Run Job, n8n POSTs to a trigger URL. |

- Airflow: heavyweight, requires persistent infrastructure
- Prefect/Dagster: excellent tools but overkill for a single weekly job
- APScheduler inside the Python process: requires always-on process, contradicts the n8n-first constraint
- Cloud Scheduler directly without n8n: removes the retry/logging layer the team already has

### Infrastructure / Deployment Layer

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Google Cloud Run Jobs | — | Serverless execution environment for the Python agent | Integrates natively with BigQuery (same GCP project, no cross-cloud auth); scales to zero (no idle cost); triggered by HTTP from n8n; container-based (no dependency hell). |
| `google-cloud-secret-manager` OR environment variables | `>=2.16.0` | Secrets: Power BI client secret, ClickUp API key, Anthropic API key | Use Secret Manager if already in GCP project; otherwise environment variables injected at Cloud Run Job deployment. Do NOT hardcode secrets or commit to git. |
| Docker | — | Container for Cloud Run Job | Standard containerization. Use `python:3.12-slim` base image. |
| Python | `3.12` | Runtime | 3.12 is current stable with performance improvements; 3.11 is acceptable fallback. Do NOT use 3.13 (too new, library ecosystem not fully validated). |

### Configuration / Project Structure

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `python-dotenv` | `>=1.0.0` | Load `.env` for local development | Standard pattern; keeps local dev credentials out of code. Cloud Run uses injected env vars — dotenv is a no-op in production. |
| `pydantic` | `>=2.5.0` | Data validation for agent inputs/outputs and config | Pydantic v2 is the standard for structured data in Python agent systems as of 2025. Use for: anomaly result schema, ClickUp payload schema, agent config (thresholds, SKU filters). Prevents malformed data propagating through the pipeline. |
| `pytest` | `>=7.4.0` | Unit tests for anomaly detection logic, ClickUp payload builder | The threshold calibration and baseline calculation logic must be unit-testable without live API calls. Mock Power BI and ClickUp responses. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| HTTP client | `requests` | `httpx` | `httpx` is excellent for async but this agent is synchronous; adds zero value |
| Data frames | `pandas` | `polars` | Team familiarity; better BigQuery ecosystem support |
| Anomaly detection | Statistical (pandas) | scikit-learn IsolationForest | Requires training data, model management; threshold % achieves the same result |
| LLM orchestration | Anthropic SDK direct | LangChain | Extra abstraction over a tool-use loop the SDK handles natively; LangChain version churn has historically caused breakage |
| Scheduling | n8n (cloud) | Airflow, Prefect | Declared stack; single weekly job does not justify additional infrastructure |
| Agent framework | None (direct SDK) | LangGraph, CrewAI, AutoGen | PROJECT.md explicitly defers multi-agent decomposition; single agent + tool use needs no framework |
| Power BI client | `requests` + `msal` | `powerbiclient` (PyPI) | `powerbiclient` is unofficial, sparsely maintained, not suitable for production |
| Secrets | Secret Manager / env vars | Hardcoded / `.env` in repo | Security — never commit credentials |
| Deployment | Cloud Run Jobs | Cloud Functions, GCE VM | Cloud Run Jobs are purpose-built for batch/scheduled work; Cloud Functions have execution time limits; GCE requires always-on cost |

## Critical Version Constraints

# Verify these before first deploy — training data cutoff August 2025

## Confidence Assessment

| Component | Confidence | Reason |
|-----------|------------|--------|
| Anthropic SDK + tool_use pattern | HIGH | Well-documented, stable API, matches declared model `claude-sonnet-4-6` |
| BigQuery via `google-cloud-bigquery` + `pandas-gbq` | HIGH | Production-stable, widely used, matches declared stack |
| Power BI REST API via `requests` + `msal` | HIGH | Microsoft-official approach; `msal` is the correct auth library for service principal flows |
| ClickUp API v2 endpoints (comment, attachment) | MEDIUM | API v2 is stable but ClickUp has not published an official Python SDK; endpoint behavior verified against ClickUp's public API docs in training data; confirm task attachment endpoint accepts multipart before building |
| n8n + Cloud Run Jobs integration | MEDIUM | Pattern is sound; actual trigger URL configuration depends on n8n instance setup at `elevenbrands.app.n8n.cloud` |
| Statistical anomaly detection (pandas rolling) | HIGH | Well-established pattern for threshold-based monitoring; no external dependencies |
| Library version numbers | MEDIUM | Based on training data cutoff August 2025; run `pip index versions <package>` to confirm latest before pinning |
| `claude-sonnet-4-6` model ID | HIGH | Declared in project context and matches Anthropic model naming convention |

## Sources

- PROJECT.md (project-declared stack and constraints)
- Training knowledge: Anthropic API documentation, Power BI REST API Microsoft docs, ClickUp API v2 docs, Google Cloud Run Jobs documentation — all as of August 2025 training cutoff
- Live verification was not possible (external network tools restricted in this session); version pins should be confirmed before first deploy

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
