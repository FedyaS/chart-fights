# Chart-Fights Game Design Document (GDD)

**Version**: 0.1 (Autonomous research phase, 2026-06-26)
**Goal**: Create a fun, psychological 1v1 "chart fighting" PvP experience where players duel on accelerated historical market data with resource management, information asymmetry, sabotage abilities, and social trash-talk. "1v1 me in stocks bro".

**Core Fantasy**: Two traders, same historical price segment, same starting conditions. One wins by better reads, timing, mind games, and tactical use of limited "focus" and abilities. Matches are short (5 real minutes), intense, replayable, and highly social.

## 1. Vision & Inspiration
From the_vision/vision.md:
- MOBA mechanics + data feeds.
- Time scale: 1 real second ≈ 1 trading day.
- Broad market instruments (national indices + forex).
- Recharging resource bar for fast-forward + pause.
- Buy more data/news feeds.
- Sabotage opponent (delete stop loss, widen spreads, fake news).
- Expensive "big headline peek" ability.
- Normalize all series to 100 at match start (% returns only).
- Voice match chat for the real fun.
- Hackathon target: tradersfight.io

**Research Insights** (from completed subagents):
- No product does the full combination. Closest: ChartChamps (fair 1v1 historical PvP), FXR Battles (voice + historical duels), TraderFi (time compression + tournaments), Hedgd (duels + scrubber), Trade Bots (progression speed unlocks).
- Steal: Same historical segment for fairness, voice chat, time control via resources, gamification.
- Differentiate hard with sabotage/abilities, resource-gated acceleration, shared chart "fights".

## 2. High-Level Gameplay Loop
1. Matchmaking / lobby (private 1v1 or quickplay).
2. Match starts: Both players see identical normalized charts (prices start at 100).
3. Real-time clock advances ~1 simulated trading day per second.
4. Players:
   - Analyze charts.
   - Place/manage trades (long/short? stops, limits).
   - Spend "Focus" resource to fast-forward, pause, or buy abilities/feeds.
   - Use sabotage on opponent.
   - React to (real or faked) news.
5. 5 real minutes → match ends. Highest P&L wins.
6. Post-match: Replay, stats, rematch.

## 3. Time & Resource System (Core Mechanic)
- **Base Speed**: 1 real second = 1 simulated trading day.
- **Focus Resource Bar** (recharges over time, faster when paused):
  - Spend to fast-forward (e.g. 2x–10x speed multipliers, costs per bar or per real-second).
  - Spend to pause the shared clock (recharges faster).
  - Different "tiers" or upgrades unlock better efficiency.
- **Why it works**: Creates tension, risk/reward on when to speed up vs gather info. Prevents passive watching. MOBA-like resource management on top of trading skill.
- **Match Duration**: ~5 real minutes (configurable). Can represent months or years of simulated data depending on speed usage.

**Open Design Notes**: Exact costs/rates, whether Focus is shared or per-player, carry-over between matches.

## 4. Instruments & Data
- Initial set: 8–12 major instruments.
  - Indices: S&P 500 (^GSPC), Dow (^DJI), Nasdaq (^IXIC), FTSE, Nikkei, etc.
  - Forex: EUR/USD, GBP/USD, USD/JPY, etc.
- **Data Source Recommendation** (from research):
  - Primary: yfinance or Stooq for free bulk historical daily OHLC.
  - Fallback/upgrade: EODHD for broader coverage.
- **Implementation**:
  - One-time pre-fetch or on-demand range.
  - Store locally (CSV/Parquet/SQLite) normalized per match.
  - All series reset to 100.00 at start. Play with % changes only.
- **Non-trading days**: Skip or interpolate cleanly.
- **Future**: Intraday bars for higher fidelity (HistData, Stooq).

**Anti-Cheat**: Private local data + % normalization makes real-world "I know what happened on this date" much harder.

## 5. Trading Mechanics
- Starting capital: Fixed virtual (e.g. $100k).
- Order types (MVP): Market, Limit, Stop-Loss, Take-Profit.
- Positions: Long / Short allowed.
- Leverage / margin: Simple rules (configurable risk limits).
- P&L: Realized + unrealized at match end (or mark-to-market).
- Portfolio view + open orders list.
- Charts: Candlestick + volume (or suitable for indices), multiple timeframes (but time is accelerated globally).

**Future**: Options, more complex derivatives.

## 6. Information, Feeds & Abilities
- **Base Feeds**: Core price action + basic indicators for selected instruments.
- **Buyable / Unlockable**:
  - Additional indices or correlated assets.
  - Technical indicators, volume profiles.
  - Economic indicator feeds.
- **News System**:
  - Real historical headlines tied to dates (sourced with data).
  - "Big National Headline Peek" (expensive, limited uses): See the actual major news at current simulated time.
- **Sabotage Abilities** (direct interaction, MOBA flavor):
  - Delete / move opponent's stop-loss.
  - Temporarily widen opponent's spreads or slippage.
  - Inject "fake news" (misleading signal visible only to opponent or with delay).
  - Jam or delay opponent's data feed.
  - Expensive "force event" or rumor that moves the chart slightly.
- **Balance**: High cost in Focus or in-match currency, cooldowns, limited charges, risk of backfire or detection. Clear visual feedback.

**Economy**: Earn in-match currency or Focus from good trades to afford abilities/feeds.

## 7. Match Structure & Winning
- Duration-based (5 min real time) or first to target.
- Win condition: Higher final P&L % (or absolute).
- Ties / scoring: Secondary metrics (accuracy, risk-adjusted).
- Modes ideas: Pure 1v1, best-of-3, tournament brackets, custom rules lobbies.
- Replays: Full match recording with speed controls for review and learning (inspired by ChartChamps).

## 8. Social & Psychology Layer (The Fun)
- **Voice + Text Match Chat**: Persistent during the fight. Trash talk, bluffing, reactions to moves. (Huge from FXR Battles research: "Trading is more than charts, it’s mental warfare... Live voice chat to talk strategy or trash. Text chat for reactions, quick calls, and taunts." "Yes — live voice and text chat during active battles.")
- Psych examples (from voice sub): Bluff/deny during sabotage ("Nice SLs... or were they?"); taunt TB control ("I'm holding pause — you're wasting IP"); react to peeks/fills/equity swings. Poker-like tells + pressure. Pair with visual indicators (speaking during sabo toasts).
- Emotes or quick taunts.
- Post-match: Share replay links, salt, rematch button.
- Integration: VoicePanel next to text chat (task-007/008); enhance text with emoji reactions to events; opt-in controls, PTT/mute. WebRTC P2P + WS signaling (extend task-005 rooms) or fallback. <150ms target. Graceful degrade + NAT testing. Benefits: engagement, psych edge, fun factor. Risks: toxicity (mitigate with mute/volume/PTT). See RESEARCH_STATUS voice sub, arch §5, task-008.
- Global or friend leaderboards, Elo or hidden MMR.
- Spectators / watch parties (future).

## 9. UI/UX Flows (High Level)
- Lobby / Matchmaking screen.
- Match screen:
  - Main multi-chart area (shared time scrubber or synced).
  - Personal portfolio + orders panel.
  - Focus/resource bar + ability hotbar.
  - Opponent status (high-level, some fog?).
  - Chat (voice + text).
  - News / events feed.
- Controls: Intuitive order placement on chart or panel.
- Accessibility: Speed indicators, clear resource costs.

**Key Feeling**: Fast, tense, personal duel. Charts feel alive and contested.

**Research Insights (15m review 2026)**: Integrate LW Charts for replay (update streaming, sync, overlays from sub); voice as psych differentiator (FXR mental warfare, trash talk validated); sabotage/TB for MOBA contest on historical. See STATUS subs, arch for details. Polish UI for contested feel (TB controls, IP actions, synced charts).

## 10. Anti-Cheat, Fairness & Technical Notes
- All players get identical historical slice for a match.
- Data pre-loaded or served from trusted server.
- Server-side simulation of state (P&L, orders) authoritative.
- Rate limit abilities.
- Optional: Mystery start dates or slight randomization of exact news timing.

**Data Pipeline** (research recs):
- Fetch bulk once.
- Normalize per match.
- Serve efficiently (no live external calls during match).

## 11. Tech Considerations (High-Level, No Code)
- Frontend: Web (TradingView lightweight or custom canvas for charts?) or desktop (Electron?).
- Backend: Game state server (WebSocket for real-time sync of clock, orders, abilities).
- Data: Local cache + server-hosted historical sets.
- Real-time: Synchronized simulation clock.
- Voice: WebRTC or third-party (Discord integration?).
- Persistence: User accounts, match history, replays (JSON or video?).
- Scalability: Start simple (1v1 direct), later matchmaking + tournaments.

**MVP Scope**: Single 1v1 match type, small instrument set, basic orders + 3-4 abilities, yfinance/Stooq data, text chat first (voice stretch).

## 12. Open Questions & Risks (to be refined)
- Exact Focus costs and recharge curves?
- Order types and leverage for MVP?
- How visible is sabotage to the victim?
- Voice chat implementation priority vs text?
- Monetization (cosmetics, extra abilities, premium data)?
- Mobile support?
- Real money elements? (Strongly recommend virtual only initially.)
- Legal: Historical data usage, gambling regs if prizes.

**Risks**:
- Data freshness / gaps.
- Cheating via external knowledge (mitigated by normalization + private data).
- Balance of abilities vs pure trading skill.
- Keeping matches snappy and fair.

## 13. Phased Roadmap (High Level)
See docs/design/roadmap-and-open-questions.md for the detailed phased implementation roadmap (MVP-first phases 0-5).
See docs/cursor-tasks/TASK_MANIFEST.md for the canonical inventory of exactly 8 tasks (no inline duplication of the list here).

All high-level vision, mechanics, and handoff details live in the referenced design package.

Verification note (2026-06-26 skeptic round): GDD phased list excised; full plan verif steps executed; observations hold per scratch/verif_*.txt.

---

**References for Implementation**:
- Detailed mechanics: `docs/design/game-mechanics-spec.md`
- Technical architecture (recommended stack, realtime sync, data pipeline, voice): `docs/design/architecture-overview.md`
- Phased roadmap + open questions: `docs/design/roadmap-and-open-questions.md`
- Cursor-ready tasks: see docs/cursor-tasks/TASK_MANIFEST.md (canonical 8-task inventory).
- Full handoff package: `docs/design/IMPLEMENTATION_HANDOFF.md`

**Next Steps for this run (autonomous)**: Deepen GDD alignment (done). Create frontend streaming and voice Cursor tasks from architecture. Polish handoff artifacts. Use background subagents and scheduler to continue without idling. All outputs in docs/.

This GDD is now the high-level entry point; see referenced specs for depth.

---

## 14. Detailed UI/UX Flow (Synthesized from LW Subs, task-007, Arch §5, Data/Netcode Subs + STATUS Cycles)

**Pre-Match Lobby / Matchmaking Flow** (high-level from GDD §2 + task-007 lobby stub + arch match lifecycle):
1. Player enters lobby (quickplay or private 1v1 code/room).
2. Arena selection: Server picks (or player prefs) pre-loaded normalized slice (P[0]=100 for all instruments, generic labels like "Broad Equities"). Hash verify on client load (anti-cheat tie to task-001/006).
3. Voice opt-in + mic permission prompt (graceful text fallback per task-008).
4. Countdown (shared state sync via WS from task-005). Both preload via LW `series.setData(initialNormData)`.

**Match Start & Core Screen Layout**:
- Main area: Multi-instrument synced candlestick charts (TradingView LW Charts). Master/slave `timeScale.subscribeVisibleLogicalRangeChange` for shared T (logical range around current sim day index; no real dates during play).
- Top/Left: Real-time clock ("Sim Day NNN" + R speed indicator), equity % for self + opponent (high-level or fog per design).
- Resource HUD (persistent, animated):
  - Tempo Bar (TB): Progress fill (color-coded by active influence: self/opponent/ neutral). Buttons/hotkeys: Pause (R=0), FF x2 / x3 / x5. Costs shown (e.g. "2.0/s"). Contested visuals: "Market Speed: 3.0x (contested)" + subtle who-is-paying if not anon.
  - Intel Points (IP): Numeric + regen sparkles. Action bar: Buy feeds (unlocks), Peek (60 IP ultimate), Sabotage buttons (with costs/cooldowns/tooltips).
- Center-right: Orders/Positions panel (market/limit/stop + attach SL/TP; size inputs; "place on chart" crosshair capture). Live list with modify/cancel.
- Bottom: Notifications feed (timestamped toasts/banners: fills, "Your SLs deleted (sabotage)", fake news flags, news peeks).
- Side panels: TextChat (persistent, emoji reactions to events) + VoicePanel (next to it per task-007/008 integration; mic/PTT/mute/volume per-player + WebAudio VAD speaking pulse indicator).
- Bottom controls: Concede / pause own view (if allowed) / speed scrubber (client-only secondary analysis?).

**In-Match Interaction Flow (contested, fast-paced)**:
- Chart stream: WS deltas (task-005) → `series.update(bar)` for latest (never setData mid-stream per LW subs 019f0577/019f05bc). ReplayController (custom hook from LW sub): useEffect + R-scaled setInterval (baseMs / R); on tick `master.timeScale().setVisibleLogicalRange({from: T-w, to: T+o})` or direct from server T. On R=0 (pause): clear/freeze. FF: scale or direct set range. Overlays rebuilt on OrderDelta/EquityDelta/EventDelta: `createSeriesMarkers` / `setMarkers` for entries/exits (full replace); `createPriceLine` for SL/TP (applyOptions/remove); parallel equity series (Line/Area on same or secondary priceScale).
- Order actions: UI input → WS action send (optimistic local marker/priceLine + tentative P&L). Server authoritative exec at T advance (reconcile on Equity/OrderDelta). Click chart for price snap.
- Tempo influence: Button hold/press → WS "start_TB_influence(level)". Server resolves contention (Pause overrides to R=0; max(FF) + all payers consume per mech-spec). Client: visual drain on TB, R label update, freeze/scale controller.
- IP spends: Button → cost check (client optimistic) → WS. On success: feeds unlock (add chart series), peek reveals headline in notifs/news; sabo applies server-side (e.g. delete SLs from opponent state) → EventDelta broadcast (victim-specific notif + subtle overlay effect like dim on affected priceLines?).
- Voice sync: PTT or open mic → low-lat P2P (WebRTC via task-005 WS signaling for offer/answer/ICE). Indicators pulse on VAD. Text reactions (emoji) broadcast on WS + tied to game events (e.g. 💥 on sabo cast).
- Reactivity: Fills/swing/sabo → notif toast + voice taunt opportunity + equity curve update. Shared clock creates urgency (can't passively watch; MOBA-like resource tension).

**Post-Match Flow**:
- End on real 5min wall time. Final equity comparison. Reveal (optional): full opponent feeds bought, exact sabo casts, arena real labels/dates.
- Replay viewer: Full log replay or re-sim (from action log + arena ID). Scrub (direct logical range), speed controls, full visibility overlays (both players' markers). Stats: IP earned/spent, sabo usage, voice event count?, accuracy.
- Rematch / share replay link / leaderboard update.

**Key UX Principles (LW + arch + GDD)**: "Fast, tense, personal duel" feel. Contested visuals everywhere (TB influence, shared T sync, sabotage feedback). No heavy client prediction for shared state (server T/R truth + conservative lerp/smooth per netcode sub; optimistic own only). Strict React cleanup (chart.remove() + unsubs). Responsive desktop-primary. Accessibility: ARIA on resources, high-contrast toasts. Pitfalls avoided: update() only latest bars; master/slave loop guards; no extrapolation on ranges.

**References**: task-007-frontend-streaming.md (ACs, LW panels, WS deltas); arch §5 (LW ReplayController + Mermaid, deltas: Bar/Resource/Order/Equity/Event, VoicePanel integration); LW subs (019f0577, 019f05bc-ed2b, 019f05db... official realtime + time-scale + markers/price-line + react/advanced excerpts); task-005 (WS); STATUS cycles (LW deep dives appended post sub; 15m reviews; 5m/10m self-checks integrating controller patterns); game-mechanics-spec §1-2 (T/R/TB exact); GDD §9 high-level.

---

## 15. Psych & Voice Warfare Section with Specific Examples (Synthesized from Voice Sub, FXR Research, Mech spec §9, LW/Arch feedback + STATUS Cycles)

**Core Principle**: Voice + text is not just comms — it is the "all-chat MOBA salt" and primary psych differentiator (validated by FXR Battles: "Trading is more than charts, it’s mental warfare... Live voice chat to talk strategy or trash. Text chat for reactions, quick calls, and taunts." "Yes — live voice and text chat during active battles."). Combined with sabotage, TB contention, info asymmetry (peeks/feeds), and visible resource pressure, it creates poker-like tells, bluffing, tilt, and reactive mind games on top of pure chart skill. Low-lat (<150ms target) enables real-time reactions. Visual speaking indicators (WebAudio VAD) + event-tied toasts amplify immersion and psych pressure. Always notify victim of sabo for counterplay + bluff opportunities. Text polish (emoji reactions, timestamps) syncs with voice moments.

**Specific Gameplay-Tied Examples** (drawn directly from voice sub research in STATUS + FXR validation + task-008 recs; pair with sabo/TB/peeks per GDD §8 and mech):
- **On Sabotage Cast (Delete SLs, 30 IP / 60s cd)**: Server applies, victim toast: "Your stop losses were deleted (sabotage) at Sim Day XXX." Caster voice (while casting or immediate): "Nice SLs... or were they?" + VAD pulse on VoicePanel. Victim can counter-bluff immediately: "Didn't need them anyway — watch this long." Visual: priceLines for SLs vanish on victim chart; speaking indicator next to sabo notif. Mind game: caster might fake a cast sound or taunt without spending to tilt.
- **During TB Contention / Pause Hold**: When holding Pause (R forced=0, own TB recharges +4/s): "I'm holding pause — you're wasting IP" (or "Scared of the next bar?"). Global UI: "Market Speed: PAUSED (contested)" + subtle influence indicator. Opponent voice reply: "Keep wasting yours, I'll FF when you crack." Psych: denies tempo during key setups; voice pressure makes opponent over-commit or tilt into bad FF spend.
- **Expensive Peek (60 IP ult)**: After using on current T: "I just peeked the headline — gl hf on that Fed move." Or bluff without peeking. Victim hears and may overreact or second-guess their read. Text reaction: 👀 or 💰 emoji on the peek event in shared chat.
- **Fake News Inject (40 IP / 90s cd) or Equity Swings**: "That wick look familiar? Or did I just feed you noise?" / "Oof, down 8% already? This is only the warm-up." On fill or big bar: "Nice entry... right into my TP." Ties to voice during volatile ranges sped up by FF.
- **General Bluff / Denial / Tilt Induction**: "Your data feed jammed or just bad reads?" (after jam sabo). "I'm diversified — you still all-in on one index?" React to opponent's voice tells (e.g. hesitation on pause decision). "GG, but that pause was expensive." Post-swing: trash + "rematch?"
- **Voice + Visual Synergy**: Speaking indicator pulses during sabo toasts or TB holds for "I did that" pressure. Quick text taunts (e.g. "😏") on event feed. PTT for precise timing (cast sabo then immediately taunt). Per-player volume/mute for toxicity control (opt-in, graceful degrade to text).

**Implementation Ties & UX** (task-008 + arch §5 + voice sub 019f058c etc.): VoicePanel sidebar next to TextChat (Zustand + WS events for join + reactions). Signaling reuses task-005 match rooms (offer/answer/ICE). Native WebRTC P2P primary (STUN + Coturn TURN ~20-30% cases); <150ms Opus; indicators via Analyser/hark or built-in. Fallback seamless to provider (Twilio/Agora) or text + notify on mic deny/NAT fail. Graceful: "Voice unavailable (text only)". Pair explicitly with game events (sabo/TB/peeks) for psych power. Risks mitigated: PTT/mute/volume, no recording in MVP (opt-in later).

**Research Backing**: FXR "mental warfare" + trash validated as huge fun/retention factor. MOBA BM (all-chat) + poker tells (voice pressure on resource decisions). LW overlays + notifs make sabo effects visible for voice reactions. Benefits: engagement, asymmetric info edge via bluff, pure fun ("1v1 me in stocks bro"). See voice sub excerpts (STATUS Process Log post 019f058c/019f05a9 etc.), task-008, GDD §8, mech §9.

---

## 16. Balance & Tuning Guidelines (from MOBA/FXR + Mech-spec, Data/Netcode Subs + STATUS Research)

**Core Philosophy** (MOBA flavor on historical replay + FXR social validation): Make trading skill primary, but layer contested resources (TB/IP), direct interaction (sabo), info asymmetry (feeds/peeks), and voice psych as skill amplifiers and "fight" differentiators. Symmetric kits for both players. Short fixed real-time (5 min) + variable sim depth (150-1500+ days) keeps snappy. Normalization (P[0]=100 + generic) + server-auth (task-005/001) ensures fairness. Good trades fund psych warfare (IP from +10% realized P&L). Comebacks enabled by late sabo/tempo swings + volatility in normalized data.

**TB (Tempo) Tuning (Mech-spec §2 exact starting numbers; MOBA "contested objective" parallel)**:
- Like fighting over dragon/baron or map control: Shared R creates direct "who controls the pace" fights.
- Recharge: +1.0 / real-s base (full bar ~100s). Pause bonus +4.0/s (when holding, R≤0) — strong denial + personal regen incentive.
- Consumption (per real-s active): Pause=0 (pure denial), FFx2 (R=2)=2.0/s, FFx3=5.0/s, FFx5 (R=5)=12.0/s (full bar in ~8s — high-risk burst only).
- Contention: Pause always forces R=0 override. Multiple FF: R=max(active), all payers consume. Default R=1.0 no controls.
- Guidelines: Tune so pause is strategic denial not stalling (test 5min real feel; avoid infinite hold via costs or soft timers). FF high multipliers for rush boring ranges but punish over-use (opportunity cost for later IP/sabo). Visual "who influencing" or anon for psych bluff. Playtest: measure % time paused vs FF, comeback frequency. Netcode sub: server truth for R resolution + conservative client follow.
- FXR parallel: Time compression is core; add resource gate + contention for interaction (vs pure solo scrub in analogs).

**IP (Intel) Economy (MOBA "gold" from performance + vision/sabo spend)**:
- Sources: Passive +0.5 / real-s; +10% of realized P&L on profitable closes (rewards good trading to "buy power").
- Uses: Premium feeds (~20-40 IP one-time, vision asymmetry); Peek ult 60 IP (limited uses/cooldown); Sabo 25-40 IP + cooldowns (45-90s real after cast).
- Sabo specifics (mech §7): Delete SLs (30 IP/60s), Widen Spreads (25 IP/45s cd, 15s effect, 0.4-0.8% adverse slip), Fake News (40 IP/90s). High cost relative to regen (~50-80s passive for one cast) forces trade-off.
- Guidelines: IP soft cap ~200; no negative. Earnings from unrealized? Playtest. Sabo always notify victim (timestamped) for counter + psych (no stealth). Cooldowns + costs prevent spam; risk of backfire (visible tilt opponent aggressive). Balance sabo power vs pure execution: high cost + detection + victim counterplay (e.g. wider stops after detected). Feeds give edge but meta may favor raw price + timing.
- MOBA: IP = farm for items/abilities. Good "CS" (trades) funds "ganks" (sabo). Snowball via IP lead but comeback via tempo/voice tilt.
- FXR: Voice amplifies without extra resource cost (free psych layer on top of execution).

**General Tuning Principles (from research/specs)**:
- Symmetric + high visibility feedback for fairness and mind games.
- Risk/reward: Expensive actions (FFx5, peek, high sabo) have big impact but drain or cooldown.
- Comeback & swing: Short duration + volatile % moves + late-game sabo allow huge equity swings.
- Test process (STATUS netcode/mech/data cycles): Deterministic sim harness (Decimal for P&L/TB; verify_replay(arena+log)); lag-inject for TB contention races; playtest multiple arenas (trending/crisis/range from data sub curation); measure winrate by sabo usage, IP efficiency, voice activity correlation (future), equity curves.
- Avoid: Over-sabo (make trading irrelevant); stall (tune pause regen/override); frustration (clear contested UI, graceful reconnect per netcode).
- MOBA/FXR steal: Contested resources create "fights" on shared objective (TB clock like objective); voice as mental warfare multiplier (FXR "rush without risk"); fairness via same historical segment (ChartChamps/FXR).
- Future: Burst lump-sum actions? Recurring IP costs? "Purge" counters? Tune post MVP via metrics.

**Numbers Baseline (exact from game-mechanics-spec; tunable via playtest)**: See §2 TB/IP, §7 sabo costs/cds/durs, §6 peek. Match 300 real-s fixed. Starting capital 100 units. Small base spread 0.05-0.1%.

---

## 17. Open Items / Polish (Consolidated from Roadmap, Mech §12, HANDOFF, STATUS Cycles & Tasks 001-008 + Prior Subs)

**Tier 1 (Critical for Phases 0-2 / tasks 001/002/005/006/003; resolve before full playable)**:
- Clock/TB contention edges: Fractional T? Exact simultaneous Pause+FF race resolution (server receive time + max)? Client prediction (netcode sub rec: pure follow + lerp for shared T/R/TB; optimistic only for own orders/TB drain). Reconnect mid-contention (full snapshot + missed deltas + active influencers).
- Determinism harness & verification (anti-cheat/netcode sub): Synctest (multi-engine same actions + checksum), lag injection on TB fights (Pause/FF races), stable Decimal state hashes (equity/P&L/TB quantize), verify_replay(arena_id + sorted action log). Integrate task-001/005. See anti-cheat-determinism-design-notes.md + STATUS det subs.
- IP economy details: Unrealized P&L grants? Negative allowed? Burst actions? Exact P&L-to-IP conversion curve.
- Sabotage: Granularity (specific instruments?); counters ("purge" ability?); victim visibility depth; probabilistic detection? Backfire mechanics.
- Arena/data: Selection (random balanced vs curated regimes vs MMR); exact prep (OHLC full vs returns + on-demand; non-trading interp); mystery offsets + content_hash (data sub 006 + task-001).
- Order fidelity: Close-only vs high/low triggers within bar? Limit fill priority on simultaneous?

**Tier 2 (Phase 3-4, tasks 007/008/004)**:
- Voice: Self-hosted Coturn vs provider priority (Twilio/Agora); NAT/cross-net test plan; post-match voice log opt-in (deferred); exact audio constraints + VAD lib.
- UI polish (LW sub + task-007): Full sabo visual effects (dim/glitch on victim overlays); contested TB "who influencing" (or always anon for psych); equity separate pane; current-T vertical line plugin; lobby full vs stub; mobile/responsive.
- Replays: Log format (action + R-ts + arena); full vs partial visibility post-match; scrubber fidelity with R scaling.
- Client state: How much fog on opponent (equity delta only vs full?); personal scrub secondary view cost?

**Polish & UX Items (from arch §5, GDD, HANDOFF, STATUS verifs)**:
- Contested feedback everywhere: Strong visuals/audibles for TB influence, R changes, sabo notifs, IP spends (tooltips + animations). "Fast tense duel" feel.
- LW integration polish: Master/slave guards explicit; React strict cleanup; no setData live (only init); handle WS lag gracefully.
- Psych enhancements: Timed voice prompts or emotes on key events; emoji reactions tied to fills/sabo/TB; speaking indicators pulse on sabo toasts.
- Anti-toxicity: Easy mute/PTT/volume; report; volume defaults reasonable.
- Performance: Broadcast ~10-20Hz or event-driven; throttle renders; virtual lists.
- Accessibility & clarity: Clear resource cost previews; speed indicators; generic labels consistent.
- Testing: Full determinism cross-client + lag sim; NAT matrix for voice; multiple arena playtests (data sub regimes).

**References to Prior STATUS Cycles & Tasks**:
- All synthesized from: Mech subs (tasks 002-time-and-tempo, 003-resources-and-sabotage, 004-orders-and-core-loop + game-mechanics-spec authoritative rules); Data sub (task-006 + research/ Parquet/arenas/yf/Stooq); Netcode/realtime (task-005 + arch + anti-cheat-notes GGPO/Photon patterns); Voice sub (task-008 + 019f058c WebRTC/psych/FXR + task-007 integration); LW subs (task-007 + 019f0577/019f05bc/019f05db controller, official tutorials, deltas, pitfalls); Own work (RESEARCH_STATUS.md Process Log: 5m/10m/15m self-checks, sub polls/integrations e.g. post 019f05xx voice/LW/det, verif "All hold 8/8 + N refs + 0 legacy", handoff polish sub 019f05f4, multiple cycles appending excerpts + deepens to arch/GDD/tasks).
- See: docs/cursor-tasks/TASK_MANIFEST.md (canonical 8); roadmap-and-open-questions.md (phases + OQs); HANDOFF_READINESS_POLISH_RECS.md + IMPLEMENTATION_HANDOFF.md (verif summaries); game-mechanics-spec §12 opens; arch §7 risks; STATUS cycles for full transcripts/FXR quotes/excerpts + sub IDs.
- MVP defaults (per roadmap): In-mem single-proc; wall-time align; text-first+WebRTC; bar-at-T + units 100; exact TB/IP/sabo from spec; server truth.

**Next for Polish**: Playtest-driven tuning of all numbers; deepen specific UI mocks for contested states; full voice psych UX tests; update GDD/mech after first impl cycle. All research/design artifacts remain in docs/.

This completes the deepened design package. Ready for Cursor agents per TASK_MANIFEST + full handoff.