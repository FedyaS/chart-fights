# Setup for Long Unattended Research & Design Run

**Date:** 2026-06-26

## Permission / Approval Setup (to avoid waiting for approves)
- Global `~/.grok/config.toml`:
  - `permission_mode = "always-approve"`
  - `yolo = true`
  - `[permission]` with broad allow for Read/Grep/WebSearch/WebFetch/Edit+Write only in `docs/**`, safe Bash (ls, dir, python -c, curl, pip, git), MCP.
  - Deny: destructive rm/del, edits outside docs/ (esp. src/, backend/, the_vision/).
- Project `.grok/config.toml` (in chart-fights):
  - Same scoped allow/deny for this repo.
- `~/.claude/settings.json`:
  - `"defaultMode": "bypassPermissions"`
  - Matching permissions allow/deny.
- **Action for you**: In the Grok TUI prompt, type `/always-approve` (or `/yolo`) to activate in this session if not already reflecting the config. This combines with the rules for full bypass on allowed actions.
- Built-in fast-paths auto-approve: all reads, grep, web_search/fetch, todo, subagent control, etc.
- Safe shell commands (ls, etc.) often fast-path.

This should let me run for hours without prompting you for every tool use.

## Cursor Agent Integration
- Cursor CLI confirmed available: `cursor` command (version 3.8.23).
- I can run `cursor "path/to/file.md"` via terminal to open files/folders in Cursor for you.
- Example: Opened `docs/design/GDD.md` in Cursor.
- Workflow for "trigger Cursor agents":
  - I prepare detailed, self-contained prompts in `docs/cursor-tasks/task-XXX.md`.
  - Each includes full context + exact instructions + "Cursor Agent prompt" section.
  - You open in Cursor, start its Agent/Composer mode (or I can open the file), paste or reference the task file.
  - I can chain: open multiple task files, manage by updating them based on progress.
- To give me "Cursor agents": Since Cursor Agent is UI-heavy, the bridge is me generating the exact prompts + using `cursor` to surface files. If you have other access (e.g. Cursor terminal agent or scripts), let me know for deeper integration.

## Subagents & Background
- Use `spawn_subagent` with:
  - `background: true` (returns immediately, poll with get_command_or_subagent_output).
  - `capability_mode`: "read-only" for pure research, "read-write" when writing design docs.
  - `isolation`: "none" (shared) or "worktree" if needed (not for pure research).
- Parent manages multiple in parallel.

## Long-Run Tools Ready
- `/goal` + update_goal tool for persistent objective across turns.
- `scheduler_create` for recurring prompts (e.g. "review progress every 15m").
- `monitor` tool for tailing logs or events.
- `run_terminal_command` with `background: true`.
- `wait_commands_or_subagents`, `get_command_or_subagent_output`.
- Auto-compact at 85% (or manual /compact keep important).
- Memory: Can enable with GROK_MEMORY=1 if desired for cross-session recall.

## Scope Enforced (Research + Design Only)
- No production code changes.
- All design outputs → `docs/`.
- Permissions actively deny src/ or other coding.
- You can later review/approve the designs before any coding agents run.

## Verification Steps (you can do)
1. Type `/always-approve` here in Grok.
2. Type `/goal Conduct 4 hours of research and design on chart-fights (no coding). Produce docs for easy Cursor agent handoff. Use subagents in background. Keep going autonomously.`
3. I will spawn initial subagents and start.
4. Leave laptop awake (powercfg already set to never sleep on AC earlier).

If any tool still prompts, we can add more --allow rules or PreToolUse hooks.

All set for you to walk away. Let me know when ready or add constraints.
