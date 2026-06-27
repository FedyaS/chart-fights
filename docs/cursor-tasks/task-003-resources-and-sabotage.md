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

## Deep Research Resolutions (sibling worker, 2026-06-26)

Resolves the **IP economy** and **sabotage visibility/granularity/counters** open questions from `game-mechanics-spec.md §2/§6/§7` ("Open") and `roadmap-and-open-questions.md` (Tier 2). All resolutions preserve exact numbers: IP start 50, +0.5/s passive, +10% realized P&L on profitable closes, soft cap ~200; Delete SL 30 IP / 60s cd; Widen Spreads 25 IP / 45s cd / 15s effect / 0.4–0.8% adverse; Fake News 40 IP / 90s cd; Peek 60 IP / 120s cd (1/use).

### IP Economy

**OQ-IP1: IP from unrealized P&L? → No. Realized-only.**
Grant +10% of realized P&L **only on profitable closes** (full or partial, see OQ-IP5). Unrealized P&L grants **no IP**. Rationale: paying on unrealized would let a player sit on a paper gain and farm IP passively, then it would have to be clawed back when the position reverses — a netting nightmare that also breaks determinism on order of marks. Realized-only makes IP a clean, monotonic reward for *closing* good trades (MOBA "you get the gold when you secure the kill", not for poking). It also tightens the loop the spec wants: "trade well → close → fund info warfare".

**OQ-IP2: Can IP go negative? → No. Spends are gated; balance floored at 0.**
Every spend is validated server-side: a cast/unlock requires `ip >= cost` AND cooldown ready; otherwise the action is **rejected with an error event** and zero state change (no partial spend, no debt). IP can never be driven below 0. Losses on trades simply grant no IP (they do **not** subtract IP) — trading P&L and the IP pool are separate ledgers; only the +10%-on-profit bridge connects them.

**OQ-IP3: Soft cap ~200 behavior → soft cap by clamping passive/grant gains, no decay, no hard wall on earning trades.**
Recommended MVP rule: **clamp at 200** — passive regen and P&L grants stop adding once `ip == 200` (gains are clipped, not banked). No decay above the cap (decay punishes players for the crime of not spending and adds non-determinism). Because it is a *soft* cap conceptually, allow a single large realized-P&L grant to **overshoot to a hard ceiling of 200** (i.e. clamp the post-grant total to 200) rather than refusing the close — you never block a trade close on IP grounds. Net effect: 200 is the working maximum balance; the "soft" framing just means we reach it gradually and never punish reaching it. Keep `IP_SOFT_CAP = 200` and `IP_DECAY = 0` as tunable config.

**OQ-IP4: Anti-burst / anti-spam.**
Three overlapping brakes, all already in the spec — make them explicit:
1. **Cooldowns** (45–90s real per ability) prevent re-casting the same sabotage; this is the primary spam gate.
2. **Cost vs. regen ratio**: passive regen is +0.5/s, so one Delete SL (30) ≈ 60s of pure regen, Fake News (40) ≈ 80s, Peek (60) ≈ 120s. A player living on passive income alone can afford **roughly one sabotage per cooldown window and nothing else** — bursting multiple abilities back-to-back requires having *traded well* to bank IP. This is the intended skill/economy coupling; do not add a separate global "ability lockout".
3. **Optional global micro-cooldown (GCD)**: a 1.0s server-side floor between *any* two IP spends from the same player, purely to stop pathological same-tick double-casts and to keep the notification feed readable. Cheap, deterministic, and prevents UI/notification flooding. Mark as tunable (`GCD = 1.0s`); can be 0 if playtests show it unnecessary.

**OQ-IP5: Partial-close grants.** When a partial close realizes profit, grant +10% of *that realized chunk* (consistent with OQ-IP1). Track realized P&L per close event so grants compose correctly across multiple partials (see task-004 OQ-O6 for partial-close P&L accounting). Losing partials grant nothing.

### Sabotage

**OQ-SAB1: Always-notify — confirmed, victim-only, timestamped.**
Every sabotage broadcasts an `EventDelta` **to the victim only** (never to the caster's view, never to a shared log mid-match) with `{type, ability, real_ts, sim_T, msg}`. Exact messages: Delete SL → "Your stop losses were deleted (sabotage)."; Widen → "Anomalous spreads detected on your trades."; Fake News → "Possible misinformation in news feed." The caster gets only a generic "ability resolved" confirmation. The timestamp (`real_ts` + `Sim Day T`) is mandatory — it is the hook for counterplay and the "when did that happen?" mind game. No stealth sabotage, ever.

**OQ-SAB2: Instrument-specific targeting? → No for MVP; sabotage is player-targeted and global to the victim.**
- **Delete SL** removes the victim's SLs across *all* instruments (default) — or, per spec's "all (or 1–2 random)", use a tunable `DELETE_SL_MODE`: MVP default = **delete ALL of the victim's active SL orders** (simplest, highest-impact, clearest to communicate). The "1–2 random" variant is a balance lever if all-delete proves too swingy; if used, the RNG must be **seeded deterministically** from `(arena_seed, action_index)` so replays reproduce the exact SLs removed.
- **Widen Spreads** applies to *all* of the victim's fills during the window (not per-instrument).
- **Fake News** plants in the victim's news feed at the current `T` (news is arena-global, so no instrument scoping needed in MVP).
Instrument-targeted sabotage (e.g. "widen only their Tech Index") is an explicit **post-MVP** depth lever; it adds a targeting UI and more state without being needed for the core fantasy.

**OQ-SAB3: A "purge"/counter ability? → Not in MVP. Counterplay is built into detection + cooldowns.**
Do **not** add a dedicated purge/cleanse ability for MVP. Counterplay already exists and is sufficient: (a) the victim is *always notified with a timestamp*, so they can immediately re-place deleted SLs, widen their own stop distances, or distrust a flagged headline; (b) the attacker paid IP + ate a cooldown, so a wasted/backfiring sabotage is itself the punishment; (c) voice/chat bluffing is the social counter ("didn't need those SLs anyway"). A purge would compress this counterplay into a button and is reserved as a **post-MVP** ability if metrics show sabotage is oppressive. Document as a tunable future option, not MVP scope.

**OQ-SAB4: Widen Spreads × fills interaction.**
The Widen effect sets `victim.effects.widen_until = now + 15s` (real wall time, per spec). The **fill hook in task-004** must check this on *every* market/limit fill for the victim during the window and apply an adverse offset:
- Adverse direction = always against the victim: buys fill higher, sells/closes fill lower.
- Magnitude: pick within **0.4%–0.8%**. For determinism, do **not** use live RNG — derive the magnitude deterministically, e.g. `0.004 + 0.004 * frac(hash(arena_seed, fill_event_index))`, or simply use a fixed `0.006` (mid-band) for MVP with `WIDEN_PCT` configurable. This stacks *on top of* the normal base spread/slippage (task-004 OQ-O4), it does not replace it.
- Only the **victim's** fills are affected; the caster's fills are untouched. If both players have widen active on each other, each applies to their own fills independently.
- Edge: a fill that triggers exactly as `widen_until` expires uses wall-time comparison at the moment of bar application; document the boundary as inclusive-start/exclusive-end (`now < widen_until`) so it's reproducible.

**OQ-SAB5: Fake News lifetime.**
A planted fake headline is pinned to the victim's news feed at the `T` of the cast and **persists in the victim's feed for the rest of the match** (it does not auto-expire) but is **only "active"/prominent around its `T` window** (display it as a current-day banner for ~the next 10–20 simulated days / a few real seconds, then it falls into the scrollable feed history like any other event). Rationale: a headline is information that was "published" — it shouldn't silently vanish, and leaving it in history supports the post-match reveal ("that Fed headline was fake"). Optional subtle credibility flag (a faint "unverified" marker) is a **balance toggle**, default **off** for MVP (off = more deceptive = more fun bluffing; on = softer). Config: `FAKE_NEWS_PROMINENCE_DAYS = 15`, `FAKE_NEWS_CREDIBILITY_FLAG = false`.

### Expensive Peek

**OQ-PEEK1: Past days? → Current/nearest `T` only (MVP).** Peek reveals the actual major headline at the **current** simulated day `T` (or the nearest dated event within a small forward/back window if the exact day is event-less). No arbitrary historical lookups — that would turn Peek into a full news-history unlock and gut the ongoing tension. `PEEK_WINDOW_DAYS = ±5` as the search radius for "nearest".

**OQ-PEEK2: Partial or full event list? → Single most-significant headline.** Return the **one** highest-impact headline for the window, not a list. Keeps it an "ultimate" (high cost, high but focused value) rather than a data dump.

**OQ-PEEK3: Can Peek verify fakes? → No.** Peek reads the **real arena news** for the caster's *own* view. It does **not** inspect or reveal whether the *opponent* injected a fake into *their own* feed (the caster can't see the victim's feed anyway). Conversely, a player who suspects *they* were Fake-News'd cannot use Peek as a lie-detector in MVP — Peek shows the genuine headline for the current day, so if their feed disagrees with a (separately obtained) real headline they could infer a fake, but Peek is not a dedicated "verify this specific headline" tool. Keep Peek and Fake News as independent systems; a "verify" interaction is post-MVP.

### Determinism checklist for this task
- All RNG (random SL selection, widen magnitude) must be seeded from `(arena_seed, action_index)` — never `random()` / wall clock — so `verify_replay` reproduces identical removed-SL sets, slippage, and IP balances.
- Cooldowns and the 15s widen window use **real wall time** (per spec), captured at server receive time; log both `real_ts` and `sim_T` per action for the replay harness (ties to task-001/005).
- IP is a `Decimal`, quantized consistently; clamp at `[0, 200]`.

**Sources (web, 2026):**
- MOBA economy: logistic/diminishing-return utility, soft ceilings, comeback windows, anti-snowball levers (informs soft-cap-by-clamp + cost/regen ratio + no-decay choices): https://frequently-asking-questions.com/2026/04/04/the-5-minute-surrender-fallacy/
- Localized vs global reward / anti-snowball income tuning (informs realized-only grants + cooldown gating): https://www.gamer.org/smite-2-ob33-jungle-changes-best-gods-and-paths-now/
- Comeback-experience & dynamic catch-up rewards as deliberate design (supports short-match swing/comeback framing for late sabotage): https://www.leagueoflegends.com/en-us/news/dev/dev-2026-season-one-gameplay-preview/