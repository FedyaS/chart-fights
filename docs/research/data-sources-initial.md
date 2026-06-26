# Historical Data Sources Research (Initial)

**Goal for this doc:** Identify best sources for daily (and possibly higher) historical price data for major indices and forex to power accelerated-time replay matches.

From quick external research (2026):

## Strong Candidates

### 1. Alpha Vantage
- Free tier available
- Stocks, indices, forex, crypto, fundamentals
- Historical + realtime
- Good for developers (JSON/CSV)
- Rate limits on free tier (need to check current: typically 5-25 calls/min or daily cap)

### 2. Finnhub
- Free access to real-time + historical
- 30+ years US, international EOD
- Forex candles supported
- Easy APIs, websocket options
- Good for indices and currencies

### 3. EODHD
- Free plan (limited calls/day ~20)
- Solid EOD historical
- Upgrade paths cheap

### 4. Financial Modeling Prep (FMP)
- Free tier ~250 requests/day
- Clean historical EOD, dividend adjusted
- Good documentation

### 5. Yahoo Finance (via yfinance or direct)
- Still widely used for historical via libraries
- Note: direct CSV downloads now limited (Gold sub may be required for bulk)
- Python yfinance library is popular and free

### 6. FirstRateData, Databento, etc.
- Paid but high quality tick/intraday historical (overkill for daily replay but future-proof)

## Key Considerations for Chart-Fights
- **Daily bars sufficient?** Vision suggests yes (each second = 1 day). We can pre-fetch large ranges of daily data for periods (e.g. 2000-2026 for several indices).
- Hosting: Better to download bulk once and serve from our DB / static files for the game to avoid rate limits and "real world lookup" cheating.
- Normalization: All series should be reset to 100 at match start. Use relative % changes.
- Forex + Indices: Need consistent sources for both.
- Coverage: Aim for 8-12 major instruments initially (US indices, Europe, Asia, key FX like EURUSD, USDJPY, etc.).

## Next Steps (for main agent)
- Validate exact free tier limits and historical depth for top 3.
- Decide on pre-fetch strategy vs on-demand.
- Research best way to store/replay time-series efficiently (e.g. Parquet, SQLite, simple JSON arrays of daily returns).
- Check for economic indicator / news data tied to dates (for the "news peek" ability).

**Status:** Initial scan done. Deeper validation in progress via subagents.
