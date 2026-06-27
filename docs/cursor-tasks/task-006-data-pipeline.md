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

## Deep Research Resolutions (sibling worker, 2026-06-26)

This section resolves the remaining OPEN data/arena questions from `roadmap-and-open-questions.md` (Tier 1 #3 "Data/arena format + pipeline", plus Medium items) with concrete, MVP-scoped, spec-faithful decisions. It extends (does not replace) the notes above. All numbers stay consistent with the spec: per-match normalization to **P[0]=100.00** using % returns only, **generic labels** during play, **private server-only** arenas, **no mid-match external calls**, and a **content_hash** for determinism/`verify_replay`.

### OQ-D1 — Storage format: full OHLC arrays vs returns-only + on-demand indicators
**Decision: persist RAW full OHLC(V) at rest; normalize at load time; never store the normalized series.**
- Rationale: arenas are tiny (~300 daily bars × a handful of instruments), so storage cost is irrelevant and there is no reason to discard information. Storing raw + normalizing on `load_arena()` keeps a single source of truth, lets us change the normalization rule later without re-fetching, and means the secret real prices/dates never leak into a normalized artifact a client could diff against history.
- Fields to persist per bar: `date` (trading day, `datetime64[ns]`/ISO date), `open`, `high`, `low`, `close`, `volume` (nullable — see OQ-D3). Do **not** store `adj_close` separately for indices/FX (≈ `close`; no corporate actions). Keep a stable column order.
- Normalization is **price-only** and applied identically to O/H/L/C so intrabar geometry (used by task-004 high/low fill triggers) is preserved:
  ```python
  # norm_factor anchors the FIRST close to 100.00; same factor applied to O/H/L/C
  # so that high/low/open relationships survive (needed for stop/limit fills).
  from decimal import Decimal, getcontext
  getcontext().prec = 28
  def normalize_instrument(bars):  # bars: list of raw OHLC dicts, chronological
      c0 = Decimal(str(bars[0]["close"]))
      f  = Decimal("100") / c0
      out = []
      for b in bars:
          out.append({
              "open":  (Decimal(str(b["open"]))  * f).quantize(Decimal("0.0001")),
              "high":  (Decimal(str(b["high"]))  * f).quantize(Decimal("0.0001")),
              "low":   (Decimal(str(b["low"]))   * f).quantize(Decimal("0.0001")),
              "close": (Decimal(str(b["close"])) * f).quantize(Decimal("0.0001")),
          })
      return out  # out[0]["close"] == 100.0000
  ```
  Note: anchoring on first **close** = 100 means the first bar's open/high/low sit slightly off 100 — that is correct and desirable (it preserves the true first-bar shape). The earlier `prod(1+ret)` formulation is equivalent for the close series; the factor form above generalizes cleanly to all four price fields. Use **Decimal** at the sim boundary; floats are acceptable inside the fetch/clean stage but everything that feeds equity/hash must be Decimal-quantized (ties task-001).

**Parquet specifics (grounded in 2026 best practice):**
- Engine `pyarrow`, `version="2.6"`, `compression="zstd"`, `compression_level=5` (3–6 band: ~30–50% smaller than snappy with comparable decompression). `write_statistics=True` is mandatory (without min/max stats, filtered reads degrade to full scans).
- Row-group size in the 100k–500k row range is the documented sweet spot — irrelevant for a single ~300-row arena (one row group), but matters if you store the **raw multi-decade bulk** as one file per instrument.
- Partition the **raw bulk** by `instrument` (and optionally `year`) — partition keys should be low-cardinality (<~1000 distinct). Do **not** over-partition (avoid thousands of tiny files). Curated **arena** slices are tiny: store one Parquet file per arena (e.g. `arenas/<arena_id>.parquet`) plus a sidecar/registry entry; no partitioning needed.
- Sources: ZSTD level 3–6 + Parquet v2 + per-symbol/date partitioning + statistics are the consensus 2026 recommendations — https://worlddata.cloud/cloud-cost-and-performance-trade-offs-for-storing-tick-level , https://medium.com/@Modexa/10-pandas-io-optimizations-parquet-arrow-zstd-that-matter-bde8ab4d6da3 , https://sudonull.com/parquet-in-python-reading-writing-and-optimization . Lossless round-trip fidelity of Parquet+ZSTD on daily OHLCV is empirically exact (RMSE 0.0) — https://github.com/Zer0pa/ZPE-FT .

### OQ-D2 — Arena selection algorithm (random balanced vs MMR vs manual) + regime labeling
**Decision (MVP): manual/scripted curation of 12–16 arenas tagged by regime, then balanced-random selection at match time. Defer skill/MMR-weighting to post-MVP.**
- Why: MMR-weighting needs a rating system that does not exist yet, and "fairness" here comes from normalization + private slices, not from matching arena difficulty to skill. Balanced-random over regime buckets gives variety and is trivially deterministic to log/replay (store the chosen `arena_id` in the action log).
- Selection at match start: pick a regime bucket (round-robin or uniform-random over buckets, **not** over arenas, so rare regimes like "crisis" appear as often as "bull"), then uniform-random an arena within it. Seed the RNG from match-creation entropy and **log the resulting arena_id** so `verify_replay` is exact.
- **Regime labeling — MVP heuristic (deterministic, dependency-light) over the slice's normalized close returns:**
  ```python
  # Compute on the normalized close series (so labels are arena-intrinsic, not date-dependent).
  import numpy as np
  def label_regime(norm_closes):
      r = np.diff(np.log(np.asarray(norm_closes, dtype=float)))
      total_ret = norm_closes[-1] / norm_closes[0] - 1.0
      ann_vol   = r.std() * np.sqrt(252)          # realized vol proxy
      # drawdown
      peak = np.maximum.accumulate(norm_closes)
      max_dd = float(((norm_closes - peak) / peak).min())
      if max_dd < -0.20 and ann_vol > 0.35:  return "crisis"
      if ann_vol > 0.30:                      return "volatile"
      if total_ret >  0.12:                   return "bull"
      if total_ret < -0.12:                   return "bear"
      return "sideways"
  ```
  These thresholds are starting points; tune against the curated set and store the computed `total_ret`/`ann_vol`/`max_dd` in metadata so selection/QA can re-bucket without recomputation.
- **Upgrade path (post-MVP, optional):** the 2026 consensus for richer regime detection is a hybrid **K-Means (silhouette-chosen k) → Gaussian HMM (`hmmlearn`)** pipeline on standardized cross-asset features (rolling returns, realized vol, VIX term-structure, credit spreads), with PCA (~95% variance) first. HMM adds temporal persistence the static heuristic lacks. Caveat from the literature: cluster→label mapping is arbitrary and prone to data-mining; always validate labels against known events. For our use (just bucketing curated arenas for variety) the heuristic is sufficient and fully deterministic. Sources: https://dev.to/ayratmurtazin/hybrid-machine-learning-for-market-regime-detection-in-python-hmm-k-means-11nl , https://github.com/taylorjmellon/market-regime-detection , https://datadave1.medium.com/detecting-market-regimes-k-means-57a5c55e17d9 .
- **Recommended starter arena set** (curate by *behavior*, then strip identity via normalization + generic labels — the historical period is an internal curation detail, never shown to players): a couple of strong uptrends, a couple of drawdowns/bear legs, 2–3 sideways/range-bound stretches, 2–3 high-vol stretches, and 1–2 crisis crashes (e.g. sharp multi-week selloffs). Pull these from decades of `^GSPC/^IXIC/^DJI` + FX so each arena bundles 2–4 instruments with **aligned** trading days (see OQ-D4). Aim for ~300 bars/arena to match the 5-minute (≈300 day) match length.

### OQ-D3 — Volume / extra fields in normalized data
**Decision: persist `volume` as a nullable column, but EXCLUDE it from normalization and from the content_hash's price component; do not surface it as a tradable signal in MVP.**
- Indices frequently report `0`/`NaN` volume and FX has no native volume, so volume is unreliable across instruments. Persist it when present (harmless, future-proof) but normalization touches price fields only. If a UI volume pane is ever added, normalize volume separately (e.g. to its own base or percent-of-median) and never mix it into price scaling.
- Do not invent volume where the source gives none — leave null (ties the "verify, don't manufacture" pitfall).

### OQ-D4 — Non-trading-day alignment across instruments
**Decision: use `pandas_market_calendars` to get valid sessions, reindex each instrument, then INNER-JOIN instruments on the common set of trading days. Skip non-trading days (do NOT interpolate). The simulated clock advances by bar index, so calendar gaps simply don't exist in-match.**
  ```python
  import pandas_market_calendars as mcal
  def align(instrument_frames, calendar="NYSE"):   # dict[name] -> df indexed by date
      cal = mcal.get_calendar(calendar)
      # 1) per-instrument: reindex onto valid sessions in its own range, drop genuine gaps
      # 2) across instruments: align on the INTERSECTION of dates so every bar index
      #    has a real bar for every instrument (clean multi-instrument arenas).
      common = None
      for df in instrument_frames.values():
          idx = set(df.dropna(subset=["close"]).index)
          common = idx if common is None else (common & idx)
      common = sorted(common)
      return {name: df.loc[common].reset_index() for name, df in instrument_frames.items()}
  ```
- Mixed-calendar arenas (e.g. US index + a non-US/FX instrument) lose the few non-overlapping sessions to the inner join; that is acceptable and keeps every bar index fully populated, which the deterministic sim and the `verify_replay` hash require. Pick a primary calendar (NYSE for US-equity arenas); FX trades ~24×5 so the equity calendar is the binding constraint. Document the chosen calendar per arena in metadata.

### OQ-D5 — Mystery/random start offset + content_hash design
- **Mystery offset (anti-cheat):** curate each arena from a slightly **larger** parent window and, at generation time, choose a random start offset within it before slicing ~300 bars. Combined with P[0]=100 normalization + generic labels, this removes "I recognize this is the COVID crash, day 12" recognition. The offset is resolved **once at curation** and baked into the stored arena (so the arena is fixed and re-simulable); it is **not** re-rolled per match. Store nothing in the arena that reveals the real date.
- **content_hash (determinism / `verify_replay`, ties task-001):** SHA-256 over a **canonical JSON** of the *normalized* sorted bars — sorted instrument keys, fixed field order, **Decimal values quantized to 4dp rendered as fixed strings**. Never use Python's builtin `hash()` (salted by `PYTHONHASHSEED`). The hash covers normalized prices only (not volume, not real dates, not generic labels).
  ```python
  import hashlib, json
  def content_hash(normalized_arena):  # {instrument: [ {open,high,low,close}, ... ]}
      canonical = {
          inst: [[f"{b['open']:.4f}", f"{b['high']:.4f}", f"{b['low']:.4f}", f"{b['close']:.4f}"]
                 for b in bars]
          for inst, bars in sorted(normalized_arena.items())
      }
      blob = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
      return hashlib.sha256(blob.encode("utf-8")).hexdigest()
  ```
  The loader returns this hash; task-005 logs it with the match; `verify_replay(arena_id, sorted_log)` re-loads the arena, re-checks the hash, and re-simulates to assert identical final equity/state. Because normalization and hashing are pure functions of the stored raw bars, the hash is stable across machines/runs.

### OQ-D6 — 2026 status of sources + reproducibility
**Decision: Stooq as the primary bulk source (free, no signup, still active in 2026), yfinance as a targeted/secondary fetcher (works but fragile), FRED as a clean fallback for US index closes. One-time offline fetch only; pin versions; log every fetch param.**
- **yfinance (2026):** still functional but an unofficial scraper that Yahoo actively rate-limits (HTTP 429 `YFRateLimitError`) and can break without notice. Mitigations that matter for our one-time bulk: install **`curl_cffi`** (browser-TLS impersonation; the supported default backend) or pass a `requests.Session` with a real Chrome User-Agent; **chunk** multi-ticker downloads (~80/batch) with `group_by='ticker'`, `auto_adjust=False`, `threads=True`; add local caching + throttling (`requests_cache`, `pyrate_limiter`); retry/backoff on 429. Treat it as prototyping-grade, not a runtime dependency (we only fetch once, privately). Sources: https://marketxls.com/blog/yahoo-finance-api-ultimate-guide , https://medium.com/@trading.dude/why-yfinance-keeps-getting-blocked-and-what-to-use-instead-92d84bb2cc01 , https://github.com/ranaroussi/yfinance/issues/2422 , https://github.com/ranaroussi/yfinance/issues/2614 .
- **Stooq (2026):** alive and well — bulk historical ZIPs (daily/hourly/5-min) by region + the per-symbol CSV endpoint `https://stooq.com/q/d/l/?s={symbol}&i=d`; covers ~21k securities/ETFs, ~1980 FX pairs, indices, commodities, bonds; no API/signup (some downloads gated by a CAPTCHA, so script the per-symbol CSV endpoint or do the ZIP bulk manually once). Personal-use license — fine for a private dev dataset; revisit licensing before any commercial launch. Sources: https://stooq.com/db/ , https://www.quantstart.com/articles/an-introduction-to-stooq-pricing-data/ , https://apify.com/parseforge/stooq-historical-stocks-scraper (confirms dataset still updated 2026-05).
- **FRED:** official, free, fully programmatic for US index closes (`SP500`, `DJIA`, `NASDAQCOM`) — close-only, so use it to backfill/cross-check index closes, not for full OHLC. EODHD (~$20/mo) remains the paid upgrade for deep global OHLC if needed later.
- **Reproducibility:** pin library versions in `requirements.txt` (`yfinance==<x>`, `pyarrow`, `pandas`, `pandas_market_calendars`, optionally `curl_cffi`); write a `fetch_manifest.json` per bulk run recording source, symbols, date range, fetch timestamp, and library versions; keep fetch scripts (`fetch_arenas.py`) separate from runtime; sort everything before hashing; never call external APIs during a match.

### Loader & registry schema (consolidated)
```python
# load_arena(arena_id) -> dict (server-side only; raw never leaves the server)
{
  "arena_id": "arena_0007",
  "bars": { "Broad Equities": [ {open,high,low,close}, ... ],   # normalized, Decimal-quantized
            "Tech Index":     [ ... ] },
  "labels": { "INSTR_A": "Broad Equities", "INSTR_B": "Tech Index" },  # generic, in-match
  "n_bars": 300,
  "content_hash": "<sha256>",
  "metadata": {                       # selection/QA only; NOT sent to clients in-match
    "regime": "crisis", "total_ret": -0.27, "ann_vol": 0.41, "max_dd": -0.33,
    "calendar": "NYSE", "instrument_count": 2, "source": "stooq",
    "curated_window": "<internal>", "start_offset": 14   # mystery offset, server-private
  }
}
# Registry: arenas/registry.json -> [ {arena_id, regime, n_bars, content_hash, instruments, source} ]
# CLI: fetch_arenas.py (one-time bulk) | list_arenas | load_arena(arena_id)
```

### Determinism / anti-cheat checklist (ties task-001 & task-005)
- [ ] Raw stored; normalization is a pure function applied at load (P[0]=100 on close, same factor to O/H/L/C).
- [ ] Decimal + 4dp quantize for everything entering equity/hash; floats only in fetch/clean.
- [ ] `content_hash` = SHA-256 over canonical sorted JSON of normalized prices (no builtin `hash()`, no dates, no volume).
- [ ] Inner-join multi-instrument arenas on common NYSE sessions; skip (never interpolate) non-trading days; no NaNs in O/H/L/C.
- [ ] Generic labels in-match; real names/dates only post-match (optional); raw + real dates never sent to clients.
- [ ] `arena_id` logged with the match; `verify_replay(arena_id, sorted_log)` re-loads, re-hashes, re-simulates to identical state.
- [ ] Tests: normalization math (first close == 100.0000), hash stability/roundtrip, calendar alignment, no-NaN, regime labeling determinism.