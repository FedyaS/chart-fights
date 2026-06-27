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
NEWS_DIR = DATA_ROOT / "news"

_arena_cache: Dict[str, Dict[str, Any]] = {}

# Anti-cheat (#4): players see a generic sector/asset-class label, never the ticker.
# The real ticker is kept only in `meta` for the post-match reveal.
SECTOR_LABELS: Dict[str, str] = {
    # Large-cap tech / semis / software
    "AAPL": "Large-Cap Tech", "MSFT": "Large-Cap Tech", "NVDA": "Large-Cap Tech",
    "AVGO": "Large-Cap Tech", "ADBE": "Large-Cap Tech", "CRM": "Large-Cap Tech",
    "CSCO": "Large-Cap Tech", "INTC": "Large-Cap Tech", "AMD": "Large-Cap Tech",
    # Communication & media
    "GOOGL": "Communication & Media", "META": "Communication & Media",
    "NFLX": "Communication & Media", "DIS": "Communication & Media",
    # Consumer discretionary
    "AMZN": "Consumer Discretionary", "HD": "Consumer Discretionary",
    "MCD": "Consumer Discretionary", "NKE": "Consumer Discretionary", "TSLA": "Consumer Discretionary",
    # Consumer staples
    "PG": "Consumer Staples", "KO": "Consumer Staples", "PEP": "Consumer Staples",
    "WMT": "Consumer Staples", "COST": "Consumer Staples",
    # Financials
    "JPM": "Financials", "BAC": "Financials", "WFC": "Financials", "V": "Financials", "MA": "Financials",
    # Healthcare
    "UNH": "Healthcare", "JNJ": "Healthcare", "PFE": "Healthcare", "MRK": "Healthcare",
    "TMO": "Healthcare", "ABT": "Healthcare", "DHR": "Healthcare", "LLY": "Healthcare",
    # Energy
    "XOM": "Energy", "CVX": "Energy",
    # Real estate (REITs)
    "AMT": "Real Estate", "PLD": "Real Estate",
    # Broad index ETFs
    "SPY": "Broad Equity Index", "DIA": "Broad Equity Index",
    "QQQ": "Broad Equity Index", "IWM": "Broad Equity Index",
    # Other asset classes
    "GLD": "Gold / Commodity", "TLT": "Long-Term Bonds",
}
ASSET_CLASS: Dict[str, str] = {"GLD": "Commodity", "TLT": "Bonds"}
# Per-arena codename so two slices of the same sector aren't obviously the same pick.
CODENAMES = [
    "Vega", "Orion", "Atlas", "Helix", "Nova", "Cobalt", "Zephyr", "Quartz",
    "Onyx", "Lyra", "Falcon", "Ember", "Drake", "Pulsar", "Talon", "Mirage",
]


def sector_label(ticker: str) -> str:
    return SECTOR_LABELS.get(ticker, "Equities")


def asset_class(ticker: str) -> str:
    return ASSET_CLASS.get(ticker, "Equity")


def codename_for(arena_id: str) -> str:
    h = int(hashlib.sha256(arena_id.encode("utf-8")).hexdigest(), 16)
    return CODENAMES[h % len(CODENAMES)]


def load_news(arena_id: str) -> Dict[str, Any]:
    """Load pre-generated news/econ feed for an arena, if present.
    Returns {"feed": [...], "indicators": [...]} (possibly empty)."""
    path = NEWS_DIR / f"{arena_id}.json"
    if not path.exists():
        return {"feed": [], "indicators": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"feed": data.get("feed", []), "indicators": data.get("indicators", [])}
    except Exception:
        return {"feed": [], "indicators": []}


def load_arena_index() -> List[Dict[str, Any]]:
    if not INDEX_PATH.exists():
        raise FileNotFoundError(f"Arenas index not found at {INDEX_PATH}")
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# Anti-cheat (#4): the real arena id ("AAPL_00000") embeds the ticker, so it must
# never reach the client. We expose an opaque, stable ref instead and resolve it
# back to the real id server-side. The real id stays in `meta` for post-match reveal.
_REF_SALT = "chart-fights-arena-v1"
_ref_to_real: Dict[str, str] = {}
_real_ids: set = set()


def arena_ref(real_id: str) -> str:
    return hashlib.sha256((_REF_SALT + real_id).encode("utf-8")).hexdigest()[:12]


def _ensure_ref_map() -> None:
    if _real_ids:
        return
    for m in load_arena_index():
        _real_ids.add(m["id"])
        _ref_to_real[arena_ref(m["id"])] = m["id"]


def resolve_arena_ref(token: str) -> str:
    """Map an opaque ref (or a raw real id) to the real arena id."""
    _ensure_ref_map()
    if token in _real_ids:
        return token
    return _ref_to_real.get(token, token)


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


def procedural_feed(bars: List[Dict[str, Any]], ticker: str, arena_id: str) -> Dict[str, Any]:
    """Deterministic fallback news/econ feed derived from the price path.

    Anonymized by design: references the sector and Sim Day N (never the real
    ticker or calendar date), so it preserves the #4 obfuscation even without a
    pre-generated file. Headlines are tied to actual moves so they 'explain' them.
    """
    sector = sector_label(ticker)
    feed: List[Dict[str, Any]] = []
    indicators: List[Dict[str, Any]] = []
    if not bars:
        return {"feed": feed, "indicators": indicators}

    up_lines = [
        f"{sector} catches a bid as buyers step in.",
        f"Risk-on tone lifts {sector} into the close.",
        f"{sector} rallies on upbeat positioning.",
        f"Dip-buyers reward {sector} after recent weakness.",
    ]
    down_lines = [
        f"{sector} slips as sellers take control.",
        f"Profit-taking drags {sector} lower.",
        f"{sector} under pressure amid risk-off rotation.",
        f"Caution weighs on {sector} into the session.",
    ]
    calendar_names = ["CPI", "Nonfarm Payrolls", "FOMC Rate Decision", "PPI", "Retail Sales", "GDP"]

    def seed(*parts: Any) -> int:
        return int(hashlib.sha256((arena_id + ":" + ":".join(str(p) for p in parts)).encode()).hexdigest(), 16)

    prev_close = float(bars[0].get("close", 100.0))
    for i, b in enumerate(bars):
        close = float(b.get("close", prev_close))
        ret = (close - prev_close) / prev_close if prev_close else 0.0
        prev_close = close
        # Headlines on notable moves (~>1.2%)
        if i > 0 and abs(ret) >= 0.012:
            pool = up_lines if ret > 0 else down_lines
            feed.append({
                "t": i,
                "kind": "headline",
                "title": pool[seed("hl", i) % len(pool)],
                "sentiment": "bullish" if ret > 0 else "bearish",
                "importance": "high" if abs(ret) >= 0.025 else "medium",
            })
        # Monthly-ish macro calendar print
        if i > 0 and i % 21 == 0:
            name = calendar_names[(i // 21) % len(calendar_names)]
            s = seed("cal", i)
            forecast = round(2.0 + (s % 50) / 25.0, 1)
            surprise = round(((seed("surp", i) % 7) - 3) / 10.0, 1)
            actual = round(forecast + surprise, 1)
            feed.append({
                "t": i, "kind": "calendar", "title": f"{name} released",
                "name": name, "actual": actual, "forecast": forecast,
                "prior": round(forecast - 0.1, 1), "surprise": surprise,
                "sentiment": "bullish" if surprise < 0 and name in ("CPI", "PPI") else ("bearish" if surprise > 0 and name in ("CPI", "PPI") else "neutral"),
                "importance": "high",
            })
        # Indicator snapshots (drift deterministically)
        if i % 21 == 0:
            indicators.append({
                "t": i,
                "cpi_yoy": round(3.0 + ((seed("cpi", i) % 30) - 15) / 10.0, 1),
                "unemployment": round(4.0 + ((seed("ue", i) % 20) - 10) / 10.0, 1),
                "fed_funds": round(4.5 + ((seed("ff", i) % 20) - 10) / 10.0, 2),
                "ten_year": round(4.0 + ((seed("ty", i) % 25) - 12) / 10.0, 2),
            })
    return {"feed": feed, "indicators": indicators}


def load_arena(arena_id: str, normalize: bool = True) -> Dict[str, Any]:
    if arena_id in _arena_cache:
        return _arena_cache[arena_id]

    index = load_arena_index()
    real_id = resolve_arena_ref(arena_id)
    meta = next((m for m in index if m["id"] == real_id), None)
    if meta is None:
        raise ValueError(f"Arena {arena_id} not found in index")

    file_rel = meta.get("file", f"data/arenas/{real_id}.parquet").replace("\\", "/")
    if not file_rel.startswith("data/"):
        file_rel = f"data/arenas/{real_id}.parquet"
    parquet_path = DATA_ROOT.parent / file_rel
    if not parquet_path.exists():
        parquet_path = ARENAS_DIR / f"{real_id}.parquet"
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet not found for {real_id}")

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
    sector = sector_label(ticker)
    cls = asset_class(ticker)
    generic_label = f"{sector} · {codename_for(real_id)}"
    arena_hash = compute_arena_hash(bars)

    news = load_news(real_id)
    if not news.get("feed"):
        news = procedural_feed(bars, ticker, real_id)

    result = {
        "id": arena_ref(real_id),     # opaque public ref — never the ticker-bearing real id
        "real_id": real_id,           # internal use only; never put in client payloads pre-match
        "meta": meta,                 # contains real ticker/dates -> post-match reveal only
        "bars": bars,
        "hash": arena_hash,
        "content_hash": arena_hash,
        "label": generic_label,
        "sector": sector,
        "asset_class": cls,
        "num_bars": len(bars),
        "ticker": ticker,             # internal use only; never put in client payloads pre-match
        "feed": news.get("feed", []),
        "indicators": news.get("indicators", []),
    }
    _arena_cache[arena_id] = result
    return result


def get_available_arenas(limit: int = 20) -> List[Dict[str, Any]]:
    """Lobby listing. Anti-cheat (#4): expose only the generic sector/asset-class
    label + a per-arena codename, never the real ticker or calendar date."""
    idx = load_arena_index()
    seen = set()
    out = []
    for m in idx:
        if m["ticker"] not in seen and len(out) < limit:
            seen.add(m["ticker"])
            aid = m["id"]
            out.append({
                "id": arena_ref(aid),  # opaque ref, not the ticker-bearing real id
                "label": f"{sector_label(m['ticker'])} · {codename_for(aid)}",
                "sector": sector_label(m["ticker"]),
                "asset_class": asset_class(m["ticker"]),
                "bars": m["bars"],
            })
    return out
