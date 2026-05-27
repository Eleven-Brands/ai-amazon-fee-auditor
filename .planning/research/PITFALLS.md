# Pitfalls: AI Amazon Fee Auditor

**Domain:** Amazon FBA fee auditing + AI agent monitoring systems
**Researched:** 2026-05-27
**Confidence:** HIGH on Amazon FBA mechanics and AI agent patterns; MEDIUM on n8n-specific reliability

---

## Phase Mapping Summary

| Phase | Pitfalls to Address |
|---|---|
| Phase 1 — Data & Baseline | P5 (data quality validation), P7 (exploratory run before threshold), P8 (data/LLM boundary), P12 (marketplace filter), P4 (policy events table — build empty), P11 (output template), P6 (prompt design) |
| Phase 1 — Baseline Logic | P1 (seasonal baseline buckets), P2 (baseline staleness / sustained-shift), P3 (per-unit fee in output) |
| Phase 2 — Anomaly Scoring | P7 (dual-gate threshold calibration), P2 (sustained-shift classification) |
| Phase 2 — n8n Workflow | P9 (error branches, heartbeat, run log) |
| Phase 3+ — Expansion | P10 (resist decomposition), P12 (marketplace segmentation), P4 (policy events maintenance) |

---

## Amazon FBA Fee Auditing Pitfalls

### ⛔ CRITICAL — P1: Seasonal Fee Spikes Treated as Anomalies

**What goes wrong:** Amazon charges ~2.4x higher monthly storage fees Oct-Dec (Q4 surcharge). A baseline from Jan-Sep data will flag every Q4 as a massive anomaly — generating a wall of 100% expected, 0% actionable alerts.

**Consequences:** Alert fatigue before the system proves its value. Team stops reading alerts after first October.

**Prevention:**
- Compute separate baseline buckets: Q4 (Oct-Dec) vs non-Q4 (Jan-Sep). Compare current period against matching seasonal bucket.
- OR: apply published Q4 surcharge multiplier before anomaly scoring.
- Long-term storage fees (assessed Feb 15 and Aug 15) are known events — treat their billing dates as calendar events, not surprises.

**Warning signs:** Every October/November run produces flood of storage fee flags, all similar percentage increases.

**Phase:** Address in Phase 1 baseline design, before any threshold calibration.

---

### ⛔ CRITICAL — P2: Baseline Staleness (State Drift)

**What goes wrong:** A 12-week rolling window takes 12 weeks to absorb a permanent step change. During those weeks, every run flags the affected SKU. OrganiHaus sells bulky home organization products near size tier boundaries — a single Amazon re-measure can permanently shift the fee.

**Consequences:** Same SKU appearing in every weekly alert report, always same direction.

**Prevention:**
- If same SKU fires same-direction anomaly for N consecutive weeks (suggest 3), auto-classify as "sustained shift" — not a repeating anomaly alert.
- Log the date of each SKU's last baseline reset.
- Build manual override: Victor or Data Team can mark SKU as "reclassified — update baseline" from ClickUp.

**Warning signs:** Same ASIN in every weekly report, same direction.

**Phase:** Phase 1 for baseline logic; Phase 2 for sustained-shift classification.

---

### ⛔ CRITICAL — P3: Size Tier Boundary Sensitivity

**What goes wrong:** Products near size tier boundaries can flip tiers when Amazon re-measures physical units in their FCs. FBA fee for large standard tops out ~$5-6/unit; small oversize jumps to $9-10+. A tier flip on a high-velocity SKU is $3-5/unit more — correctly flagged, but root cause isn't visible in Power BI fee data.

**Consequences:** Correct anomaly detection but wrong/blocked investigation. Victor can't see "why" from the data alone.

**Prevention:**
- Include fee-per-unit in anomaly output alongside total fee delta.
- In ClickUp output, suggest "check size tier in Seller Central" as first investigation step for per-unit fee anomalies.
- Note explicitly: rate card reconciliation (deferred) will eventually be needed to close this loop.

**Warning signs:** Anomaly is in fee-per-unit (not volume × rate), and delta matches known inter-tier step.

**Phase:** Phase 1 data output schema must include per-unit fees.

---

### ⛔ CRITICAL — P6: Hallucination in Analytical Conclusions

**What goes wrong:** LLM generates plausible-sounding narrative regardless of whether data supports it. E.g., agent says "increase likely due to Q4 storage surcharges" when anomaly is actually in fulfillment fees. Victor (non-analyst) may take the wrong action based on confident wrong explanation.

**Prevention:**
- Separate "what happened" (quantitative, computed) from "why it might have happened" (LLM reasoning). Data first, interpretation second, with explicit labels.
- Never ask the agent to interpret without the data: "FBA fee per unit for ASIN X jumped from $4.12 to $6.83. What might cause this?" is acceptable.
- Include standard disclaimer: "These observations are computed from fee data. Root cause requires human verification in Seller Central."
- Agent uses "this may indicate" not "this is caused by."

**Warning signs:** Agent output uses confident causal language without data support visible in same output.

**Phase:** Phase 1 prompt design. Must be in system prompt from day one.

---

### ⛔ CRITICAL — P7: Alert Fatigue from Uncalibrated Threshold

**What goes wrong:** A percentage-of-total-fee threshold fires constantly on low-volume SKUs. A SKU selling 2 units one week and 3 the next has a 50% fee increase — entirely volume-driven, not a fee rate change.

**Prevention:**
- **Dual-gate threshold:** flag only if `(fee_delta_pct > threshold) AND (fee_delta_abs > $X)`. The absolute floor eliminates low-volume noise.
- Prioritize by absolute dollar magnitude in ClickUp output, not just percentage.
- First data exploration run (before building anomaly logic) should produce distribution of week-to-week fee changes — empirical basis for both thresholds.
- Cap ClickUp alert at top 10-15 anomalies regardless of total flagged. Full list in CSV attachment.

**Warning signs:** Report shows 40+ flagged SKUs, all with small absolute dollar amounts.

**Phase:** Phase 1 must include exploratory data run before threshold is set. Phase 2 tunes the dual-gate.

---

### ⚠️ MODERATE — P4: Amazon Policy Change Lag (Rate Card Updates)

**What goes wrong:** Amazon announces fee changes annually (typically effective Feb/Mar). When new rates take effect, historical baseline will flag every SKU as anomalous — a report so large it's useless.

**Prevention:**
- Maintain a `fee_policy_events` BigQuery table: `(date, description, marketplace, scope)`. Entries like `2025-02-05, "FBA fulfillment fee adjustment", US, all_skus`.
- Before computing anomaly scores, check if current period crosses a known policy event. If yes, suppress anomaly scoring and post "policy change detected — baseline reset in progress" comment.
- Build the check logic in Phase 1 even if table starts empty.

**Warning signs:** 80%+ of active SKUs flag in same direction in same week.

**Phase:** Phase 1 — build policy events table (empty). Suppression logic is cheap to build now, expensive to retrofit.

---

### ⚠️ MODERATE — P5: Data Quality in Power BI as Single Source

**What goes wrong:** Power BI is a reporting layer over Amazon reports, which have known issues:
- FBA fee reversals/reimbursements appear as negative values — naïve summing makes a reimbursed period look cheaper
- Settlement periods cross month boundaries
- Storage fees may post to a different reporting month than the inventory snapshot month

**Prevention:**
- Clarify with Gustavo: are credits already netted in the Power BI model, or separate line items?
- Build data quality check as the first step of every run: count of SKUs, sum of fees, count of zero-fee SKUs. If any deviate >30% from prior run, halt and alert instead of computing anomalies.
- Document Power BI data model assumptions in Phase 1 technical discovery.

**Phase:** Phase 1 must include explicit data quality validation.

---

### ⚠️ MODERATE — P8: Context Window Management

**What goes wrong:** Passing all SKU-level fee data for all periods into a single LLM context. Token limits make it impossible at scale, and LLMs perform poorly on numerical reasoning across many rows.

**Prevention:**
- Compute anomalies in Python, not inside the LLM. LLM receives only pre-computed anomaly list.
- Pipeline: `data fetch → statistical computation (Python) → anomaly scoring (Python) → LLM receives anomaly list only → LLM generates narrative → post to ClickUp`
- If full SKU list needs summarizing: batch by 20-30 SKUs per LLM call

**Warning signs:** Prompt construction logic includes SQL query results or DataFrames dumped directly into f-strings.

**Phase:** Phase 1 architecture decision — define data/LLM boundary explicitly before writing any code.

---

### ⚠️ MODERATE — P9: n8n Workflow Silent Failures

**What goes wrong:** n8n workflows can fail silently: node times out but marks as success, errors swallowed without explicit error branch, scheduled triggers skip runs during high load. A skipped run means a week of anomalies go undetected.

**Prevention:**
- Every n8n workflow must have explicit error branch: "AUDIT RUN FAILED — [error details]" comment to ClickUp.
- Implement run heartbeat: post "run started" comment to ClickUp before any data processing. If Victor sees "run started" with no follow-up, he knows it failed.
- Use n8n's Error Trigger node to catch uncaught exceptions at workflow level.
- Store each run's output in BigQuery so run history is verifiable outside n8n's execution log.

**Warning signs:** ClickUp shows "run started" comments without completion in 2+ consecutive weeks.

**Phase:** Phase 2 (workflow reliability hardening); heartbeat pattern in Phase 1 from the start.

---

### ⚠️ MODERATE — P10: Over-Engineering Agent Decomposition Too Early

**What goes wrong:** Designing a multi-agent system (data agent, analysis agent, reporting agent, orchestration agent) before the single-agent version has run even once. Multi-agent systems multiply failure modes, inter-agent communication bugs, and state management concerns.

**Prevention:**
- Hard rule: ship single-agent v1, run it 4+ weeks, identify actual pain points. Decompose only when a specific identified bottleneck justifies it.
- Do not design agent interfaces before the single agent exists — extract from working code, not anticipated in advance.
- PROJECT.md already has this in Out of Scope. Treat any Phase 1 pressure to add orchestration layers as a red flag.

**Phase:** Relevant from Phase 1 through Phase 2. Revisit only at milestone boundary after real operational data.

---

### ℹ️ MINOR — P11: ClickUp Comment Verbosity

**What goes wrong:** LLM generates a comprehensive narrative by default. Victor opens ClickUp and sees 800 words. He stops reading after the first run.

**Prevention:**
- Strict output template in system prompt: (1) one-line status, (2) bullet list of top anomalies with dollar amounts, (3) one-sentence action request. Full analysis in attached file only.
- Token-budget the output explicitly: "Generate ClickUp comment under 150 words."

**Warning signs:** Draft ClickUp output during development is more than one screen of text.

**Phase:** Phase 1 prompt design.

---

### ℹ️ MINOR — P12: Marketplace Mixing Without Segmentation

**What goes wrong:** OrganiHaus sells US, UK, CA, EU, MX. Fee structures, currencies, and storage calendars differ. Mixing marketplaces in baselines blends incompatible fee structures.

**Prevention:**
- From day one, include `marketplace` as first-class dimension in the data model even if v1 only processes US.
- Document explicitly: threshold calibrated on US data does not transfer to UK/EU without recalibration.
- Data query must include explicit marketplace filter — don't rely on Power BI "only having US data."

**Phase:** Phase 1 data schema.

---

## Open Questions for Phase 1 Discovery

1. Does Power BI model net out FBA fee credits/reimbursements, or do they appear as separate line items? (Pitfall 5)
2. What is the current active SKU count in US? (Alert volume and context window planning)
3. Does Power BI expose fee-per-unit, or only total fees per period per SKU? (Pitfall 3)
4. How frequently has Amazon re-measured OrganiHaus products? (Pitfall 3 — historical examples to validate against)
