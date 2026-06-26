#!/usr/bin/env python3
"""
Fetch historical daily OHLC data for chart-fights arenas.
- Uses yfinance (default) or Stooq for free bulk daily US stock data.
- Normalizes to P[0]=100 using first Close (% returns only; anti-cheat friendly).
- Slices long histories into 1000+ short "arenas" (200-300 bars each, e.g. ~8-12mo trading days).
- Robust: retries with backoff, error handling per ticker, validation (no NaN/<=0), skips bad.
- Saves as Parquet (snappy, local storage only) + index.json with metadata.
- Runnable locally; supports --test for small subset (no full run), --dry-run, --source.
- Generates 1000s+ arenas from 55+ US stocks x ~5-10y history -> variety for matches.
- Outputs:
  - data/arenas/*.parquet (normalized OHLC, columns: Date, Open, High, Low, Close)
  - data/arenas_index.json (list of {id, ticker, start_date, end_date, bars, file, source})
Usage (local, from project root):
  pip install yfinance pandas pyarrow  # or for stooq: pandas sufficient (uses http)
  python scripts/fetch_historical_data.py --source yfinance
  python scripts/fetch_historical_data.py --test --dry-run   # validate logic fast
  python scripts/fetch_historical_data.py --source stooq   # alt free bulk source
For 1000s of games: Run once to (re)gen data/ ; server picks arena_id randomly per match.
Data private/local; re-gen as needed for fresh history. See README.
"""

import argparse
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
# yfinance imported lazily in fetch to allow stooq-only runs without it
try:
    import yfinance as yf
except ImportError:
    yf = None

# Config - adjust for more/less arenas. Target: 50+ US stocks, 5-10y -> 1000+ arenas
# Pure large/mid US stocks (liquid, good history). No ETFs/indices here (can add via other means).
TICKERS = [
    # Tech / Growth (15)
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "ADBE", "CRM",
    "ORCL", "CSCO", "INTC", "AMD", "IBM",
    # Semis / Software (5)
    "QCOM", "TXN", "NOW", "SNPS", "CDNS",
    # Financials (7)
    "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK",
    # Energy (5)
    "XOM", "CVX", "COP", "SLB", "EOG",
    # Healthcare (10)
    "UNH", "JNJ", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY", "AMGN",
    # Consumer / Staples / Retail (10)
    "PG", "KO", "PEP", "COST", "WMT", "HD", "MCD", "NKE", "SBUX", "TGT",
    # Payments / Media / Telecom (8)
    "MA", "V", "DIS", "NFLX", "CMCSA", "VZ", "T", "AXP",
]  # 60 total - easily >50

PERIOD = "10y"
INTERVAL = "1d"
WINDOW_BARS = 252       # within e.g. 200-300 bars example; ~1y trading days
STEP_BARS = 42          # ~2mo step -> ~3.5-5x slices per ticker for 1000+ total (50*~30+)
MIN_BARS = 200          # enforce short but sufficient arenas; skip shorter histories

DATA_DIR = Path("data/arenas")
INDEX_FILE = Path("data/arenas_index.json")
RAW_CACHE_DIR = Path("data/raw")  # optional local storage for raw downloads (future proofing)

def normalize_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize OHLC to P[0]=100 using first Close. Idempotent if already ~100. Rounds for stability."""
    if df.empty or "Close" not in df.columns:
        return df
    first = float(df["Close"].iloc[0])
    if first <= 0:
        first = 1.0
    scale = 100.0 / first
    for col in ["Open", "High", "Low", "Close"]:
        if col in df.columns:
            df[col] = (df[col] * scale).round(4)
    return df

def _validate_ohlc(df: pd.DataFrame) -> bool:
    if df is None or df.empty:
        return False
    needed = ["Date", "Open", "High", "Low", "Close"]
    if not all(c in df.columns for c in needed):
        return False
    ohlc = df[["Open", "High", "Low", "Close"]]
    if ohlc.isna().any().any() or (ohlc <= 0).any().any():
        return False
    return True

def fetch_yfinance(ticker: str, period: str = PERIOD) -> pd.DataFrame | None:
    if yf is None:
        raise RuntimeError("yfinance not installed. pip install yfinance")
    print(f"Fetching {ticker} via yfinance (period={period}) ...")
    raw = yf.download(
        ticker,
        period=period,
        interval=INTERVAL,
        auto_adjust=True,
        progress=False,
        threads=False,  # safer for retries
    )
    if raw is None or (hasattr(raw, "empty") and raw.empty):
        print(f"  No data for {ticker}")
        return None
    # Handle Series / MultiIndex / DF cases
    if isinstance(raw, pd.Series):
        df = raw.to_frame(name="Close")
        df["Open"] = df["Close"]
        df["High"] = df["Close"]
        df["Low"] = df["Close"]
    else:
        df = raw.copy()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [str(c[0]) for c in df.columns]
        cols = [c for c in ["Open", "High", "Low", "Close"] if c in df.columns]
        if not cols:
            print(f"  No OHLC cols for {ticker}")
            return None
        df = df[cols]
    df = df.reset_index()
    # Date column may be 'Date' or 'index' or 'Datetime'
    if "Date" not in df.columns:
        for cand in ["index", "Datetime", "date"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "Date"})
                break
    if "Date" not in df.columns:
        df = df.reset_index().rename(columns={"index": "Date"})
    df = df[[c for c in ["Date", "Open", "High", "Low", "Close"] if c in df.columns]].dropna()
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df = normalize_ohlc(df)
    if not _validate_ohlc(df):
        print(f"  Validation failed for {ticker}")
        return None
    if len(df) < MIN_BARS:
        print(f"  Too short ({len(df)}) for {ticker}")
        return None
    return df

def fetch_stooq(ticker: str, years: int = 10) -> pd.DataFrame | None:
    """Alternative free source via direct CSV (no API key, US suffix)."""
    sym = f"{ticker}.US".lower()
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    print(f"Fetching {ticker} via Stooq ({sym}) ...")
    try:
        df = pd.read_csv(url)
        if df.empty or len(df) < 10:
            return None
        # Stooq CSV: Date,Open,High,Low,Close,Volume (case may vary)
        df.columns = [str(c).strip().title() for c in df.columns]
        if "Date" not in df.columns:
            return None
        keep = ["Date", "Open", "High", "Low", "Close"]
        df = df[[c for c in keep if c in df.columns]].copy()
        df = df.dropna()
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
        # Trim to ~years
        if years and len(df) > 10:
            cutoff = (pd.Timestamp.now() - pd.DateOffset(years=years)).strftime("%Y-%m-%d")
            df = df[df["Date"] >= cutoff]
        df = normalize_ohlc(df)
        if not _validate_ohlc(df):
            print(f"  Stooq validation failed for {ticker}")
            return None
        if len(df) < MIN_BARS:
            print(f"  Stooq too short ({len(df)}) for {ticker}")
            return None
        return df
    except Exception as e:
        print(f"  Stooq error for {ticker}: {e}")
        return None

def fetch_ticker(ticker: str, source: str = "yfinance", period: str = PERIOD) -> pd.DataFrame | None:
    """Robust fetch with retries + jitter for rate limits / transient errors. Uses local-friendly sources."""
    max_retries = 5
    for attempt in range(max_retries):
        try:
            if source == "stooq":
                df = fetch_stooq(ticker, years=10 if "10y" in str(period) or period == "max" else 5)
            else:
                df = fetch_yfinance(ticker, period=period)
            if df is not None and _validate_ohlc(df) and len(df) >= MIN_BARS:
                return df
            # if partial, still may retry
        except Exception as e:
            print(f"  Attempt {attempt+1} error for {ticker} ({source}): {e}")
        # backoff + jitter (robust to Yahoo/Stooq throttling)
        sleep_s = (2 ** attempt) + random.uniform(0.5, 1.5)
        if attempt < max_retries - 1:
            print(f"  Retrying {ticker} in {sleep_s:.1f}s ...")
            time.sleep(sleep_s)
    print(f"  Giving up on {ticker} after retries.")
    return None

def create_arenas(df: pd.DataFrame, ticker: str, source: str = "yfinance", window: int = None, step: int = None, min_bars: int | None = None) -> list[dict]:
    """Slice into short contiguous arenas. Always store forward-slash paths for cross-platform."""
    window = window or WINDOW_BARS
    step = step or STEP_BARS
    seg_min = min_bars if min_bars is not None else min(MIN_BARS, window)
    arenas = []
    n = len(df)
    if n < seg_min:
        return arenas

    start_idx = 0
    arena_counter = 0
    while start_idx + window <= n:
        segment = df.iloc[start_idx : start_idx + window].copy()
        if len(segment) < seg_min:
            break

        arena_id = f"{ticker}_{start_idx:05d}"
        filename = f"{arena_id}.parquet"
        filepath = DATA_DIR / filename

        # Save as Parquet - local storage only (snappy compression for small fast files). pyarrow preferred if present.
        try:
            segment.to_parquet(filepath, index=False, compression="snappy", engine="pyarrow")
        except Exception:
            segment.to_parquet(filepath, index=False, compression="snappy")  # fallback (fastparquet or default)

        # Always use posix-style relative path in index for loader compat (win/linux)
        file_rel = f"data/arenas/{filename}"
        meta = {
            "id": arena_id,
            "ticker": ticker,
            "start_date": segment["Date"].iloc[0],
            "end_date": segment["Date"].iloc[-1],
            "bars": len(segment),
            "file": file_rel,
            "source": source,
        }
        arenas.append(meta)

        arena_counter += 1
        start_idx += step

    print(f"  Created {arena_counter} arenas for {ticker} (window={window}, step={step})")
    return arenas


def rebuild_index_from_disk(source: str = "yfinance") -> list[dict]:
    """Rebuild arenas_index.json from existing parquet files (no network)."""
    entries: list[dict] = []
    for fp in sorted(DATA_DIR.glob("*.parquet")):
        arena_id = fp.stem
        ticker = arena_id.rsplit("_", 1)[0]
        try:
            df = pd.read_parquet(fp)
        except Exception as e:
            print(f"  Skip {arena_id}: {e}")
            continue
        if df.empty or "Close" not in df.columns:
            continue
        date_col = "Date" if "Date" in df.columns else df.columns[0]
        entries.append({
            "id": arena_id,
            "ticker": ticker,
            "start_date": str(df[date_col].iloc[0])[:10],
            "end_date": str(df[date_col].iloc[-1])[:10],
            "bars": len(df),
            "file": f"data/arenas/{fp.name}",
            "source": source,
        })
    entries.sort(key=lambda x: (x["ticker"], x["id"]))
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    print(f"Rebuilt index: {len(entries)} entries from {DATA_DIR}")
    return entries


def main():
    parser = argparse.ArgumentParser(description="Generate normalized stock arenas for Chart-Fights (1000+ real historical slices).")
    parser.add_argument("--source", choices=["yfinance", "stooq"], default="yfinance", help="Data source (yfinance recommended; stooq alt free no-key)")
    parser.add_argument("--test", action="store_true", help="Small test set: first 5 tickers + shorter period/window, fewer arenas. Safe for quick runs.")
    parser.add_argument("--dry-run", action="store_true", help="Compute #arenas / simulate without network fetches or writes. Good for validation.")
    parser.add_argument("--window", type=int, default=None, help="Override WINDOW_BARS (200-300 recommended)")
    parser.add_argument("--step", type=int, default=None, help="Override STEP_BARS (smaller = more arenas)")
    parser.add_argument("--rebuild-index", action="store_true", help="Rebuild index from existing parquet files (no network)")
    args = parser.parse_args()

    if args.rebuild_index:
        rebuild_index_from_disk(source=args.source)
        return

    source = args.source
    test_mode = args.test
    dry_run = args.dry_run
    win = args.window or (252 if test_mode else WINDOW_BARS)
    stp = args.step or (42 if test_mode else STEP_BARS)
    seg_min = min(MIN_BARS, win) if test_mode else MIN_BARS

    effective_tickers = TICKERS[:5] if test_mode else TICKERS
    effective_period = "2y" if test_mode else PERIOD

    print(f"Starting arena generation | source={source} | test={test_mode} | dry={dry_run}")
    print(f"Tickers: {len(effective_tickers)} (of {len(TICKERS)}) | window={win} | step={stp}")
    print(f"Target arenas: est. {int(len(effective_tickers) * max(1, (2000/win) * (win/stp)))} (aim >1000 total possible)")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)  # for future raw cache use

    all_arenas = []
    errors = []

    for i, ticker in enumerate(effective_tickers):
        if dry_run:
            # Simulate: assume typical 10y~2520 bars -> many slices
            n_sim = 2200 if not test_mode else 450
            n_arenas = max(0, (n_sim - win) // stp + 1) if n_sim > win else 0
            print(f"[DRY] Would fetch {ticker} -> ~{n_arenas} arenas")
            # still generate dummy metas for count test (no net, no write)
            for s in range(0, max(0, n_sim - win + 1), stp):
                aid = f"{ticker}_{s:05d}"
                all_arenas.append({
                    "id": aid, "ticker": ticker, "start_date": "2016-01-01", "end_date": "2016-12-31",
                    "bars": win, "file": f"data/arenas/{aid}.parquet", "source": source
                })
            continue

        df = fetch_ticker(ticker, source=source, period=effective_period)
        if df is None or len(df) < seg_min:
            errors.append(ticker)
            time.sleep(0.5)
            continue

        arenas = create_arenas(df, ticker, source=source, window=win, step=stp, min_bars=seg_min)
        all_arenas.extend(arenas)

        # Polite delay + jitter (robust)
        delay = 1.2 + random.uniform(0, 0.8) if source == "yfinance" else 0.3
        if i < len(effective_tickers) - 1:
            time.sleep(delay)

    # Write index only if not dry (but dry simulated some); never wipe with empty fetch
    if not dry_run or all_arenas:
        # Dedup by id just in case, sort stable
        seen = set()
        unique_arenas = []
        for a in all_arenas:
            if a["id"] not in seen:
                seen.add(a["id"])
                unique_arenas.append(a)
        unique_arenas.sort(key=lambda x: (x["ticker"], x["id"]))

        if not dry_run and not unique_arenas:
            print("No new arenas fetched; preserving existing index (use --rebuild-index to scan disk).")
            if INDEX_FILE.exists():
                with open(INDEX_FILE, "r", encoding="utf-8") as f:
                    unique_arenas = json.load(f)
            else:
                unique_arenas = rebuild_index_from_disk(source=source)
        elif not dry_run:
            # Merge with existing index entries so partial runs don't drop prior arenas
            existing: list[dict] = []
            if INDEX_FILE.exists():
                try:
                    with open(INDEX_FILE, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = []
            merged = {a["id"]: a for a in existing}
            for a in unique_arenas:
                merged[a["id"]] = a
            unique_arenas = sorted(merged.values(), key=lambda x: (x["ticker"], x["id"]))
            with open(INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(unique_arenas, f, indent=2)
        elif dry_run:
            pass  # dry-run count only; no write

        print(f"\nDone! Total arenas written/simulated: {len(unique_arenas)}")
        print(f"Index: {INDEX_FILE} (absolute: {INDEX_FILE.resolve()})")
        print(f"Arenas dir: {DATA_DIR.resolve()}")
        if unique_arenas:
            print("Example arena:", unique_arenas[0])
    else:
        print("\nDry run complete (no writes).")

    if errors and not dry_run:
        print(f"Tickers with errors/skips: {errors}")
    print("Run with --test --dry-run to validate quickly. Re-run full for fresh 1000s of arenas.")
    print("This enables 1000s of unique real-historical normalized games (server selects by id).")


if __name__ == "__main__":
    main()