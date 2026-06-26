"""Arena loader for normalized historical data (P[0]=100 per spec)."""
from __future__ import annotations
import json
from pathlib import Path
from decimal import Decimal
import pandas as pd
import hashlib
from typing import Dict, List, Any

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
INDEX_PATH = DATA_ROOT / "arenas_index.json"
ARENAS_DIR = DATA_ROOT / "arenas"

_arena_cache: Dict[str, Dict[str, Any]] = {}


def load_arena_index() -> List[Dict[str, Any]]:
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"Arenas index not found at {INDEX_PATH}")
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_to_p0_100(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) == 0:
        return df
    base = float(df["Close"].iloc[0])
    if base == 0:
        base = 1.0
    scale = 100.0 / base
    for col in ["Open", "High", "Low", "Close"]:
        if col in df.columns:
            df[col] = df[col] * scale
    return df


def compute_arena_hash(bars: List[Dict[str, Any]]) -> str:
    stable = json.dumps(bars, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()[:16]


def load_arena(arena_id: str, normalize: bool = True) -> Dict[str, Any]:
    if arena_id in _arena_cache:
        return _arena_cache[arena_id]

    index = load_arena_index()
    meta = next((m for m in index if m["id"] == arena_id), None)
    if meta is None:
        raise ValueError(f"Arena {arena_id} not found in index")

    file_rel = meta.get("file", f"data/arenas/{arena_id}.parquet").replace("\\", "/")
    if not file_rel.startswith("data/"):
        file_rel = f"data/arenas/{arena_id}.parquet"
    parquet_path = DATA_ROOT.parent / file_rel
    if not parquet_path.exists():
        parquet_path = ARENAS_DIR / f"{arena_id}.parquet"
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet not found for {arena_id}")

    df = pd.read_parquet(parquet_path)
    if normalize:
        df = normalize_to_p0_100(df.copy())

    bars: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        bars.append({
            "t": len(bars),
            "date": str(row.get("Date", "")),
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
        })

    ticker = meta.get("ticker", "UNKNOWN")
    generic_label = {"AAPL": "Tech Growth", "SPY": "Broad Equities"}.get(ticker, f"Asset {ticker}")
    arena_hash = compute_arena_hash(bars)
    result = {
        "id": arena_id,
        "meta": meta,
        "bars": bars,
        "hash": arena_hash,
        "content_hash": arena_hash,
        "label": generic_label,
        "num_bars": len(bars),
        "ticker": ticker,
    }
    _arena_cache[arena_id] = result
    return result


def get_available_arenas(limit: int = 20) -> List[Dict[str, Any]]:
    idx = load_arena_index()
    seen = set()
    out = []
    for m in idx:
        if m["ticker"] not in seen and len(out) < limit:
            seen.add(m["ticker"])
            out.append({"id": m["id"], "ticker": m["ticker"], "bars": m["bars"], "start": m.get("start_date")})
    return out
