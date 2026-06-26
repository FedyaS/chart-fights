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