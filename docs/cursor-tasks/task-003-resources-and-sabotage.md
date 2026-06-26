# Cursor Agent Task: Intel Points (IP) Economy + Sabotage Abilities

**Context**: Chart-Fights. Primary references:
- docs/design/game-mechanics-spec.md (sections 2, 5, 6, 7)
- docs/design/GDD.md

**Goal**: Implement the IP resource system and the three core sabotage abilities + expensive news peek, with costs, cooldowns, notifications, and server-side effects.

## Requirements (from spec)
**Intel Points (IP)**:
- Start 50, soft cap ~200.
- Passive +0.5 / real second.
- +10% of realized P&L on profitable closes (as IP).
- Spent on feeds, peek, sabotage.

**Sabotage (all IP cost, real-time cooldowns, always notify victim)**:
1. Delete Stop Losses (30 IP, 60s cd): Remove opponent's SL orders.
2. Widen Spreads (25 IP, 45s cd, lasts 15 real sec): Adverse fill slippage 0.4-0.8%.
3. Inject Fake News (40 IP, 90s cd): Plant misleading headline in victim's view.

**Expensive Peek** (60 IP, 1/use or 120s cd): Reveal actual major headline at current T.

All effects are server-authoritative. Victim always gets clear message + timestamp.

**Fairness**: High cost + cooldowns. No stealth. Trade well → earn IP → fund advantage.

## Acceptance Criteria
1. IP manager: regen, P&L grants, spending with validation.
2. Ability system: cooldown tracking, cost checks, effect application.
3. Concrete implementations for the 3 sabotages + peek (mock or real hooks into order system, news system, fill logic).
4. Victim notification system (messages/events).
5. Tests for economy (P&L → IP), cooldowns, costs, and effect application.
6. Clean separation: abilities don't assume full UI or data layer.

## Cursor Agent Prompt
"Implement the Intel Points economy and sabotage abilities exactly per docs/cursor-tasks/task-003-resources-and-sabotage.md and game-mechanics-spec.md sections 2,5,6,7.

Create IP tracking with passive regen and P&L grants. Implement the three sabotages (Delete SLs, Widen Spreads, Fake News) and the Expensive Peek with exact costs and cooldowns from the spec.

All sabotage must notify the victim. Effects must be server-side and deterministic. Include tests for IP economy and cooldown enforcement. Hook placeholders for later integration with orders/news/clock.

Do not implement time/tempo (see task-002) or full trading engine yet. Follow the spec numbers and rules precisely."

## Notes
- Coordinate with time engine (shared T for effects).
- Victim notification is key for psychology and counterplay.
- This + time system unlocks most MOBA-style gameplay.

**Priority**: High (enables the "sabotage and mind games" core fantasy).

## Additional Research Notes

**Extracted Mechanics (game-mechanics-spec.md §2/6/7; GDD §6; task-003):**
- IP: start 50 +0.5/s passive regen + 10% realized profitable P&L grants (soft cap ~200). Not for TB (task-002).
- Delete SL (30 IP / 60s cd): remove all (or 1-2 random) victim SLs.
- Widen Spreads (25 IP / 45s cd; 15s duration): 0.4-0.8% adverse slip on victim's market/limit fills.
- Fake News (40 IP / 90s cd): plant misleading headline ~T in victim feed *only*.
- Peek (60 IP; 1/use or 120s cd): reveal actual major headline at current T (caster only).

**Server Effect Hooks / Validation (arch §4 Ability/IP Resolver in SimulationEngine; roadmap Phase 2):**
- IP/Cooldown: per-player state (ip: float, cooldowns: dict[ability, last_ts]). On cast: if ip >= cost && (now - last >= cd) then deduct, set last=now, apply.
- Delete SL: mutate victim orders (filter type=SL); deterministic.
- Widen: set victim.effect.widen_until = now + 15s (real). On fill (hook task-004): if active, price = base * (1 + adverse 0.004-0.008 rand/dir).
- Fake News: append to victim-private news_events[] (server T-tied; never broadcast to caster/opponent full).
- Peek: arena news lookup by T; private reply event only.
All server-authoritative (clients actions only). Use real wall time for cds (spec). Tie effects to shared T for duration (e.g. bars during window).

**Victim Notification UX (spec §7 "always notify"; GDD §8 psych):**
- Broadcast EventDelta {type:"sabo"|"peek", ability, ts: real_wall + sim_T, msg: "Your stop losses were deleted (sabotage)."} *to victim only*.
- UI: immediate toast (sticky 4-6s + "sabotage" icon), + append timestamped match log. Spreads: "Anomalous spreads detected on your trades." Fake: "Possible misinformation in news feed." Enables counterplay/bluff. Timestamp critical for timing mind games.

**Economy Balance Notes (spec §2/7 "trade well → earn IP"; GDD):**
P&L grants (10% profitable closes) reward good play directly funding vision/sabo (MOBA loop). High costs relative to regen (~50-120s pure regen for one cast) + opportunity (IP not for feeds) enforce fairness/spam prevention. No negative IP; asymmetric info (feeds private) amplifies. Backfire risk (tilt) intentional.

**Psych Integration (GDD §8; RESEARCH_STATUS FXR excerpts; research/chart-fights-research-notes.md analogs):**
MOBA fantasy + psych/mind games + voice tie. Pair sabo casts with voice taunts: post-Delete SL "Nice SLs... or were they?"; Fake News bluff "Fed news incoming... or was that me?". TB too ("holding pause — wasting your IP"). FXR validation: "Trading is more than charts, it’s mental warfare... Live voice chat to talk strategy or trash... taunts." "Voice + sabotage + bluffing is the 'all-chat' MOBA salt" (spec §11). Integrate VoicePanel adjacent to notif feed (see task-008).

**Test Ideas (per AC 1-5; actionable for Cursor):**
- Economy: mock profitable close → assert +10% IP grant (no grant on loss); test regen tick, cap, spend validation.
- CD/IP enforcement: cast during cd/low IP → server reject + error event (no state change).
- Effect application: seed SLs → cast delete → assert removed. Activate widen → exec victim fill → assert slipped price (caster unaffected). Fake: assert in victim feed only.
- Notify: cast → verify WS EventDelta to victim only (ts accurate, not to self/full room); mock UI toast + log append.
- Cross: integrate T (002), orders/fills (004), WS deltas (005). Determinism: log actions + re-sim (arena+log) yields identical orders/IP/notifs (anti-cheat tie-in task-001).
Cross-refs: arch §4 (resolver + state + events), §2 (deltas), §6 (server auth fairness); roadmap Phase 2 (IP/sabo after 002/004/005); spec §7/11; GDD §8; STATUS (FXR mental warfare/trash + psych subs); research-notes (FXR voice trash talk).

(Word count ~295 for notes section. Spec-faithful; ready for direct Cursor paste + full design pkg.)