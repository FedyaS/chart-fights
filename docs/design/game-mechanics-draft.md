# Chart-Fights Game Mechanics (Working Draft)

**DEPRECATED** — Superseded by `game-mechanics-spec.md` (2026-06-26). Kept for reference only. Use the authoritative spec for all implementation.

**Source Vision:** See the_vision/vision.md

## Core Time Model
- Real time : Simulated time = 1 second : 1 trading day
- A standard match lasts 5 real minutes → 5 "trading minutes" but representing hundreds of simulated days of price action.
- The "market" advances one bar per real second by default.
- Players have a recharging "time resource" bar (like energy or mana) that allows spending to:
  - Fast-forward (advance multiple bars per real second)
  - Pause (stop the market while planning/acting)
- Pausing recharges the bar faster.

**Details to resolve (research in progress):**
- Exact recharge rates
- Max speed multiplier
- Whether fast-forward consumes per-bar or per-real-second

## Information Asymmetry & Feeds
- Base game provides core price charts for a set of instruments (national indices + major FX).
- Players can spend resources/points to unlock additional data feeds (more indices, technicals?, correlated assets).
- "News peek" (very expensive one-shot): Reveal the actual major headline or economic event that occurred on the simulated day the match clock is at.

## Sabotage / Interaction
- Abilities to interfere with opponent:
  - Remove or move their stop-loss orders
  - Widen their effective spreads temporarily
  - Inject fake news (misleading signal)
- These should have high cost, cooldowns, risk of backfire or detection to keep it balanced and fun.

## Normalization & Anti-Cheat
- All price series reset to 100.00 at the start of every match.
- Players see and trade relative percentage changes only.
- Goal: Prevent easy "I know what SPX did on this date in real life" cheating.
- Economic indicators and news may be harder to obscure — research mitigation (scrambled labels, synthetic events, limited precision).

## Match Structure
- 1v1
- Fixed duration or best-of style?
- Win condition: Higher P&L / portfolio value at end of match.
- Voice + text match chat for trash talk and mind games (huge part of the fun per vision).

## Open Design Questions (to be answered in research)
- Order types available (market, limit, stop, etc.)
- Leverage / margin rules
- Starting capital
- How "positions" persist across fast time
- UI for placing trades while time is running
- Spectator / replay mode?

This is a living draft. Will be expanded by research subagents.
