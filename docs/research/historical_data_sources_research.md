# Historical Daily (and Intraday) Data Sources for Major Stock Indices and Forex Pairs

**Research Date:** 2026-06-26 (using current web data)  
**Purpose:** Identify free or low-cost sources of EOD/daily OHLC (and intraday where available) for major indices (S&P 500/^GSPC, Nasdaq/^IXIC, Dow/^DJI, FTSE, Nikkei, etc.) and major forex pairs (EUR/USD, GBP/USD, etc.) suitable for a historical replay game. Emphasis on bulk/large-range fetches for time-accelerated replay ("each second = one trading day"), programmatic access, local/private hosting for anti-cheat, coverage depth, costs/limits, and ease of use.

**Scope Notes:** 
- Focused on EOD/daily OHLCV primary; intraday as bonus.
- Indices and FX prioritized over individual stocks.
- Suitability for replay: Ability to fetch full historical ranges easily (one or few calls per symbol), store locally (CSV/JSON/parquet), replay sequentially without ongoing API dependency or high costs.
- Adjusted data: Less critical for pure indices/FX (no corporate actions like stocks); noted where relevant.
- All sources allow private/local hosting of fetched data.
- Exhaustive on top ~7 options; others noted briefly.
- Data from official sites, docs, comparisons, and user reports (cited where factual claims derive from searches).

## Top Sources Overview

### 1. yfinance (Yahoo Finance wrapper)
- **Access:** Free Python library (pip install yfinance). No API key required for basic use. Unofficial scraper of Yahoo data.
- **Coverage:** 
  - Indices: Excellent – ^GSPC (S&P 500, back to ~1927-1950s depending on source), ^DJI (Dow), ^IXIC (Nasdaq), ^FTSE, ^N225 (Nikkei), and many global indices.
  - Forex: Major pairs like EURUSD=X, GBPUSD=X, USDJPY=X, etc. (often from early 2000s, e.g., EURUSD ~2003+).
- **Depth:** Decades for most indices (e.g., S&P 500 full history via `period='max'`); forex 15-20+ years typical.
- **Granularity:** Daily (full history), weekly/monthly. Intraday (1m-1h) limited to recent ~7-60 days.
- **Programmatic:** Extremely Python-friendly: `import yfinance as yf; df = yf.download('^GSPC', start='1950-01-01', end='2026-01-01')` or `period='max'`. Returns pandas DataFrame (Date, Open, High, Low, Close, Adj Close, Volume).
- **Rate Limits/Cost:** None official; rate-limited by Yahoo scraping (can be blocked for abuse). Free.
- **Replay Suitability:** Excellent – fetch full range in one call per symbol, cache to CSV/parquet locally. Easy bulk for multiple symbols via Tickers or loop. Time-accelerated replay straightforward with local data.
- **Normalization/Adjusted:** Adj Close for stocks (splits/divs); indices/FX usually raw OHLC (Adj Close ≈ Close). Volume for indices often 0 or N/A.
- **Private Hosting/Anti-cheat:** Fully supported – download once, store/host privately. No ongoing dependency.
- **Other Notes:** Reliable for most purposes but occasional gaps or changes in Yahoo data. Widely used for backtesting/replay. Intraday not suitable for deep history.
- **Links:** [PyPI yfinance](https://pypi.org/project/yfinance/), [Yahoo Finance examples](https://finance.yahoo.com/quote/%5EGSPC/history), GitHub ranaroussi/yfinance.

### 2. Stooq
- **Access:** Completely free, no signup. Direct bulk downloads from website (ZIPs of ASCII/CSV or Metastock format). Web interface for single symbols.
- **Coverage:** 
  - World bundle: Indices, forex (~1980+ pairs?), commodities, bonds.
  - Regional: US (large stocks/indices), UK, Japan, Hong Kong, Poland, etc.
  - Specific: Major indices (e.g., ^SPX equivalents), forex majors/minors.
- **Depth:** Decades (daily data often 20-50+ years depending on asset; forex/indices strong historical coverage).
- **Granularity:** Daily, hourly, 5-minute. Bulk files available.
- **Programmatic:** Script downloads (wget/curl of ZIP URLs or per-symbol). Use pandas `read_csv` on extracted files. pandas-datareader has Stooq support for some queries.
- **Rate Limits/Cost:** None; free bulk downloads (hundreds of MB for full sets). Personal use only (commercial prohibited per site).
- **Replay Suitability:** Outstanding for offline replay. Download world/US bundles once (or targeted), extract to local structure, load as needed. Perfect for accelerated daily replay or even intraday if desired. No API calls during game.
- **Normalization/Adjusted:** Raw OHLCV (ASCII format typically Date,Open,High,Low,Close,Volume). No adjustments noted for indices/FX.
- **Private Hosting/Anti-cheat:** Ideal – one-time download, fully private/local files.
- **Other Notes:** Data in simple CSV-like format (easy to parse/normalize). Large files but comprehensive. Update by re-downloading recent or full.
- **Links:** [Stooq Historical DB](https://stooq.com/db/h/), [Download page examples](https://stooq.com/db/).

### 3. EODHD (EOD Historical Data)
- **Access:** Free plan (API key signup) or paid. REST API, Python SDK (`pip install eodhd`), JSON/CSV output. Bulk options.
- **Coverage:** 
  - 600+ indices, 1100+ forex pairs.
  - Global stocks/ETFs/funds (150k+ tickers across 60+ exchanges).
  - Major indices (S&P, Dow, Nasdaq, international) and forex majors.
- **Depth:** 30+ years EOD for major markets (US often longer, e.g., some from 1970s); non-US mostly from ~2000. Free plan: 1 year only.
- **Granularity:** Daily (raw + adjusted), weekly/monthly. Intraday (1min/5min/etc.) on higher plans.
- **Programmatic:** Excellent – Python lib returns DataFrames. One call per symbol for full range (`from`/`to` dates or full). Bulk EOD updates available. JSON/CSV.
- **Rate Limits/Cost:** Free: 20 calls/day (1yr depth). Paid: EOD All World ~$19.99/mo (100k calls/day, full history); higher for intraday. Very affordable for reasonable use.
- **Replay Suitability:** Very high. Fetch full historical per symbol (or bulk) with paid tier once, store locally. Supports large ranges easily. Updates via daily bulk if needed.
- **Normalization/Adjusted:** Raw OHLC + adjusted close (splits/dividends); volume adjusted for splits. Indices/FX: primarily raw.
- **Private Hosting/Anti-cheat:** Yes – fetch and cache privately. Paid tier enables comprehensive initial load.
- **Other Notes:** Strong global coverage. DEMO key for testing limited tickers. Good docs and support.
- **Links:** [EODHD Site](https://eodhd.com/), [Historical EOD API docs](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes), [Pricing](https://eodhd.com/pricing).

### 4. Alpha Vantage
- **Access:** Free API key signup. REST API (JSON/CSV). Python wrappers available (e.g., alpha_vantage lib).
- **Coverage:** Stocks, market indices (dedicated endpoints for S&P 500, Dow Jones, Nasdaq Composite, Nasdaq 100, VIX, Russell 2000, others), forex, commodities, crypto.
- **Depth:** 20+ years historical for daily/intraday (since ~2000+ for many).
- **Granularity:** Daily (raw and adjusted), weekly, monthly. Intraday (1/5/15/30/60min) – historical depth often premium-gated.
- **Programmatic:** Good – direct HTTP or libs. `TIME_SERIES_DAILY`, `TIME_SERIES_DAILY_ADJUSTED`, index-specific functions, forex endpoints. Compact (recent) or full output.
- **Rate Limits/Cost:** Free tier: Limited (commonly cited ~25 calls/day or 5/min; compact output). Full history ("full" outputsize) and advanced intraday typically require premium plans (~$49.99+/mo).
- **Replay Suitability:** Good for moderate-scale (daily indices/FX). Fetch ranges with "full"; cache results. Less ideal for massive bulk without paid (rate limits slow initial fetch). Local storage fine.
- **Normalization/Adjusted:** Separate endpoints for adjusted (splits/divs). Raw available.
- **Private Hosting/Anti-cheat:** Yes.
- **Other Notes:** NASDAQ-licensed for some US data. Includes technical indicators. Free tier sufficient for testing/prototyping replay with few symbols.
- **Links:** [Alpha Vantage](https://www.alphavantage.co/), [Documentation](https://www.alphavantage.co/documentation/).

### 5. FRED (Federal Reserve Economic Data, St. Louis Fed)
- **Access:** Free API key (easy signup via account). REST API (JSON/XML/CSV). Also web downloads/graphs.
- **Coverage:** Primarily US economic/macro data, including major stock indices (S&P 500 as SP500, Dow Jones Industrial Average, others like NASDAQ composites, VIX via related series). Limited direct forex (some exchange rates as macro series, e.g., DEXUSEU).
- **Depth:** Strong for indices – daily closes. Historical often decades to 1950s/1920s+ (e.g., SP500 series charts back to 1971 or earlier in archives; full observations via API). Recent agreement notes ~10 years for some new SP/DJ series, but historical data remains accessible.
- **Granularity:** Daily (close primarily for indices).
- **Programmatic:** Very easy – `fred/series/observations` endpoint with series_id (e.g., SP500), date ranges, file_type=json. Python: `fredapi` or requests. Bulk full history supported.
- **Rate Limits/Cost:** Free with API key. No strict public limits mentioned; suitable for reasonable programmatic use.
- **Replay Suitability:** Excellent for US indices. Fetch full series history in one or few calls, store locally as CSV/DF. Sequential replay trivial. Less comprehensive for global indices or deep FX.
- **Normalization/Adjusted:** Raw index levels (closes); not price-adjusted in stock sense.
- **Private Hosting/Anti-cheat:** Fully supported.
- **Other Notes:** High-quality, official source. Many related economic series for context. API v2 for bulk.
- **Links:** [FRED API Docs](https://fred.stlouisfed.org/docs/api/fred/), [SP500 Series](https://fred.stlouisfed.org/series/SP500), [API Key Signup](https://fredaccount.stlouisfed.org/).

### 6. Finnhub
- **Access:** Free API key signup. REST + WebSocket. Good Python support (requests or client libs).
- **Coverage:** US/global stocks, indices (via candles/quotes), forex (multiple brokers), crypto.
- **Depth:** US: 30+ years historical OHLC. International: EOD or tick-level limited. Forex candles available.
- **Granularity:** Candles (daily to 1min+), tick data on plans.
- **Programmatic:** REST endpoints like `/stock/candles` or forex equivalents. Specify resolution, from/to timestamps. JSON responses.
- **Rate Limits/Cost:** Free tier generous (e.g., 60 calls/min or ~300+/day cited in comparisons; real-time limited). Paid for higher limits/depth.
- **Replay Suitability:** Strong – fetch large historical ranges (specify from/to). Cache locally. Good rate limits aid bulk initial loads.
- **Normalization/Adjusted:** Standard OHLC; adjustments depend on endpoint.
- **Private Hosting/Anti-cheat:** Yes.
- **Other Notes:** Developer-friendly with news/sentiment extras. Free tier practical for replay prototypes.
- **Links:** [Finnhub](https://finnhub.io/), [Docs/Candles](https://finnhub.io/docs/api/stock-candles), Pricing page.

### 7. Financial Modeling Prep (FMP)
- **Access:** Free tier (API key) + paid. REST API, JSON/CSV. Python-friendly.
- **Coverage:** Global stocks/ETFs, 750+ indices, forex, commodities. Major indices and FX pairs.
- **Depth:** 15+ to 30+ years EOD historical. Intraday intervals (1min to 4h).
- **Granularity:** EOD (light/full, dividend/split-adjusted options), intraday.
- **Programmatic:** Endpoints like historical-price-eod/full or /intraday. Batch and date-range support.
- **Rate Limits/Cost:** Free tier (limits e.g., requests/month or bandwidth; exact varies but usable for testing). Paid from low monthly for more.
- **Replay Suitability:** Good – full historical EOD with adjusted variants. Easy ranges for replay caching.
- **Normalization/Adjusted:** Multiple options (unadjusted, dividend-adjusted, full adjusted).
- **Private Hosting/Anti-cheat:** Yes.
- **Other Notes:** Comprehensive docs/playground. Strong for backtesting with fundamentals too.
- **Links:** [FMP Developer Docs](https://site.financialmodelingprep.com/developer/docs), Historical endpoints.

### Bonus FX-Focused: HistData.com
- **Access:** Free, no signup. Manual or scripted ZIP downloads.
- **Coverage:** ~60+ forex pairs (majors, minors, some exotics + metals like XAU/USD), some indices/commodities.
- **Depth:** Long (often 2000+ or earlier per pair/monthly files).
- **Granularity:** Tick and 1-minute (M1) bars. Aggregate to daily if needed.
- **Programmatic:** Download ZIPs by pair/year/month; parse ASCII/CSV. Formats for MT4, NinjaTrader, Excel, generic.
- **Rate Limits/Cost:** Free. Optional paid auto-updates.
- **Replay Suitability:** Good for FX – bulk historical M1/tick downloadable. Convert/aggregate for daily replay. Local files.
- **Notes:** Ready-to-import formats. Dukascopy is similar free tick export alternative.
- **Links:** [HistData.com](https://www.histdata.com/), [Download page](https://www.histdata.com/download-free-forex-data/).

**Other Mentions:** 
- **Polygon.io**: Free tier or $125 credit for new users; limited (e.g., EOD or 2yrs hist, 5 calls/min). Strong US stocks/FX; paid for more. Less free-broad than above.
- **Marketstack / Twelve Data**: Free tiers (e.g., 1000 req/mo or limited); EOD/historical with indices/FX. Good supplements.
- **Direct Exchange/Gov:** Limited free (e.g., some central banks for FX).

## Pros/Cons Comparison Table (Top Sources)

| Source       | Pros                                      | Cons                                      | Best For                          | Est. Free Tier Limits          | Global Indices/FX Strength |
|--------------|-------------------------------------------|-------------------------------------------|-----------------------------------|--------------------------------|----------------------------|
| yfinance    | Free, simple Python, decades history, bulk easy, pandas native | Unofficial (scrape risks), intraday limited, occasional data quirks | Quick Python prototyping, full offline replay | None strict (abuse risk)      | Excellent                 |
| Stooq       | 100% free bulk Zips, no signup, daily+intraday, simple CSV | No API (manual/script downloads), personal use only, file management | Large-scale offline datasets, private hosting | Unlimited free downloads     | Strong (world bundles)    |
| EODHD       | Affordable paid full depth, broad global (600+ indices, 1100+ FX), SDK, bulk, adjusted | Free very limited (1yr/20 calls), paid for depth | Production replay with global coverage | 20 calls/day (1yr)            | Excellent                 |
| Alpha Vantage | Structured API, indices-specific, indicators, JSON/CSV | Free limits tight for bulk, premium for full hist/intraday | API-based moderate use, indicators | ~25/day or 5/min (compact)   | Good (dedicated indices)  |
| FRED        | Official, free full history for US indices, simple API, bulk | Primarily US indices (limited FX), close-only mostly | US-centric index replay, macro context | Free (API key, reasonable use)| US indices strong; weak FX |
| Finnhub     | Generous free rates, 30+ yr US, forex candles, real-time option | International depth shallower on free, rate caps on free | Mixed US/global with forex      | 60/min or ~300+/day          | Good                      |
| FMP         | Flexible adjusted EOD/intraday, indices/forex, docs | Free tier bandwidth/req limits            | Backtesting with options for adjustments | Limited free (varies)        | Good                      |
| HistData (FX) | Free tick/M1 forex long history, platform formats | Manual downloads, primarily intraday (aggregate daily), fewer pairs | Detailed FX replay or backtesting | Free (ZIPs)                  | FX excellent; limited indices |

## Suitability for Time-Accelerated Historical Replay Game
- **Ideal Workflow:** Fetch full multi-year history once per symbol (or bulk), normalize to consistent OHLC (daily preferred), store in local DB/files (e.g., per-symbol Parquet/CSV or SQLite). Replay: load sequence, advance "day" per simulated second (or faster), apply any game logic.
- **Best Matches:** Stooq (bulk offline), yfinance (easy Python fetch/cache), EODHD paid (comprehensive global), FRED (US indices). These support large ranges in minimal calls/operations.
- **Challenges Avoided:** High-rate-limit sources (e.g., strict free Alpha Vantage) slow initial data load. Prefer sources allowing `from=earliest&to=latest` or bulk.
- **Intraday Bonus:** Stooq/HistData/Dukascopy for finer granularity if game needs sub-daily simulation.
- **Anti-Cheat Friendly:** All listed support full private hosting – game uses local data only, no external API calls during play (prevents tampering or rate issues). Fetch/update offline or in controlled env.
- **Normalization Notes:** Use adjusted where provided for accuracy (though minimal impact on indices/FX). Handle missing days/holidays consistently (e.g., forward-fill or skip non-trading).
- **Python Ecosystem:** Most pair well with pandas, backtrader/zipline for replay sims, or custom loops with time acceleration.

## Key Findings and Links Summary
- **Free/Zero-Cost Standouts:** yfinance, Stooq, FRED, HistData.com – sufficient for core replay without spend.
- **Low-Cost Upgrade:** EODHD ~$20/mo unlocks deep global bulk.
- **Coverage Gaps:** Pure free tiers often limit depth or calls; global non-US indices/FX deeper on paid or bulk sites.
- **Programmatic Ease:** Python-centric sources (yfinance, EODHD SDK, FRED libs) win for integration.
- **Replay Optimization:** Prioritize bulk-downloadable or full-range APIs over per-day granular calls.
- **Sources for Further:** See individual links above. Comparisons from Reddit/Quant sites confirm these as top free/low-cost for backtesting/replay.

**Full Research Sources (selected web results used):** Alpha Vantage docs, EODHD pricing/API pages, FRED API/series pages, Finnhub docs/pricing, FMP docs, Stooq DB, HistData.com, various 2025-2026 API comparison articles and Reddit threads (e.g., algotrading discussions on yfinance alternatives, data providers).

## One-Paragraph Summary
Free or low-cost options for historical daily OHLC on major indices and forex are robust for a replay game, with yfinance (decades of ^GSPC/^DJI/EURUSD=X etc. via simple Python bulk downloads) and Stooq (free no-signup bulk ZIP CSVs covering world indices/forex) standing out for zero-cost, fully local/private hosting that enables easy "second = trading day" acceleration without rate limits or external calls. EODHD offers excellent paid value (~$20/mo for 30+ years global 600+ indices/1100+ FX with SDK/bulk), while FRED excels for official US index depth (API full-history JSON), Alpha Vantage/Finnhub/FMP provide structured API access with varying free tiers (limits on depth/calls), and HistData.com delivers free tick/M1 forex for detail. Most support private caching of fetched data for anti-cheat, with adjusted/raw options and strong programmatic Python paths; top sources allow fetching large ranges in one go for efficient initial setup and offline replay.

## Follow-up Questions
1. What is the exact set of indices and forex pairs required (e.g., specific ones like FTSE 100, USDJPY, or broader)?
2. Is intraday (e.g., hourly/minute) data essential, or is daily OHLC sufficient for the replay mechanic?
3. Target replay depth (e.g., 10 years, 30+ years, or max available)?
4. Preferred tech stack (Python-only, or need other languages/APIs/Excel integration)?
5. Any need for volume data, adjusted prices, or additional fields (e.g., for game mechanics)?
6. Budget tolerance for low-cost paid tiers if free limits prove insufficient for bulk?
7. Specific anti-cheat or hosting constraints (e.g., must be fully offline after initial fetch, cloud vs local)?
8. Any preference for data provenance (e.g., official like FRED vs aggregated)?

This report is based solely on publicly available web research as of the query date. Verify current limits/coverage on provider sites before implementation, as terms can change.