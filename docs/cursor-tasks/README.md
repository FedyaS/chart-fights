# Using Cursor Agents with Grok (for chart-fights)

## How Grok Can "Run" Cursor Agents

Grok has direct access to the `cursor` CLI, including the powerful `agent` subcommand.

### Core Mechanism
1. Grok prepares or selects a detailed task (in `docs/cursor-tasks/`).
2. Grok uses the terminal to open relevant context files in your Cursor IDE:
   - `cursor docs/design/GDD.md docs/design/game-mechanics-spec.md --reuse-window`
3. Grok launches the Cursor agent:
   - `cursor agent`
4. The agent inherits:
   - The open workspace
   - The `.cursorrules` file (project-specific instructions)
   - The opened task file as the primary spec

### Recommended Way to Trigger (what Grok will do)
- Grok will often run a helper or direct commands like:
  ```powershell
  cd "C:\Users\fedse\Documents\Github\chart-fights"
  cursor docs/design/game-mechanics-spec.md docs/cursor-tasks/task-002-time-and-tempo.md --reuse-window
  cursor agent
  ```

### Using the Helper Script
```powershell
# Launch with full context
.\scripts\launch-cursor-agent.ps1

# Launch focused on a specific task
.\scripts\launch-cursor-agent.ps1 -Task "002-time-and-tempo"
```

### Tips for Best Results
- Have Cursor open or let Grok open the files first.
- The agent respects the rules in `.cursorrules`.
- Feed the full task file content as the main instruction.
- You can continue the agent conversation in the terminal or switch to the GUI composer.

This setup lets Grok autonomously prepare high-quality work and directly invoke Cursor's agent when needed.

## Current Tasks Available
See docs/cursor-tasks/TASK_MANIFEST.md for the canonical inventory of 8 tasks. Each task-*.md is self-contained with goal/requirements/non-goals/references to GDD+mechanics-spec.
