#!/usr/bin/env python3
"""Pre-generate news / economic-calendar feeds for chart-fights arenas (#5).

For each arena (real ticker + real date range from data/arenas_index.json) this
writes data/news/{arena_id}.json with:
  - feed:       [{t (bar index, "Sim Day"), kind: "headline"|"calendar", title,
                  sentiment, importance, [name, actual, forecast, prior, surprise]}]
  - indicators: [{t, cpi_yoy, unemployment, fed_funds, ten_year}]

Two modes:
  --api         Use Claude (claude-opus-4-8) to generate realistic headlines that
                explain the actual moves + the real macro calendar for the period.
                ANONYMIZED by design: the prompt forbids naming the company/index
                or any real calendar date — headlines reference the SECTOR and
                "Sim Day N" only, preserving the #4 obfuscation. Requires
                ANTHROPIC_API_KEY and `pip install anthropic`.
  --procedural  Deterministic price-derived fallback (reuses app.arena.procedural_feed).
                No API key needed. This is also what the backend uses at runtime
                when an arena has no pre-generated file.

Idempotent: skips arenas that already have a file unless --force.

Usage (from project root):
  python scripts/generate_news.py --procedural               # all lobby tickers, offline
  python scripts/generate_news.py --api                      # one arena per ticker via Claude
  python scripts/generate_news.py --api --all                # every arena (expensive)
  python scripts/generate_news.py --api --ids AAPL_00000 ABT_00000
  python scripts/generate_news.py --test                     # 2 arenas, validate plumbing
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.arena import (  # noqa: E402  (path set above)
    load_arena_index,
    procedural_feed,
    sector_label,
)

NEWS_DIR = ROOT / "data" / "news"
MODEL = "claude-opus-4-8"


def _arena_parquet(meta: dict) -> Path:
    rel = str(meta.get("file", f"data/arenas/{meta['id']}.parquet")).replace("\\", "/")
    p = ROOT / rel
    return p if p.exists() else (ROOT / "data" / "arenas" / f"{meta['id']}.parquet")


def _normalized_closes(path: Path) -> list[float]:
    df = pd.read_parquet(path)
    if "Close" not in df.columns or len(df) == 0:
        return []
    base = float(df["Close"].iloc[0]) or 1.0
    return [round(float(c) * 100.0 / base, 4) for c in df["Close"]]


def _path_summary(closes: list[float], step: int = 10) -> str:
    """Compact per-window % move summary so the model can place headlines on the
    right Sim Days without seeing the full series."""
    lines = []
    for i in range(0, len(closes), step):
        window = closes[i:i + step]
        if not window:
            continue
        start, end = closes[max(0, i - 1)], window[-1]
        pct = (end - start) / start * 100 if start else 0.0
        lines.append(f"  Sim Day {i}-{i + len(window) - 1}: {pct:+.1f}%")
    return "\n".join(lines)


def generate_with_api(meta: dict, closes: list[float]) -> dict | None:
    try:
        import anthropic
    except ImportError:
        print("  anthropic SDK not installed (pip install anthropic) — falling back")
        return None

    ticker = meta["ticker"]
    sector = sector_label(ticker)
    n = len(closes)
    prompt = f"""You are generating an anonymized news + economic-calendar feed for a trading game.

GROUND TRUTH (for your reasoning only — DO NOT reveal any of it in the output):
- Instrument: {ticker}
- Real date range: {meta.get('start_date')} to {meta.get('end_date')}
- Sector shown to players: "{sector}"
- The chart has {n} daily bars, indexed as Sim Day 0..{n - 1}.
- Normalized price path (% move per window):
{_path_summary(closes)}

TASK: Produce a JSON feed that makes the price moves above feel explainable.
- "headline" items: short (<= 90 char) realistic headlines for the period that plausibly
  drove the move in that window. Tie sentiment to the actual move (up window -> bullish).
- "calendar" items: the REAL major macro releases that occurred during the real date range
  (CPI, Nonfarm Payrolls / Jobs, FOMC rate decisions, PPI, GDP, etc.), each with actual/
  forecast/prior/surprise where known. Place them on the Sim Day that matches when in the
  window they occurred.
- "indicators": ~6-12 snapshots across the window of the REAL macro readings for those dates
  (cpi_yoy %, unemployment %, fed_funds %, ten_year %).

HARD ANTI-CHEAT RULES (the whole point of the game):
- NEVER name the company, its products, its ticker, or the specific index.
- NEVER use a real calendar date, year, month, or quarter label. Use "Sim Day N" only.
- Refer to the instrument generically as "{sector}" or "the asset".
- Macro events may be real (Fed, CPI) since they're market-wide, but strip any date — say
  "Sim Day N" not the real date.

Return ONLY valid JSON, no prose, with this exact shape:
{{"feed":[{{"t":0,"kind":"headline","title":"...","sentiment":"bullish|bearish|neutral","importance":"low|medium|high"}},
          {{"t":21,"kind":"calendar","name":"CPI","title":"CPI release","actual":3.2,"forecast":3.1,"prior":3.4,"surprise":0.1,"sentiment":"bearish","importance":"high"}}],
 "indicators":[{{"t":0,"cpi_yoy":3.2,"unemployment":4.1,"fed_funds":5.25,"ten_year":4.2}}]}}
All "t" must be integers in 0..{n - 1}."""

    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=8000,
            thinking={"type": "adaptive"},
            output_config={"effort": "medium"},
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:  # auth, rate limit, etc. — fall back to procedural
        print(f"  API error: {e} — falling back")
        return None

    text = next((b.text for b in resp.content if b.type == "text"), "")
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1].lstrip("json").strip() if "```" in text else text
    try:
        data = json.loads(text)
        feed = data.get("feed", [])
        indicators = data.get("indicators", [])
        if not isinstance(feed, list) or not isinstance(indicators, list):
            raise ValueError("bad shape")
        # clamp t in range
        feed = [e for e in feed if isinstance(e.get("t"), int) and 0 <= e["t"] < n]
        indicators = [i for i in indicators if isinstance(i.get("t"), int) and 0 <= i["t"] < n]
        return {"feed": feed, "indicators": indicators}
    except Exception as e:
        print(f"  JSON parse failed ({e}) — falling back")
        return None


def select_arenas(index: list[dict], args) -> list[dict]:
    if args.ids:
        wanted = set(args.ids)
        return [m for m in index if m["id"] in wanted]
    if args.all:
        return index
    if args.test:
        return index[:2]
    # default: one arena per ticker (the lobby / quick-match surface)
    seen, out = set(), []
    for m in index:
        if m["ticker"] not in seen:
            seen.add(m["ticker"])
            out.append(m)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate per-arena news/econ feeds.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--api", action="store_true", help="Generate via Claude (needs ANTHROPIC_API_KEY)")
    mode.add_argument("--procedural", action="store_true", help="Deterministic price-derived feed (offline)")
    ap.add_argument("--all", action="store_true", help="Every arena (default: one per ticker)")
    ap.add_argument("--ids", nargs="*", help="Specific arena ids")
    ap.add_argument("--test", action="store_true", help="Just 2 arenas, to validate plumbing")
    ap.add_argument("--force", action="store_true", help="Regenerate even if a file exists")
    args = ap.parse_args()

    use_api = args.api  # default to procedural if neither flag given
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    index = load_arena_index()
    arenas = select_arenas(index, args)
    print(f"Generating news for {len(arenas)} arenas | mode={'api' if use_api else 'procedural'}")

    written = skipped = fell_back = 0
    for meta in arenas:
        aid = meta["id"]
        out_path = NEWS_DIR / f"{aid}.json"
        if out_path.exists() and not args.force:
            skipped += 1
            continue
        closes = _normalized_closes(_arena_parquet(meta))
        if not closes:
            print(f"  {aid}: no bars, skipping")
            continue

        result = None
        if use_api:
            print(f"  {aid} ({meta['ticker']}) via Claude…")
            result = generate_with_api(meta, closes)
            if result is None:
                fell_back += 1
        if result is None:
            bars = [{"close": c} for c in closes]
            result = procedural_feed(bars, meta["ticker"], aid)

        result["meta"] = {"sector": sector_label(meta["ticker"]), "bars": len(closes)}
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        written += 1

    print(f"Done. written={written} skipped={skipped} api_fallbacks={fell_back}")
    print(f"Output dir: {NEWS_DIR}")


if __name__ == "__main__":
    main()
