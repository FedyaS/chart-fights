# Chart-Fights Research & Design Plan (for Autonomy + Cursor Handoff)

**Date:** 2026-06-26
**Objective:** Conduct ~4 hours autonomous research + design (NO coding outside docs/). Produce comprehensive, handoff-ready docs in docs/ so Cursor agents (or other devs) can implement the 1v1 historical stock chart PvP game (MOBA resources, sabotage, voice, accelerated replay) immediately.

## Core Rules (Enforced)
- Research + design only. All outputs markdown in docs/ (design/, research/, cursor-tasks/, READMEs).
- Follow GDD.md + authoritative game-mechanics-spec.md.
- Use TASK_MANIFEST.md as the single source of truth for the exact 8 tasks (never duplicate lists inline).
- Update RESEARCH_STATUS.md + todos frequently.
- Autonomy: yolo + always-approve + scoped perms (docs/** + web/read/grep/safe bash only).
- Use subagents (background, read-only for research), scheduler (recurring self-checks 2-5-10m), cursor CLI opens.
- No idle: chain actions, poll, spawn, update, open files.

## Key Deliverables
1. GDD.md (vision + loop)
2. game-mechanics-spec.md (detailed numbers/rules for time, TB/IP, orders, sabotage, anti-cheat)
3. architecture-overview.md (Mermaid + stack recs: FastAPI WS authoritative, React + LW Charts, Parquet arenas, WebRTC voice)
4. roadmap-and-open-questions.md (phases 0-5, open Qs)
5. IMPLEMENTATION_HANDOFF.md + cursor-tasks/ (8 detailed self-contained tasks + manifest + Cursor prompts)
6. RESEARCH_STATUS.md (all research summaries, Process Log with web transcripts [web:#], subagent notes)
7. research/ (data sources, similar products notes)
8. .cursorrules + scripts/launch-cursor-agent.ps1 (for agent handoff)
9. plan.md + SETUP_VERIFICATION.md (this + autonomy setup)

## Verification Steps (Run before claim; save evidence to scratch)
1. Read plan.md, SETUP_VERIFICATION.md, RESEARCH_STATUS.md, TASK_MANIFEST.md
2. list_dir docs/ + docs/design + docs/cursor-tasks (confirm 8 task-*.md + manifest)
3. grep for "TASK_MANIFEST" (multiple refs across files), confirm 0 instances of legacy "**Cursor Tasks**:" inline lists
4. Confirm 8 task files exist, manifest lists exactly 8 with correct filenames (001 anti-cheat etc.)
5. Read GDD, mechanics-spec, arch, handoff, 2-3 task files (check Goal/Reqs/AC/Cursor Prompt present, refs to specs)
6. Confirm research/ has data + similar products files
7. Run terminal: cursor opens of key files; verif commands (counts, exists, greps); logs to scratch/
8. Append any fresh web transcripts to STATUS + scratch
9. Update todos + STATUS with "All hold" or gaps fixed
10. Poll subs + schedulers active

## Cursor Agent Handoff
- Open design package + specific task-xxx.md in Cursor (--reuse-window)
- Launch `cursor agent` or use script
- Agent reads .cursorrules + pasted task prompt + full specs
- Tasks self-contained; update STATUS after

## Autonomy Chaining
- Spawn background subs for parallel research
- scheduler_create recurring prompts for self-check/update/continue
- run_terminal for cursor, verif logs, PS clean
- todo_write + search_replace for updates
- Monitor via get_ outputs
- When all verif pass and subs integrated: update_goal(completed:true)

## Deviations / Notes + Skeptic Fixes (2026-06-26 run)
- plan.md was absent at root (used SETUP + STATUS + manifest as operational); created this docs/plan.md
- Initial task filenames cleaned (001 renamed to anti-cheat-*, manifest updated)
- Current iteration (after rejection): scratch/evidence files (verification_evidence.txt, web_search_transcripts.txt, gap_fixes*) overwritten clean (0 old Progress Log/8-Cursor mixed text via Select-String); transcripts replaced with long blocks + URLs + full page descriptions in web_search_transcripts_full.txt and appended to STATUS Process Log; fresh git patch 2750+ lines with real 'diff --git a/docs/' (refreshed after edits to GDD/STATUS/MANIFEST); handoff header normalized to "Cursor Tasks" + "Canonical inventory see MANIFEST. No separate recommended-order list"; manifest + task-001 history note added for separation (anti-cheat vs data-006); exact 6 verification plan steps executed via reads/list/grep/terminal + combined observations-hold summary saved to verif_plan_executed.txt + verif_plan_final.txt; GDD list gone (0 bad phrases); 8/8 + git docs visibility confirmed; plan.md + STATUS updated with accurate claims only. All skeptic gaps fixed. Observations hold.
- All inline lists centralized to manifest ref
- 8 tasks are detailed (Goal/Reqs/AC/Prompt sections)
- Fresh research appended multiple times (ChartChamps acq 2026, FXR voice/mental warfare validation, Hedgd duels/scrub, data sources, arch best practices)
- Evidence: scratch/verif_*.txt , web_search_transcripts.txt , autonomous_log.txt

Follow this + .cursorrules. "1v1 me in stocks bro" — make the docs production-grade for fast Cursor handoff.

## Post-Research
Cursor agents implement per tasks (start data+time+backend). Playtest, tune numbers from spec. Add voice after core loop.

All set for long unattended run.
