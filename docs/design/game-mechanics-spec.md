**Game Mechanics Specification (GMS)**

**Project:** chart-fights (tradersfight.io)  
**Source:** Raw vision in `the_vision/vision.md` + working draft in `docs/design/game-mechanics-draft.md` + GDD context + data research.  
**Purpose:** Unambiguous, detailed, implementation-ready mechanics definition. This is the authoritative reference layer below the high-level GDD. All numbers, rules, and interactions are specified as concrete starting points (tunable via playtest). "1v1 me in stocks bro" with MOBA-style resource/info/sabotage gameplay layered on shared historical price action.

---

### 1. Time Model

**Core Rule:** 1 real-time second = 1 simulated trading day (1 daily bar advance).

**Match Duration:** Fixed 5 real minutes (300 real seconds) per match.  
- At base rate (R=1.0): exactly **300 simulated trading days** traversed (~1.2 trading years at ~250 trading days/year).  
- With time manipulation: final simulated day counter `T_final` can range roughly 150–1500+ days depending on net fast-forward vs. pause usage. The match always ends on the real-time clock, not on `T`.

**Shared Market Clock (T):**  
- `T` = current simulated trading day index (integer + fractional for smooth advance). Starts at `T=0`.  
- All price application, order execution, position marking-to-market, and news events are driven by the **shared** `T`. Both players compete on the exact same underlying data sequence.  
- The clock rate `R` (simulated days per real second) starts at **1.0**.  
- `R` is **globally shared and contested** (see Resource section).  
- Visual clock shown to players: generic "Sim Day NNN" or "Arena Day NNN (Q? 20XX)" — never real calendar dates during play.

**Progression Details:**  
- Bars are discrete daily closes (or OHLC aggregates). As `T` crosses integer boundaries, the new bar is revealed/applied to charts and positions for both players.  
- Non-trading days in source data are skipped or linearly interpolated at data-prep time (implementation detail).  
- 5 min real-time match = default 300 bars; variable with controls.

**Rationale for shared/contested model (vs. fully personal views):** Enables direct interaction (tempo fights), prevents desync on positions/P&L, and creates MOBA-style "objective control" over match pacing. Personal "analysis scrub" can be added later as a low-cost secondary action.

**Open:** Exact max `R`; whether fractional `T` triggers partial-bar interpolation for orders.

---

### 2. Resource System: Tempo Bar (TB) + Intel Points (IP)

Two distinct resources to separate concerns.

**Tempo Bar (TB) — 0–100 (exclusively for fast-forward / pause):**  
- **Base recharge:** +1.0 per real second (full bar in ~100s under normal conditions).  
- **Pause recharge bonus:** When a player holds Pause (and `R` is forced ≤0), that player recharges at +4.0/s.  
- **Consumption (while action is actively held, per real second):**  
  - Pause (forces `R ≤ 0`): 0 cost (purely enables faster recharge + denies opponent tempo).  
  - FF x2 (`R=2`): 2.0/s.  
  - FF x3 (`R=3`): 5.0/s.  
  - FF x5 (`R=5`): 12.0/s (drains a full bar in ~8s — high risk).  
- **Contention rules (shared `R`):**  
  - Any active Pause forces `R=0` (Pause overrides FF).  
  - Multiple FF attempts: `R = max(chosen R values)`. All paying players pay their respective costs.  
  - No active controls: `R=1.0`.  
  - Visual indicator: global "Market Speed: 1.0x / 3.0x / PAUSED" + who is currently influencing it (or anonymous).  
- **Benefits:** Strategic pacing (rush boring ranges, camp key setups).  
- **Costs:** Opportunity (drains resource you might want for later burst). No direct IP interaction.

**Intel Points (IP) — starting 50, soft cap ~200:**  
- Used for data feed unlocks, news peek, and all sabotage.  
- **Sources:**  
  - Passive regen: +0.5 / real second.  
  - Trade performance: +10% of realized P&L (in IP units) on profitable closes (encourages good trading to fund info warfare).  
- IP is **not** used for time control.

**Overall Design:** TB is "mana for tempo/mobility." IP is "gold" earned and spent on vision/sabotage (MOBA economy loop). Good P&L directly funds stronger sabotage/info advantage.

**Open/Ambiguities:** IP from unrealized P&L? Can IP go negative? Exact regen curves and caps need tuning. Burst "instant FF" actions (consume lump sum for X days jump)?

---

### 3. Core Player Loop

1. Observe live updating charts (prices advance with shared `T`).  
2. Monitor personal equity curve, open positions, pending orders, TB/IP.  
3. Place, modify, or cancel orders on any visible instrument.  
4. Manage risk (adjust SL/TP, size, close, hedge).  
5. Manipulate shared tempo with TB.  
6. Spend IP on vision (feeds), peek, or sabotage.  
7. Psychological warfare via chat/voice.  
8. React to fills, detected sabotage, and new bars.

**Loop runs continuously** for 300 real seconds. Fast decision-making + resource timing is core skill expression.

---

### 4. Orders & Position Management

- **Direction:** Long (profit when normalized price rises) or Short (profit when falls).  
- **Size:** Any (in "units" where position P&L % ≈ price % change scaled by size; starting capital = 100 units). No hard position limits initially.  
- **Order Types (MVP):**  
  - **Market:** Immediate fill at current bar price (minor base spread/slippage ~0.05–0.1%).  
  - **Limit:** Resting; fills only if price reaches the limit (favorable to player).  
  - **Stop (SL/Entry):** Resting; triggers on adverse (or desired) price.  
- **Attached Orders:** SL and/or TP can be attached to positions or orders. Modifiable while live.  
- **Execution:** All against the bar at the moment of `T` advance / trigger. Server-authoritative.  
- **Management:** Close partial/full at market anytime. Modify active SL/TP. View history of fills.  
- **P&L:** Unrealized marked continuously as `T` advances. Realized on close. Final score uses fully marked portfolio at match end.  
- **Spreads/Slippage:** Small base; can be worsened by sabotage.

**No complex margin calls** in MVP (P&L can go deeply negative; final equity determines win). Future: simple leverage caps or drawdown "tilt" penalties.

**Open:** Exact notional sizing model (percent of capital vs. absolute units). Limit order fill priority if simultaneous triggers. Options/futures later.

---

### 5. Information & Data Feeds

**Base (free):**  
- 5 core instruments with price-only charts (candles or line) + basic MA toggle.  
  Example set: Broad Equities, Tech/Growth, Europe Equities, USD/JPY, EUR/USD.  
- Generic high-impact event flags on timeline (no text).

**Premium Feeds (buy with IP, one-time unlock per match, ~20–40 IP each):**  
- More instruments (Asia indices, additional FX pairs, Gold, Oil, VIX-proxy, rates).  
- Analytics pack: full technicals (RSI, MACD, Bollinger, volume) on all charts + cross-asset correlation matrix.  
- Macro series: numeric indicator timelines (normalized deltas or levels).

**Benefits of extras:** Correlation trading, leading signals, diversification, confirmation. Meta will likely favor raw price action + timing over "fundamental" use (per vision).

Unlocks are immediate and permanent for the match. Opponent cannot see what you bought (information asymmetry).

**Open:** Recurring IP cost vs. one-time? Can feeds be "lost" via sabotage? Number of simultaneous visible charts.

---

### 6. News System + Expensive Peek

- News/events are arena-specific and tied to day offsets in the chosen historical slice.  
- **Base:** Minimal (generic flags only).  
- **Expensive Peek (Ultimate-style):**  
  - Cost: 60 IP.  
  - Uses: 1 per match (or 120s real cooldown).  
  - Effect: Reveals the **actual major headline** for the current (or nearest) simulated day `T`.  
  - Example: "Fed unexpectedly hikes 50bp — equity selloff."  
  - Extremely powerful context for recent or imminent moves. Silly/fun when it reveals something obvious in hindsight after normalization.

**Open:** Can peek be used on past days? Does it give partial or full event list? Fake news interaction (can peek verify fakes?).

---

### 7. Sabotage Abilities

All IP-cost, cooldown-based (45–90s real after cast), symmetric, high-cost relative to regen. **Always notify the victim** with clear feedback and timestamp for counterplay and mind games. No stealth sabotage.

**Implemented Effects (server-side state mutation):**  
1. **Delete Stop Losses** (30 IP, 60s cd): Remove all (or 1–2 random) of opponent's current SL orders. Victim message: "Your stop losses were deleted (sabotage)."  
2. **Widen Spreads** (25 IP, 45s cd, lasts 15 real sec / ~20 simulated days): Opponent's fills (market/limits) execute 0.4–0.8% worse (adverse). Victim message: "Anomalous spreads detected on your trades."  
3. **Inject Fake News** (40 IP, 90s cd): Plants one misleading headline in the victim's news view around current `T`. Victim message: "Possible misinformation in news feed." (Optional subtle credibility flag.)

**Fairness Safeguards:**  
- High cost + cooldowns + detection prevent abuse.  
- IP spent is IP not spent on your own vision or tempo.  
- Visual/audible cues on victim side + chat bluffing opportunities.  
- Backfire risk: obvious sabotage can tilt opponent into aggressive play.

**Open:** Can you sabotage specific instruments? "Purge" counters? Probabilistic detection? Duration tuning. "Leak position size" as fourth ability?

---

### 8. Winning Conditions

- Fixed real-time 5:00 end.  
- Winner = higher final equity (starting 100 units + all realized + marked unrealized P&L).  
- Pure relative performance.  
- Ties: draw (or secondary: highest peak equity during match, or lowest sabotage usage, or most instruments traded).  
- Displayed live as equity and % return.

**Open:** Sudden-death if data exhausted? Best-of series scoring?

---

### 9. Match Chat / Voice

- **Text:** Always-on, match-scoped chat log. Fast, persistent.  
- **Voice:** Core feature (per vision and "your SL is my TP" meme). In-game voice (WebRTC or equivalent), push-to-talk + mute, per-player volume.  
- Requirements: Low latency (<150ms target), reliable join on match start, easy mute, text fallback. Optional post-match voice log (privacy opt-in).  
- Fun factor: Bluffs, reactions, psychological pressure, "I just peeked" mind games.

---

### 10. Starting Normalization (Anti-Cheat)

- Every match uses a pre-selected contiguous historical return slice ("arena").  
- For **every** instrument: `P[0] = 100.0`.  
- `P[t] = P[t-1] * (1 + historical_daily_return[t])`.  
- Players see and trade **only % changes** from the normalized 100 baseline.  
- Instrument labels: generic during match ("Broad Equities", "Tech Index", "USDJPY Pair") or lightly anonymized. Real names/dates optionally revealed post-match.  
- Non-price data (indicators, events) similarly offset from `T=0` or normalized to deltas.

**Rationale:** Prevents "I know SPX did X on this date" lookups. Combined with private server-side arenas, makes external knowledge far less reliable.

---

### 11. Additional Mechanics for "1v1 Stocks Bro" + MOBA Feel

- **Vision / Information Asymmetry (Fog-of-War analog):** Base feeds = your "warded lanes." Premium feeds = buying extra vision/wards. More data = better map awareness.  
- **Resource Economy Loop:** Trade well → earn IP → buy vision or sabotage → create asymmetric advantage → force opponent into bad tempo decisions.  
- **Tempo as Contested Objective:** Shared clock fights feel like fighting over dragon/baron.  
- **Ability Kit (same for both):** Tempo controls (basic), vision purchases, 3 sabos + expensive peek ult. Cooldown and resource management is skill.  
- **Build Variety:** Heavy concentration in 1–2 instruments (glass-cannon) vs. diversified. Different feed purchases = different "item builds."  
- **Psychological / Social Layer:** Voice + sabotage + bluffing is the "all-chat" MOBA salt.  
- **Comeback & Swing Potential:** Short duration + volatile normalized moves + late sabotages allow huge swings.  
- **Arena Variety ("Maps"):** Pre-loaded slices (calm, trending, crisis, range-bound). Different event density and vol profiles.  
- **Post-Match:** Full replay with full visibility (including what opponent saw/bought) for learning.  
- **Skill Expression:** Precise order timing, tempo timing, resource discipline, reading incomplete info, bluffing.

**MVP Scope Constraints (from GDD):** Basic orders + 3 sabos + peek + tempo + feeds + chat. No complex derivatives, no real-money.

---

### 12. Ambiguities & Open Questions (to resolve before/full GDD or impl)

(See numbered list in thinking trace + GDD for full set. Highest priority:)  
1. Exact shared-clock contention edge cases and UI feedback. Personal-view alternative?  
2. Precise tuning (all rates, costs, durations, spread %).  
3. IP generation formula and economy balance.  
4. Sabotage visibility granularity and counters.  
5. Arena selection, anonymization strength, and data-prep pipeline details.  
6. Order model fidelity (closes only vs. high/low triggers).  
7. Voice priority and fallback.  
8. Tiebreakers, surrender, and post-match reveal policy.

---

**This spec is now detailed enough for a coding agent to implement core loop, simulation, abilities, and UI without further high-level invention.** It stays faithful to the raw vision while adding unambiguous rules, costs, and MOBA-flavored interactions.

### Critical Files for Implementation
- `Documents/Github/chart-fights/the_vision/vision.md` - [Primary source of all high-level intent and flavor]
- `Documents/Github/chart-fights/docs/design/game-mechanics-draft.md` - [Existing partial draft; formal spec supersedes/expands it]
- `Documents/Github/chart-fights/docs/design/GDD.md` - [High-level context and roadmap that must stay aligned with this detailed mechanics spec]
- `Documents/Github/chart-fights/docs/research/data-sources-initial.md` - [Informs concrete choices for instruments, normalization, feeds, and news data assumptions]
- `Documents/Github/chart-fights/docs/design/game-mechanics-spec.md` (or equivalent new file) - [Target location for this authoritative spec; will drive all subsequent cursor-tasks and code]

<subagent_meta>id=019f053a-1ea3-7810-b995-27068be9a7ce, type=plan, tool_calls=38, turns=1, duration_ms=276653</subagent_meta>