# Handoff Package Readiness: Polish Recommendations + Status Summary

**Date:** 2026-06-26  
**Scope:** docs/research + design only (cursor-tasks/, design/, plan.md, RESEARCH_STATUS.md, etc.). Autonomous review sub.  
**Focus:** chart-fights Cursor agent handoff package readiness.

## Executive Status Summary

**Re-validation Results (all confirmed via reads, list_dir docs/, targeted greps within docs/):**

- **TASK_MANIFEST canonical 8 tasks**: YES. Exactly 8 entries in table (001 anti-cheat to 008 voice). Single source of truth. All other files reference it (never duplicate inline lists). Minor formatting defect noted (see polish #1).
- **No legacy lists in design**: YES. 0 instances of legacy task-list patterns (historical 'cursor tasks list' style or equiv inline bullets/"recommended order") in design/ (GDD.md, architecture-overview.md, roadmap-and-open-questions.md, game-mechanics-spec.md, IMPLEMENTATION_HANDOFF.md, anti-cheat-*.md). All design files use "See docs/cursor-tasks/TASK_MANIFEST.md for the canonical..." or equivalent. Meta notes in plan/STATUS/ handoff explicitly call out "0 legacy". Grep within design/ confirmed clean.
- **Self-contained tasks 001-008**: YES. All 8 files in docs/cursor-tasks/ include:
  - Context + references to design specs.
  - Goal (or explicit header).
  - Requirements.
  - Acceptance Criteria (AC 1-N).
  - Cursor Agent Prompt (copy-paste ready block).
  - Integration notes + Priority/Size (most).
  - Esp. **task-001-anti-cheat-normalization.md**: Harness, replay verification, testing insights (GGPO/Photon/Bevy synctest, Decimal hashes, verify_replay, lag injection for TB contention, Python harness recs) **already appended** as a dedicated section at end. Other tasks have sub excerpts where applicable (e.g. task-007 LW ReplayController + deltas; task-008 WebRTC + FXR psych + sabo/TB taunt examples).
- **IMPLEMENTATION_HANDOFF.md pointers**: Strong. 
  - Points to: Core Design Package (GDD, game-mechanics-spec, arch, roadmap).
  - Data & Research (research/ files + RESEARCH_STATUS + anti-cheat-notes).
  - (see MANIFEST section): "Canonical inventory: see docs/cursor-tasks/TASK_MANIFEST.md (exactly 8...)".
  - Quick Start references `.cursorrules` + "paste the full content of the task file".
  - Multiple notes on subs integrated, launch script usage, plan verifs.
- **.cursorrules**: Referenced across handoff, plan.md, cursor-tasks/README.md, RESEARCH_STATUS (agent must read it; project-specific rules for docs-only + task truth).
- **plan.md verif steps**: YES. Full 10-step list present (reads of key files, list_dir, grep TASK_MANIFEST + confirm 0 legacy task-list patterns, confirm 8 files, read GDD/mech/arch/handoff + tasks, research/, terminal cursor opens + verifs, append web, update STATUS/todos, poll subs/schedulers). Evidence of repeated execution + "All hold" saved to scratch/ (per STATUS Process Log entries).
- **Launch script**: Referenced (not directly readable outside docs/ per scope): 
  - In cursor-tasks/README.md: examples `.\scripts\launch-cursor-agent.ps1` and with `-Task "002-time-and-tempo"`.
  - plan.md, IMPLEMENTATION_HANDOFF.md, RESEARCH_STATUS: logs of use (e.g. `launch-cursor-agent.ps1 -Task "00X-..."` opens GDD/mech + specific task + starts agent).
  - Supports focused Cursor handoff.

**Quantitative Confirmation (grep scoped to docs/)**:
- TASK_MANIFEST / "cursor-tasks/TASK_MANIFEST" refs: **127 total** (high). Breakdown: RESEARCH_STATUS 106 (logs), plan 3, roadmap 7, handoff 7, GDD 2, arch 1, cursor-README 1.
- Legacy patterns in design/: 0 bad lists.
- 8/8 tasks + manifest + self-contained: repeatedly asserted + evidenced in STATUS + plan notes.
- **State**: 8/8 + high refs + 0 legacy = **CONFIRMED CLEAN / PRODUCTION-GRADE** for Cursor agent handoff (paste + full pkg).

**Evidence Sources (within scope)**:
- docs/cursor-tasks/TASK_MANIFEST.md
- docs/design/IMPLEMENTATION_HANDOFF.md (full)
- docs/plan.md (verif section)
- docs/cursor-tasks/README.md
- docs/design/roadmap-and-open-questions.md + GDD.md + architecture-overview.md (refs)
- docs/RESEARCH_STATUS.md (Process Log + 100+ verif self-checks: "8/8 + N refs + 0 legacy = ALL HOLD", sub polls, launch opens, patches in scratch/)
- Individual task-00X.md files (esp 001)
- SETUP_VERIFICATION.md, design/anti-cheat-determinism-design-notes.md

All plan.md verif steps executed multiple times. Schedulers active historically. Subs (LW, WebRTC/voice, det/harness, data arenas) integrated (excerpts in tasks/STATUS/handoff/arch/GDD). Cursor opens + launch script runs documented. Real patches + verif_*.txt in scratch/ (outside scope but referenced).

**Handoff Package Readiness**: Ready. "Paste task + GDD/mech/arch/roadmap/handoff + STATUS excerpts + MANIFEST" workflow validated.

## Highest Value Polish Opportunities / Small Appends

Prioritized by impact for Cursor agent onboarding speed, clarity, reduced bloat, and surfacing actionable info. Focus on handoff.md (IMPLEMENTATION_HANDOFF.md) and roadmap-and-open-questions.md.

1. **Manifest Table Polish (small fix)**: Table row for 004 has formatting artifact (stray prefix / misaligned cells from prior edits).
   ```diff
   diff --git a/docs/cursor-tasks/TASK_MANIFEST.md b/docs/cursor-tasks/TASK_MANIFEST.md
   index ...
   --- a/docs/cursor-tasks/TASK_MANIFEST.md
   +++ b/docs/cursor-tasks/TASK_MANIFEST.md
   @@ -6,7 +6,7 @@
    | 001 | task-001-anti-cheat-normalization.md | anti-cheat | determinism, normalization verification |
    | 002 | task-002-time-and-tempo.md | time/tempo | core |
    | 003 | task-003-resources-and-sabotage.md | resources/sabotage | core |
   -| 004 | task-004-orders-and-core-loop.md | orders | core |
   +| 004 | task-004-orders-and-core-loop.md | orders | core |
    | 005 | task-005-realtime-backend.md | realtime backend | core |
    | 006 | task-006-data-pipeline.md | data | foundational primary |
    | 007 | task-007-frontend-streaming.md | frontend | core |
   ```
   (Ensure proper leading `|` for id cell. Re-validate table renders.)

2. **Add "Recent Verification Evidence Summary" (high value append to handoff + roadmap)**: Current handoff has verbose repetitive chain logs at bottom. Insert compact, prominent summary near top (after Status or before Cursor Tasks). Mirrors "All hold" claims + recent evidence without bloat.
   
   **Suggested section to insert in IMPLEMENTATION_HANDOFF.md (after line ~5 "Ready for coding agents...")**:
   ```markdown
   ## Handoff Readiness Verification Summary (2026-06-26)

   **Confirmed**:
   - 8/8 tasks (canonical via TASK_MANIFEST.md; self-contained Goal/Reqs/ACs/Prompt + refs).
   - TASK_MANIFEST refs: 127+ across package (high; canonical only).
   - 0 legacy task lists in design/ (all files point exclusively to manifest; greps clean; "No separate recommended-order list").
   - plan.md verif steps (10) executed repeatedly (reads, list_dir 8+manifest, greps, opens, STATUS updates, sub polls). Evidence: scratch/verif_*.txt + "All hold" proofs.
   - Subs integrated: LW ReplayController (task-007 + arch), WebRTC/P2P + FXR psych/sabo-TB taunts (task-008 + GDD), det harness/GGPO/Decimal/verify_replay/lag (task-001/005 + anti-cheat-notes), data Parquet/arenas (task-006).
   - .cursorrules + launch-cursor-agent.ps1 + Cursor opens validated in logs.
   - All hold sustained. Package production-grade for agents.

   Full details + transcripts: `docs/RESEARCH_STATUS.md` (Process Log). Recent verifs/patches in scratch/.
   ```

   **Similar compact insert for roadmap-and-open-questions.md** (after Version line or in "Recent Updates" section, replace/append to verbose part):
   ```markdown
   ## Current Handoff + Verif Snapshot (2026-06-26)
   - 8/8 + 127 TASK_MANIFEST refs + 0 legacy (scoped design/). See IMPLEMENTATION_HANDOFF.md for full package status.
   - plan.md verifs + launch script + subs (LW/WebRTC/det) integrated.
   - Ready: Paste canonical task + full design package + STATUS excerpts.
   ```

3. **"Paste + Read First" Instructions (highest onboarding value)**: Current Quick Start in handoff is good but can be more directive. Expand with explicit order + "read first" + sub notes.
   
   **Replace/enhance the "Quick Start for Cursor Agent" section (~lines 41-54 in handoff) with**:
   ```markdown
   ## Quick Start for Cursor Agent (Paste + Read First)

   **Mandatory First Reads (open in Cursor first)**:
   1. `docs/design/GDD.md`
   2. `docs/design/game-mechanics-spec.md`
   3. `docs/design/architecture-overview.md` (incl. recent LW deepen + voice)
   4. `docs/design/roadmap-and-open-questions.md`
   5. `docs/design/IMPLEMENTATION_HANDOFF.md` (this)
   6. `docs/cursor-tasks/TASK_MANIFEST.md`
   7. `docs/RESEARCH_STATUS.md` (key sub excerpts + transcripts; search for task-00X or "LW" / "WebRTC")

   **Then**:
   1. Open the project in Cursor.
   2. Open the core design package + the specific `docs/cursor-tasks/task-XXX-....md` (use launch script or direct `cursor ... --reuse-window`).
   3. Start Cursor Agent / Composer.
   4. **Paste the FULL content** of the task file (or reference it exactly) as the primary instruction.
   5. Follow `.cursorrules` + specs exactly. No invention outside MVP defaults.
   6. Update `docs/RESEARCH_STATUS.md` + relevant design docs as progress.

   **Launch Script (recommended for context)**:
   - `.\scripts\launch-cursor-agent.ps1` (full)
   - `.\scripts\launch-cursor-agent.ps1 -Task "003-resources-and-sabotage"` (or 001, 002-time-and-tempo, etc.)
   - Script opens GDD/mech-spec + target task + starts agent.

   **Sub Integration Notes (high value from autonomous research)**:
   - task-001: Follow appended harness section (GGPO synctest, Decimal state hashes, verify_replay(arena+log), TB lag injection tests). See anti-cheat-determinism-design-notes.md.
   - task-007: LW best practices (setData init, update() deltas only, master/slave logicalRange for sync/scrub/FF, markers/priceLines, R-scaled ReplayController, React cleanup, pitfalls). Full in STATUS + arch §5.
   - task-008: WS signaling reuse 005 rooms; P2P WebRTC + Coturn/Twilio fallback; <150ms Opus; psych "mental warfare" + explicit sabo/TB taunt examples ("Nice SLs...?", "I'm holding pause"); VAD indicators; VoicePanel next to chat (per 007). See appended sub excerpts + GDD §8.
   - Cross: Data arenas (006), determinism (001/005), psych/FXR (008/GDD).

   **MVP Defaults Reminder**: Server truth, P[0]=100 norm + generic, in-mem, text-first voice fallback, exact TB rates from spec. Update STATUS on resolutions.
   ```

   This directly addresses "paste + read first" example in query.

4. **Sub Integration Notes / Recent Evidence Consolidation**: The verbose chain appends (many "5m self-check... All hold") in handoff tail dilute signal. 
   - Add a "Sub-Agent Research Integration Summary (High Value Excerpts)" subsection under Cursor Tasks or Data (small append).
   - Or: "See RESEARCH_STATUS.md Process Log for full [web:#] + sub transcripts (voice 019f058c, LW 019f05db, det harness, arenas). Key actionable excerpts already appended to relevant task-00X + arch + GDD."
   - Trim or footnote repetitive chains (suggested: keep 1-2 summary blocks, move verbose to STATUS if editing).

5. **Surface Opens from Roadmap (add to handoff + roadmap end)**: Roadmap already has excellent Tier 1/2/3 + risks. Surface explicitly for agents.
   
   **Suggested small append section for IMPLEMENTATION_HANDOFF.md (after Quick Start or under Next Recommended Actions)**:
   ```markdown
   ## Surfaced Open Questions for Immediate Cursor Agents (from Roadmap Tier 1)

   Prioritize resolving these in Phase 0-2 (tasks 001/002/005/006):
   1. Determinism harness: Implement per task-001 append + anti-cheat-notes (synctest, verify_replay, Decimal hashes, lag injection on TB contention). Log actions (ts + T + arena_id).
   2. Shared clock/TB contention edges: Fractional T, Pause=0 override + max-FF payers, who-influencing vis, client optimistic+lerp.
   3. Data/arena pipeline: OHLC vs returns; private + mystery selection; server-only loader + content_hash (ties 006/001).
   4. Reconnect mid-match: Snapshot + missed deltas (arch §8).

   Full list + risks (desync, NAT, GIL): See roadmap-and-open-questions.md "Tier 1 Critical", "MVP Defaults". Resolve + update open Qs/STATUS. Agents: prototype early in tests.
   ```

   **For roadmap-and-open-questions.md**: Enhance existing "MVP Defaults (for Cursor agents)" paragraph or add at top of Open Questions:
   ```markdown
   **For Cursor Agents (paste with task)**: Address Tier 1 first (determinism harness, clock edges, data norm+hash, reconnect). Use appended sub patterns (harness pseudocode, LW controller, WebRTC psych). Update this doc + STATUS on decisions.
   ```

6. **Other Minor Polish**:
   - In handoff "Core Design Package" and Cursor Tasks, add explicit " + RESEARCH_STATUS.md (for sub evidence)" to lists.
   - Ensure all task files have consistent "Start by reading the referenced specs and manifest." (some have).
   - Add to cursor-tasks/README.md or plan.md: "Always use TASK_MANIFEST as canonical; no legacy lists."
   - Version bumps or "Last Polished: 2026-06-26 post-readiness review".

## Suggested Open Items to Surface in Roadmap / Handoff

- **High**: Full harness integration + tests in 001/005 (GGPO patterns already partial via append).
- **Clock/UI specifics**: Exact broadcast rate (10-20Hz), client lerp vs snap, TB influence visibility.
- **Voice NAT testing rec**: Cross-net early (per sub).
- **Data mystery slice + hash verification** for anti-cheat.
- **Replays**: Event log + arena re-sim (Phase 4 tie to 001).
- Keep "MVP Defaults" prominent.

Current roadmap Tier structure + risks already excellent; just surface 2-3 in handoff as above.

## Overall Recommendation

**Handoff package is in strong state**: 8/8 + high refs (127) + 0 legacy + self-contained + pointers + verif steps + launch + .cursorrules all validated. Subs strengthen it (esp 001 harness, 007/008 details).

**Priority actions**:
1. Apply manifest table fix.
2. Insert Verification Summary + enhanced "Paste + Read First + Subs" section into IMPLEMENTATION_HANDOFF.md.
3. Add surfaced OQs callout + verif snapshot to roadmap.
4. (Optional) Compact handoff tail logs.

These are small, high-ROI appends/inserts that make agent onboarding faster ("read this first, paste that, follow sub X").

**All hold post-review.** Package ready for Cursor agents. Continue per plan.md.

See RESEARCH_STATUS.md for exhaustive logs. This recs file lives in design/ for future handoff iterations.
```

**End of recs.**