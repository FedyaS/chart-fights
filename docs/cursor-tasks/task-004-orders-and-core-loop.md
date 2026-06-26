# Cursor Agent Task: Orders, Positions & Core Player Loop (MVP)

**Context**: Chart-Fights. References:
- docs/design/game-mechanics-spec.md (sections 3, 4, 8)
- Previous tasks (time engine from task-002, IP/sabotage from task-003)

**Goal**: Implement the core player loop, order types, position management, P&L, and win condition integration on top of the time/tempo engine.

## Requirements
- Player actions: Place/modify/cancel Market, Limit, Stop orders on instruments.
- Long/Short supported.
- Attached SL/TP modifiable live.
- Execution against the current bar at T advance.
- Unrealized P&L marked continuously; realized on close.
- Starting capital normalized (100 units).
- Final win condition: higher equity at real-time end.

Integrate with:
- Shared clock (new bars trigger marking + potential order fills).
- Sabotage effects (e.g. widened spreads on fills, deleted SLs).

## Acceptance Criteria
1. Order model + execution engine.
2. Position tracking and P&L calculator (realized + unrealized).
3. Core loop skeleton: observe -> decide -> act -> react to fills/events.
4. Basic validation and state consistency.
5. Tests for fills, partial closes, P&L at end, sabotage interaction placeholders.
6. Clean hooks for future UI.

## Cursor Prompt
"Implement orders, positions, P&L and the core player action loop per task-004-orders-and-core-loop.md and game-mechanics-spec.md sections 3,4,8.

Build on the time engine (task-002). Support Market/Limit/Stop + attached orders. Calculate P&L correctly as T advances. Handle sabotage effects on fills and stops.

Keep MVP simple (no complex margin). Include tests for determinism and edge cases. Wire in placeholder hooks for IP/sabotage from task-003."

**Priority**: Completes the playable core once time + abilities are done.
