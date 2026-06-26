# Cursor Agent Task: Data Pipeline - Pre-fetch, Arena Curation, Storage & Normalization (MVP)

**Context**: Chart-Fights. References:
- docs/design/architecture-overview.md (data pipeline section)
- docs/research/data-sources-initial.md + historical_data_sources_research.md
- docs/design/game-mechanics-spec.md (normalization, private arenas, anti-cheat)

**Goal**: Build the one-time fetch + storage + per-match loading pipeline for historical daily bars. Primary sources yfinance or Stooq. Output normalized arenas ready for simulation engine.

## Requirements
- One-time bulk fetch (decades preferred): indices (^GSPC, ^DJI, ^IXIC, others) + major FX (EURUSD=X, etc.) using yfinance (easiest) or Stooq bulk.
- Clean & store: Handle non-trading days (skip or interpolate), consistent OHLCV format. Store as Parquet (preferred for efficiency) or SQLite/CSV + metadata (source, date range, regime notes).
- Arena curation: Pre-select / script to generate "arena" slices (contiguous periods with variety: trending, volatile, range-bound, crisis). Include metadata for selection (e.g., by regime).
- Per-match loader: Given arena ID or slice, load into memory, normalize (P[0]=100 for every instrument using % returns), apply generic labels during play. No external API calls mid-match.
- CLI/scripts: fetch_arenas.py, list_arenas, load_arena(slice).
- Anti-cheat: Private local storage; normalization + generic labels enforced.

**Sources priority** (from research): yfinance for ease + depth; Stooq for free bulk no-signup. Avoid rate-limited free tiers for initial bulk.

## Acceptance Criteria
1. Fetch script(s) for yfinance + Stooq paths that download multi-year data for core instruments.
2. Storage in Parquet with metadata.
3. Loader that returns normalized bars (P[0]=100) for a slice.
4. Simple arena registry / selection (at least 4-6 varied slices).
5. Tests: Normalization math, determinism (same slice always same output), data integrity (no NaNs in critical fields).
6. Documentation: How to add new instrument or regenerate arenas.

## Cursor Agent Prompt
"Build the data pipeline for historical replay arenas per docs/cursor-tasks/task-006-data-pipeline.md + architecture-overview.md data section + data-sources research.

Use yfinance (primary) or Stooq. One-time bulk fetch of daily OHLC for specified indices/FX. Store as Parquet. Provide loader that normalizes any slice to P[0]=100 (percentage returns only). Include CLI tools and at least a few pre-curated arenas.

Follow the anti-cheat normalization and private arena requirements exactly. Make it efficient and easy to extend. Add tests for the normalization step. No mid-match external calls."

## Notes
- Feeds into task-005 simulation (pre-loaded in-memory).
- Supports future intraday if needed.
- Keep fetch scripts separate from runtime.

**Priority**: Foundational for all replay.
**Size**: Small-medium.

## Data Research Notes (from historical_data_sources_research.md + 2026 web + arenas sub)
- Primary: yfinance (decades ^GSPC/^DJI/^IXIC + FX pairs, pandas one-call, period='max' or date ranges) or Stooq (free bulk ZIPs daily/5min, no signup, world coverage). EODHD for paid global. 2026: yfinance still viable programmatic (Yahoo paid downloads); Stooq active.
- Pipeline: Fetch -> clean/align (skip or interp non-trading) -> store Parquet (preferred: columnar, compressed snappy/zstd, pyarrow engine for speed/schema/metadata; tiny for ~300 bars). Use pyarrow for read/write. Partition larger raw by year/instr.
- Per-match: Load slice (server-only) -> normalize P[0]=100 (% returns: norm[t] = 100 * prod(1+ret)) + generic labels. Compute content_hash (SHA256 of normalized sorted). Enforce private (no client raw, no mid-match external).
- Non-trading: Use pandas_market_calendars (NYSE.valid_days) + reindex + dropna/bfill for strict skip or interp. Align multi-instr dates (inner join).
- Arena curation/registry: Pre-generate 10-20 varied (bull/bear/sideways/vol/crisis). Metadata: id, source, date_range, regime_tags, vol_stats, content_hash, instruments. Selection: balanced random or prefs. Registry JSON/DB.
- Regime labeling (example): rolling mean/vol heuristics or clustering on returns for bull/bear/sideways buckets.
- Loader: load_arena(arena_id) returns {"bars": norm_dict (Decimal or float), "labels": generic, "hash": str, "metadata": {...}}. CLI: fetch_arenas, list_arenas, load_arena.
- Hash + verify: Store hash; use in determinism tests + verify_replay(arena_id, action_log) for re-sim match (ties task-001).
- Tests: norm math stable + hash consistent; roundtrip; non-trading alignment; no NaNs.
- Ext: Intraday via Stooq/HistData aggregates. Parquet benefits: fast sequential, efficient deltas for WS.
- Server: Preload full slice in room (tiny); serve initial + deltas (new bar at T). No client access to raw.

**From deep arenas research sub (integrate to 006/001)**: yfinance/Stooq fetch sketches (yf.download multi, Stooq ZIP extract + pd.read); pyarrow to_parquet/read_parquet; normalize+hash pseudocode; regime label; pandas_market_calendars valid_days; metadata schema; server enforce + WS deltas; anti-cheat via private+norm+hash. Repro: pin versions, log params, sorted for hash. Pitfalls: date align, float vs Decimal (use Decimal in sim), timestamp res.

## Integration with other tasks
- Feeds task-005 (preloaded normalized, hash for verify).
- Supports task-001 (norm fn, private loader, hash for re-sim).
- See anti-cheat-determinism-design-notes.md for full verify_replay pseudocode.
- Refs: research/historical_data_sources_research.md, architecture data section, det sub (norm hash in verify). No live APIs mid-match.

## Deep Arenas / Data Pipeline Subagent Transcript (15m Review Integration)
High-value excerpts from completed explore sub (full transcript in sub output + prior STATUS; actionable for Cursor agent handoff):

**Completed Research Summary (all subs + own work reviewed)**:
- Data sources: yfinance/Stooq primary free (bulk decades, Parquet store); EODHD/FRED supplements. Strategy: one-time fetch + private local + norm to 100 + hash. (From initial research + arenas sub.)
- Similar products: ChartChamps (historical PvP fairness, Elo/replays, acquired 2026), FXR Battles (voice "mental warfare"/trash talk validated, time trial/profit targets), Hedgd (duels/scrub), others. Differentiation: MOBA TB/IP + sabotage + private normalized arenas + contested clock.
- Mechanics: Full spec (1s real=1 day shared T/R ~300 bars, TB +1/s base/+4 pause, consume 0/2/5/12, IP +0.5/s +10% PnL, sabotage always-notify, orders M/L/S+SL/TP, win equity, anti-cheat norm P[0]=100/generic labels).
- Tech/Arch: FastAPI/Starlette WS authoritative (deltas 10-20Hz), LW Charts (setData init + series.update deltas, logicalRange master/slave for FF/pause/scrub, markers/priceLines/equity, React refs+cleanup+ReplayController R-scaled), WebRTC P2P+WS sig (Coturn primary, <150ms Opus, psych UX FXR taunts tied to sabo/TB), det (GGPO/Photon/Bevy harnesses: synctest/rollback/checksums/verify_replay, Decimal for equity/TB, stable SHA, lag injection for TB contention, snapshots).
- Subs integrated: LW realtime/replay (official patterns, pitfalls like setData jumps, master/slave); voice (signaling, Coturn/Twilio, VAD, psych examples); det harness (pseudocode SimEngine/verify/TB resolver); data arenas (this full: fetch/clean, Parquet best practices, calendars, norm/hash, regime, loader, anti-cheat ties, pitfalls, 001/005 integration).

**Data Sub Key Excerpts & Recs (condensed for task-006)**:
- Fetch: yfinance (pandas one-call, decades) or Stooq (bulk ZIPs). Cleaning: pandas, gaps/NaNs, volume 0 for indices.
- Calendars: pandas_market_calendars (valid_days, reindex, skip non-trading for fidelity; align multi-instr inner join).
- Parquet: columnar (snappy/zstd, pyarrow); partition by year/instr/arena; metadata sidecar (id, range, regime, hash); fast sequential for replay/WS deltas. Sketch: df.to_parquet(..., engine='pyarrow'); pd.read_parquet + filters.
- Norm + Hash: P[0]=100 %returns (norm[t]=100 * prod(1+ret)); generic labels ("Broad Equities"); content_hash=SHA256(sorted normalized). Private server-only.
- Regime/Arena: Pre-gen 10-20 varied (bull/bear/sideways/vol/crisis via rolling/vol or clustering); metadata for selection (balanced random).
- Loader/Enforce: load_arena(arena_id) -> {bars, labels:generic, hash, metadata}; server preload tiny slice; no mid external.
- Anti-cheat ties: private + norm + generic + mystery/random offsets neutralize knowledge; hash for verify_replay (ties 001).
- Determinism: arena hash + action log (real_ts+sim_t) -> re-sim identical state/PnL/equity (Decimal quantize, stable sorted SHA).
- Best practices: one-time private fetch+version; columnar Parquet; calendar skip; server-authoritative; Decimal+stable hashes; full log for audit; tests (norm, hash, no-NaN, roundtrip, re-sim).
- Pitfalls: float drift (use Decimal in sim); date/symbol align (inconsistent global); hash instability (sort, no platform hash, finite); gaps (verify don't manufacture); over-partition; client leakage (enforce).
- Integration: Feeds 005 (preload+verify+log); supports 001 (norm+private+hash); see anti-notes for pseudocode.

**Append recs from sub**: Paste this into task-006 Data Notes; update handoff "Data & Research" + "Next actions" (parallel 006+002); arch §3 deepen Parquet + regime + pitfalls; roadmap data OQ with resolved. Prioritize Decimal/hash in det paths. Full sub transcript dense + web (Parquet finance compression/speed, calendars, regime HMM/kmeans).

**Priority for Cursor**: Follow exactly for MVP (yfinance/Stooq -> Parquet -> norm P[0]=100 + generic + hash + loader). Tests for det + anti-cheat. No invention.