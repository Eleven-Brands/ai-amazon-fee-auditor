---
phase: 2
slug: detection-output-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-28
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.3 |
| **Config file** | `pytest.ini` (exists — `testpaths = tests`, `addopts = -q`) |
| **Quick run command** | `pytest tests/test_detection.py -x -q` |
| **Full suite command** | `pytest tests/ -x -q` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_detection.py -x -q`
- **After every plan wave:** Run `pytest tests/ -x -q` (full suite including Phase 1 regression)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** ~3 seconds

---

## Per-Task Verification Map

| Task ID | Req | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|-----|------------|-----------------|-----------|-------------------|-------------|--------|
| rolling baseline | DETECT-02 | — | shift(1) excludes current week from its own baseline | unit | `pytest tests/test_detection.py::test_rolling_baseline_excludes_current_week -x -q` | ❌ Wave 0 | ⬜ pending |
| threshold flagging | DETECT-02 | — | 15% flags correctly; below-threshold not flagged | unit | `pytest tests/test_detection.py::test_anomaly_threshold_15pct -x -q` | ❌ Wave 0 | ⬜ pending |
| sparse history | DETECT-02 | — | min_periods=1 handles < 8 weeks without error | unit | `pytest tests/test_detection.py::test_sparse_baseline_min_periods -x -q` | ❌ Wave 0 | ⬜ pending |
| consecutive count | DETECT-03 | — | count increments across consecutive weekly runs | unit | `pytest tests/test_detection.py::test_consecutive_count_increments -x -q` | ❌ Wave 0 | ⬜ pending |
| gap reset | DETECT-03 | — | count resets when gap week detected (±1 day tolerance) | unit | `pytest tests/test_detection.py::test_consecutive_count_resets_on_gap -x -q` | ❌ Wave 0 | ⬜ pending |
| sustained shift | DETECT-03 | — | consecutive >= N → sustained_shift classification | unit | `pytest tests/test_detection.py::test_sustained_shift_classification -x -q` | ❌ Wave 0 | ⬜ pending |
| narrative payload | OUT-01 | — | generate_narrative() called with correct anomaly_summary structure | unit (mocked) | `pytest tests/test_detection.py::test_generate_narrative_payload -x -q` | ❌ Wave 0 | ⬜ pending |
| CSV columns | OUT-02 | — | attachment CSV contains all D-18 required columns | unit | `pytest tests/test_detection.py::test_csv_attachment_columns -x -q` | ❌ Wave 0 | ⬜ pending |
| sustained in CSV | OUT-02 | — | sustained-shift rows in CSV with sustained_shift=True | unit | `pytest tests/test_detection.py::test_csv_includes_sustained_shift_rows -x -q` | ❌ Wave 0 | ⬜ pending |
| config drives task | OUT-03 | — | task_id in config drives ClickUp target, no code change | unit (mocked) | `pytest tests/test_detection.py::test_config_drives_task_id -x -q` | ❌ Wave 0 | ⬜ pending |
| escalation prompt | ESC-01 | — | comment ends with exact escalation prompt string | unit (mocked) | `pytest tests/test_detection.py::test_escalation_prompt_in_comment -x -q` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_detection.py` — 11 unit tests listed above (RED state until Wave 1+)
- [ ] `snapshots/.gitkeep` — create `snapshots/` directory with `.gitkeep`; add `snapshots/*` + `!snapshots/.gitkeep` to `.gitignore`
- [ ] `audit_config.json` — default config at project root: `{"THRESHOLD_PCT": 15, "CLICKUP_TASK_ID": "PLACEHOLDER", "RECIPIENTS": [], "SUSTAINED_SHIFT_N": 4}`
- [ ] Update `.env.example` — add `CLICKUP_API_KEY=` and `ANTHROPIC_API_KEY=` placeholders
- [ ] Update `requirements.txt` — add `anthropic==0.101.0`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Claude returns ≤150 words | OUT-01 | Requires live ANTHROPIC_API_KEY | Run `python run_audit.py` with real config; count words in ClickUp comment |
| ClickUp comment appears on task | OUT-01/OUT-02 | Requires live CLICKUP_API_KEY + real task ID | Set `CLICKUP_TASK_ID` in audit_config.json; run audit; verify comment + CSV attachment on task |
| CSV attached to same ClickUp comment | OUT-02 | Requires live ClickUp API | Verify attachment visible in ClickUp task after run |
| Escalation prompt readable in comment | ESC-01 | UX check — formatting | Read the posted ClickUp comment; confirm "Reply YES" is visible at end |

---

## Security Notes (ASVS L1)

- `CLICKUP_API_KEY` and `ANTHROPIC_API_KEY` stay in `.env` — never in `audit_config.json`
- ClickUp auth: `Authorization: {CLICKUP_API_KEY}` header (NO "Bearer" prefix — pk_... tokens are passed raw)
- `.env` is git-ignored; `audit_config.json` is git-tracked (contains only non-secret calibration values)

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
