"""Standalone dataflow library for TradingAgentsCC.

Provides all data fetching functions needed by the tool scripts without
requiring a local TradingAgents installation.
"""
from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime
from typing import Iterable, Optional

import pandas as pd
import requests
import yfinance as yf
from dateutil.relativedelta import relativedelta
from stockstats import wrap
from yfinance.exceptions import YFRateLimitError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

_HOME = os.path.join(os.path.expanduser("~"), ".tradingagentscc")

_CONFIG = {
    "data_cache_dir": os.getenv("TRADINGAGENTSCC_CACHE_DIR", os.path.join(_HOME, "cache")),
    "news_article_limit": 20,
    "global_news_article_limit": 10,
    "global_news_lookback_days": 7,
    "global_news_queries": [
        "Federal Reserve interest rates inflation",
        "S&P 500 earnings GDP economic outlook",
        "geopolitical risk trade war sanctions",
        "ECB Bank of England BOJ central bank policy",
        "oil commodities supply chain energy",
    ],
}

# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

_TICKER_PATH_RE = re.compile(r"^[A-Za-z0-9._\-\^]+$")


def safe_ticker_component(value: str, *, max_len: int = 32) -> str:
    """Validate ticker is safe to interpolate into a filesystem path."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"ticker must be a non-empty string, got {value!r}")
    if len(value) > max_len:
        raise ValueError(f"ticker exceeds {max_len} chars: {value!r}")
    if not _TICKER_PATH_RE.fullmatch(value):
        raise ValueError(f"ticker contains characters not allowed in a filesystem path: {value!r}")
    if set(value) == {"."}:
        raise ValueError(f"ticker cannot consist solely of dots: {value!r}")
    return value


def yf_retry(func, max_retries=3, base_delay=2.0):
    """Execute a yfinance call with exponential backoff on rate limits."""
    for attempt in range(max_retries + 1):
        try:
            return func()
        except YFRateLimitError:
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "Yahoo Finance rate limited, retrying in %.0fs (attempt %d/%d)",
                    delay, attempt + 1, max_retries,
                )
                time.sleep(delay)
            else:
                raise


def _clean_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """Normalize a stock DataFrame for stockstats: parse dates, drop invalid rows, fill price gaps."""
    if "Date" not in data.columns:
        for candidate in ("Datetime", "date", "datetime", "index"):
            if candidate in data.columns:
                data = data.rename(columns={candidate: "Date"})
                break
    data["Date"] = pd.to_datetime(data["Date"], errors="coerce")
    data = data.dropna(subset=["Date"])
    price_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in data.columns]
    data[price_cols] = data[price_cols].apply(pd.to_numeric, errors="coerce")
    data = data.dropna(subset=["Close"])
    data[price_cols] = data[price_cols].ffill().bfill()
    return data


def load_ohlcv(symbol: str, curr_date: str) -> pd.DataFrame:
    """Fetch OHLCV data with file caching, filtered to prevent look-ahead bias."""
    safe_symbol = safe_ticker_component(symbol)
    cache_dir = _CONFIG["data_cache_dir"]
    curr_date_dt = pd.to_datetime(curr_date)

    today_date = pd.Timestamp.today()
    start_date = today_date - pd.DateOffset(years=5)
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = today_date.strftime("%Y-%m-%d")

    os.makedirs(cache_dir, exist_ok=True)
    data_file = os.path.join(cache_dir, f"{safe_symbol}-YFin-data-{start_str}-{end_str}.csv")

    if os.path.exists(data_file):
        data = pd.read_csv(data_file, on_bad_lines="skip", encoding="utf-8")
    else:
        data = yf_retry(lambda: yf.download(
            symbol,
            start=start_str,
            end=end_str,
            multi_level_index=False,
            progress=False,
            auto_adjust=True,
        ))
        data = data.reset_index()
        data.to_csv(data_file, index=False, encoding="utf-8")

    data = _clean_dataframe(data)
    data = data[data["Date"] <= curr_date_dt]
    return data


def filter_financials_by_date(data: pd.DataFrame, curr_date: str) -> pd.DataFrame:
    """Drop financial statement columns after curr_date to prevent look-ahead bias."""
    if not curr_date or data.empty:
        return data
    cutoff = pd.Timestamp(curr_date)
    mask = pd.to_datetime(data.columns, errors="coerce") <= cutoff
    return data.loc[:, mask]


# ---------------------------------------------------------------------------
# Market data & technical indicators
# ---------------------------------------------------------------------------

def get_YFin_data_online(symbol: str, start_date: str, end_date: str) -> dict:
    """Fetch OHLCV price history from yfinance as columnar dict."""
    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")

    base: dict = {
        "symbol": symbol.upper(),
        "start_date": start_date,
        "end_date": end_date,
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "records": 0,
        "dates": [], "open": [], "high": [], "low": [], "close": [], "volume": [],
    }

    try:
        ticker = yf.Ticker(symbol.upper())
        data = yf_retry(lambda: ticker.history(start=start_date, end=end_date))
    except Exception as e:
        base["error"] = f"Error fetching price data: {e}"
        return base

    if data.empty:
        return base

    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)

    for col in ["Open", "High", "Low", "Close"]:
        if col in data.columns:
            data[col] = data[col].round(2)

    base["dates"] = [idx.strftime("%Y-%m-%d") for idx in data.index]
    for src, dst in (("Open", "open"), ("High", "high"), ("Low", "low"), ("Close", "close")):
        if src in data.columns:
            base[dst] = [None if pd.isna(v) else float(v) for v in data[src]]
    if "Volume" in data.columns:
        base["volume"] = [None if pd.isna(v) else int(v) for v in data["Volume"]]
    base["records"] = len(data)
    return base


def _get_stock_stats_bulk(symbol: str, indicator: str, curr_date: str) -> dict:
    """Calculate all indicator values in one pass. Returns {date_str: value_str}."""
    data = load_ohlcv(symbol, curr_date)
    df = wrap(data)
    df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
    df[indicator]  # trigger stockstats calculation
    result = {}
    for _, row in df.iterrows():
        val = row[indicator]
        result[row["Date"]] = "N/A" if pd.isna(val) else str(val)
    return result


def _get_stock_stats_single(symbol: str, indicator: str, curr_date: str) -> str:
    """Fallback: get a single indicator value for one date."""
    try:
        data = load_ohlcv(symbol, curr_date)
        df = wrap(data)
        df["Date"] = df["Date"].dt.strftime("%Y-%m-%d")
        curr_date_str = pd.to_datetime(curr_date).strftime("%Y-%m-%d")
        df[indicator]
        matching = df[df["Date"].str.startswith(curr_date_str)]
        if not matching.empty:
            return str(matching[indicator].values[0])
        return "N/A: Not a trading day (weekend or holiday)"
    except Exception as e:
        return f"Error: {e}"


_INDICATOR_DESCRIPTIONS = {
    "close_50_sma": (
        "50 SMA: A medium-term trend indicator. "
        "Usage: Identify trend direction and serve as dynamic support/resistance. "
        "Tips: It lags price; combine with faster indicators for timely signals."
    ),
    "close_200_sma": (
        "200 SMA: A long-term trend benchmark. "
        "Usage: Confirm overall market trend and identify golden/death cross setups. "
        "Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries."
    ),
    "close_10_ema": (
        "10 EMA: A responsive short-term average. "
        "Usage: Capture quick shifts in momentum and potential entry points. "
        "Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals."
    ),
    "macd": (
        "MACD: Computes momentum via differences of EMAs. "
        "Usage: Look for crossovers and divergence as signals of trend changes. "
        "Tips: Confirm with other indicators in low-volatility or sideways markets."
    ),
    "macds": (
        "MACD Signal: An EMA smoothing of the MACD line. "
        "Usage: Use crossovers with the MACD line to trigger trades. "
        "Tips: Should be part of a broader strategy to avoid false positives."
    ),
    "macdh": (
        "MACD Histogram: Shows the gap between the MACD line and its signal. "
        "Usage: Visualize momentum strength and spot divergence early. "
        "Tips: Can be volatile; complement with additional filters in fast-moving markets."
    ),
    "rsi": (
        "RSI: Measures momentum to flag overbought/oversold conditions. "
        "Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. "
        "Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis."
    ),
    "boll": (
        "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. "
        "Usage: Acts as a dynamic benchmark for price movement. "
        "Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals."
    ),
    "boll_ub": (
        "Bollinger Upper Band: Typically 2 standard deviations above the middle line. "
        "Usage: Signals potential overbought conditions and breakout zones. "
        "Tips: Confirm signals with other tools; prices may ride the band in strong trends."
    ),
    "boll_lb": (
        "Bollinger Lower Band: Typically 2 standard deviations below the middle line. "
        "Usage: Indicates potential oversold conditions. "
        "Tips: Use additional analysis to avoid false reversal signals."
    ),
    "atr": (
        "ATR: Averages true range to measure volatility. "
        "Usage: Set stop-loss levels and adjust position sizes based on current market volatility. "
        "Tips: It's a reactive measure, so use it as part of a broader risk management strategy."
    ),
    "vwma": (
        "VWMA: A moving average weighted by volume. "
        "Usage: Confirm trends by integrating price action with volume data. "
        "Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses."
    ),
    "mfi": (
        "MFI: The Money Flow Index is a momentum indicator that uses both price and volume to measure buying and selling pressure. "
        "Usage: Identify overbought (>80) or oversold (<20) conditions and confirm the strength of trends or reversals. "
        "Tips: Use alongside RSI or MACD to confirm signals; divergence between price and MFI can indicate potential reversals."
    ),
}


def _coerce_indicator_value(raw):
    """Coerce stockstats string output to float, or None for missing days."""
    if raw is None or raw == "N/A":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def get_stock_stats_indicators_window(symbol: str, indicator: str, curr_date: str, look_back_days: int) -> dict:
    """Return technical indicator values for a date window ending at curr_date.

    Returns a dict with chronological (oldest → newest) `dates` and `values` arrays.
    Missing/non-trading days have value=None.
    """
    if indicator not in _INDICATOR_DESCRIPTIONS:
        raise ValueError(f"Indicator {indicator} is not supported. Choose from: {list(_INDICATOR_DESCRIPTIONS.keys())}")

    curr_date_dt = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_date_dt - relativedelta(days=look_back_days)

    base: dict = {
        "indicator": indicator,
        "symbol": symbol.upper(),
        "start_date": before.strftime("%Y-%m-%d"),
        "end_date": curr_date,
        "description": _INDICATOR_DESCRIPTIONS.get(indicator, "No description available."),
        "dates": [],
        "values": [],
        "fallback": False,
    }

    try:
        indicator_data = _get_stock_stats_bulk(symbol, indicator, curr_date)
        current_dt = before
        while current_dt <= curr_date_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            base["dates"].append(date_str)
            base["values"].append(_coerce_indicator_value(indicator_data.get(date_str)))
            current_dt += relativedelta(days=1)
    except Exception as e:
        import sys as _sys
        print(f"Bulk stockstats error: {e}, falling back to per-day mode", file=_sys.stderr)
        base["fallback"] = True
        current_dt = before
        while current_dt <= curr_date_dt:
            date_str = current_dt.strftime("%Y-%m-%d")
            raw = _get_stock_stats_single(symbol, indicator, date_str)
            base["dates"].append(date_str)
            base["values"].append(_coerce_indicator_value(raw))
            current_dt += relativedelta(days=1)

    return base


# ---------------------------------------------------------------------------
# Financial statements
# ---------------------------------------------------------------------------

_FUNDAMENTAL_FIELDS = [
    ("Name", "longName"),
    ("Sector", "sector"),
    ("Industry", "industry"),
    ("Market Cap", "marketCap"),
    ("PE Ratio (TTM)", "trailingPE"),
    ("Forward PE", "forwardPE"),
    ("PEG Ratio", "pegRatio"),
    ("Price to Book", "priceToBook"),
    ("EPS (TTM)", "trailingEps"),
    ("Forward EPS", "forwardEps"),
    ("Dividend Yield", "dividendYield"),
    ("Beta", "beta"),
    ("52 Week High", "fiftyTwoWeekHigh"),
    ("52 Week Low", "fiftyTwoWeekLow"),
    ("50 Day Average", "fiftyDayAverage"),
    ("200 Day Average", "twoHundredDayAverage"),
    ("Revenue (TTM)", "totalRevenue"),
    ("Gross Profit", "grossProfits"),
    ("EBITDA", "ebitda"),
    ("Net Income", "netIncomeToCommon"),
    ("Profit Margin", "profitMargins"),
    ("Operating Margin", "operatingMargins"),
    ("Return on Equity", "returnOnEquity"),
    ("Return on Assets", "returnOnAssets"),
    ("Debt to Equity", "debtToEquity"),
    ("Current Ratio", "currentRatio"),
    ("Book Value", "bookValue"),
    ("Free Cash Flow", "freeCashflow"),
]


def get_fundamentals(ticker: str, curr_date: str = None) -> dict:
    """Get company fundamentals overview from yfinance.

    Returns dict with ordered `fields` (label → value) preserving canonical order.
    """
    base: dict = {
        "ticker": ticker.upper(),
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "fields": {},
    }
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        info = yf_retry(lambda: ticker_obj.info)
        if not info:
            base["error"] = f"No fundamentals data found for symbol '{ticker}'"
            return base
        for label, key in _FUNDAMENTAL_FIELDS:
            value = info.get(key)
            if value is not None:
                base["fields"][label] = value
        return base
    except Exception as e:
        base["error"] = f"Error retrieving fundamentals for {ticker}: {str(e)}"
        return base


def _coerce_cell(value):
    """Coerce a DataFrame cell to JSON-friendly type."""
    if pd.isna(value):
        return None
    if isinstance(value, (int,)) and not isinstance(value, bool):
        return int(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def _financials_to_dict(ticker: str, freq: str, statement_type: str, data, curr_date: str | None) -> dict:
    """Convert a financials DataFrame (period columns, line-item rows) to dict."""
    base: dict = {
        "ticker": ticker.upper(),
        "freq": freq,
        "statement_type": statement_type,
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "periods": [],
        "rows": [],
    }
    data = filter_financials_by_date(data, curr_date)
    if data is None or data.empty:
        return base
    base["periods"] = [
        col.strftime("%Y-%m-%d") if hasattr(col, "strftime") else str(col)
        for col in data.columns
    ]
    rows = []
    for label, row in data.iterrows():
        rows.append({
            "label": str(label),
            "values": [_coerce_cell(v) for v in row.tolist()],
        })
    base["rows"] = rows
    return base


def get_balance_sheet(ticker: str, freq: str = "quarterly", curr_date: str = None) -> dict:
    """Get balance sheet data from yfinance as structured dict."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        if freq.lower() == "quarterly":
            data = yf_retry(lambda: ticker_obj.quarterly_balance_sheet)
        else:
            data = yf_retry(lambda: ticker_obj.balance_sheet)
        return _financials_to_dict(ticker, freq, "balance_sheet", data, curr_date)
    except Exception as e:
        return {
            "ticker": ticker.upper(), "freq": freq, "statement_type": "balance_sheet",
            "error": f"Error retrieving balance sheet for {ticker}: {str(e)}",
            "periods": [], "rows": [],
        }


def get_cashflow(ticker: str, freq: str = "quarterly", curr_date: str = None) -> dict:
    """Get cash flow data from yfinance as structured dict."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        if freq.lower() == "quarterly":
            data = yf_retry(lambda: ticker_obj.quarterly_cashflow)
        else:
            data = yf_retry(lambda: ticker_obj.cashflow)
        return _financials_to_dict(ticker, freq, "cashflow", data, curr_date)
    except Exception as e:
        return {
            "ticker": ticker.upper(), "freq": freq, "statement_type": "cashflow",
            "error": f"Error retrieving cash flow for {ticker}: {str(e)}",
            "periods": [], "rows": [],
        }


def get_income_statement(ticker: str, freq: str = "quarterly", curr_date: str = None) -> dict:
    """Get income statement data from yfinance as structured dict."""
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        if freq.lower() == "quarterly":
            data = yf_retry(lambda: ticker_obj.quarterly_income_stmt)
        else:
            data = yf_retry(lambda: ticker_obj.income_stmt)
        return _financials_to_dict(ticker, freq, "income_statement", data, curr_date)
    except Exception as e:
        return {
            "ticker": ticker.upper(), "freq": freq, "statement_type": "income_statement",
            "error": f"Error retrieving income statement for {ticker}: {str(e)}",
            "periods": [], "rows": [],
        }


def get_insider_transactions(ticker: str) -> dict:
    """Get insider transactions data from yfinance as structured dict."""
    base: dict = {
        "ticker": ticker.upper(),
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "columns": [],
        "transactions": [],
    }
    try:
        ticker_obj = yf.Ticker(ticker.upper())
        data = yf_retry(lambda: ticker_obj.insider_transactions)
        if data is None or data.empty:
            return base
        base["columns"] = [str(c) for c in data.columns]
        for _, row in data.iterrows():
            tx = {str(col): _coerce_cell(row[col]) for col in data.columns}
            base["transactions"].append(tx)
        return base
    except Exception as e:
        base["error"] = f"Error retrieving insider transactions for {ticker}: {str(e)}"
        return base


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------

def _extract_article_data(article: dict) -> dict:
    """Extract article data from yfinance news format (handles nested 'content' structure)."""
    if "content" in article:
        content = article["content"]
        title = content.get("title", "No title")
        summary = content.get("summary", "")
        provider = content.get("provider", {})
        publisher = provider.get("displayName", "Unknown")
        url_obj = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
        link = url_obj.get("url", "")
        pub_date_str = content.get("pubDate", "")
        pub_date = None
        if pub_date_str:
            try:
                pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass
        return {"title": title, "summary": summary, "publisher": publisher, "link": link, "pub_date": pub_date}
    return {
        "title": article.get("title", "No title"),
        "summary": article.get("summary", ""),
        "publisher": article.get("publisher", "Unknown"),
        "link": article.get("link", ""),
        "pub_date": None,
    }


def get_news_yfinance(ticker: str, start_date: str, end_date: str) -> str:
    """Retrieve news for a specific stock ticker using yfinance."""
    article_limit = _CONFIG["news_article_limit"]
    try:
        stock = yf.Ticker(ticker)
        news = yf_retry(lambda: stock.get_news(count=article_limit))
        if not news:
            return f"No news found for {ticker}"
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        news_str = ""
        filtered_count = 0
        for article in news:
            data = _extract_article_data(article)
            if data["pub_date"]:
                pub_date_naive = data["pub_date"].replace(tzinfo=None)
                if not (start_dt <= pub_date_naive <= end_dt + relativedelta(days=1)):
                    continue
            news_str += f"### {data['title']} (source: {data['publisher']})\n"
            if data["summary"]:
                news_str += f"{data['summary']}\n"
            if data["link"]:
                news_str += f"Link: {data['link']}\n"
            news_str += "\n"
            filtered_count += 1
        if filtered_count == 0:
            return f"No news found for {ticker} between {start_date} and {end_date}"
        return f"## {ticker} News, from {start_date} to {end_date}:\n\n{news_str}"
    except Exception as e:
        return f"Error fetching news for {ticker}: {str(e)}"


def get_global_news_yfinance(curr_date: str, look_back_days: Optional[int] = None, limit: Optional[int] = None) -> str:
    """Retrieve global/macro economic news using yfinance Search."""
    if look_back_days is None:
        look_back_days = _CONFIG["global_news_lookback_days"]
    if limit is None:
        limit = _CONFIG["global_news_article_limit"]
    search_queries = _CONFIG["global_news_queries"]
    all_news: list = []
    seen_titles: set = set()
    try:
        for query in search_queries:
            search = yf_retry(lambda q=query: yf.Search(query=q, news_count=limit, enable_fuzzy_query=True))
            if search.news:
                for article in search.news:
                    title = _extract_article_data(article)["title"] if "content" in article else article.get("title", "")
                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        all_news.append(article)
            if len(all_news) >= limit:
                break
        if not all_news:
            return f"No global news found for {curr_date}"
        curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        start_dt = curr_dt - relativedelta(days=look_back_days)
        news_str = ""
        for article in all_news[:limit]:
            if "content" in article:
                data = _extract_article_data(article)
                if data.get("pub_date"):
                    pub_naive = data["pub_date"].replace(tzinfo=None)
                    if pub_naive > curr_dt + relativedelta(days=1):
                        continue
                title = data["title"]
                publisher = data["publisher"]
                link = data["link"]
                summary = data["summary"]
            else:
                title = article.get("title", "No title")
                publisher = article.get("publisher", "Unknown")
                link = article.get("link", "")
                summary = ""
            news_str += f"### {title} (source: {publisher})\n"
            if summary:
                news_str += f"{summary}\n"
            if link:
                news_str += f"Link: {link}\n"
            news_str += "\n"
        return f"## Global Market News, from {start_dt.strftime('%Y-%m-%d')} to {curr_date}:\n\n{news_str}"
    except Exception as e:
        return f"Error fetching global news: {str(e)}"


# ---------------------------------------------------------------------------
# Social sentiment
# ---------------------------------------------------------------------------

_REDDIT_API = "https://www.reddit.com/r/{sub}/search.json"
_STOCKTWITS_API = "https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
_UA = "tradingagentscc/0.1"
_HTTP_HEADERS = {"User-Agent": _UA, "Accept": "application/json"}

DEFAULT_SUBREDDITS = ("wallstreetbets", "stocks", "investing")


def _http_timeout(timeout: float) -> tuple:
    """Split a single-value timeout into (connect, read) for requests."""
    return (min(timeout, 5.0), timeout)


def _fetch_subreddit(ticker: str, sub: str, limit: int, timeout: float) -> list:
    url = _REDDIT_API.format(sub=sub)
    params = {"q": ticker, "restrict_sr": "on", "sort": "new", "t": "week", "limit": limit}
    try:
        resp = requests.get(url, params=params, headers=_HTTP_HEADERS, timeout=_http_timeout(timeout))
        resp.raise_for_status()
        payload = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("Reddit fetch failed for r/%s · %s: %s", sub, ticker, exc)
        return []
    children = (payload.get("data") or {}).get("children") or []
    return [c.get("data", {}) for c in children if isinstance(c, dict)]


def fetch_reddit_posts(
    ticker: str,
    subreddits: Iterable[str] = DEFAULT_SUBREDDITS,
    limit_per_sub: int = 5,
    timeout: float = 10.0,
    inter_request_delay: float = 0.4,
) -> str:
    """Fetch recent Reddit posts mentioning ticker across finance subreddits."""
    blocks = []
    total_posts = 0
    for i, sub in enumerate(subreddits):
        if i > 0:
            time.sleep(inter_request_delay)
        posts = _fetch_subreddit(ticker, sub, limit_per_sub, timeout)
        total_posts += len(posts)
        if not posts:
            blocks.append(f"r/{sub}: <no posts found mentioning {ticker.upper()} in the past 7 days>")
            continue
        lines = [f"r/{sub} — {len(posts)} recent posts mentioning {ticker.upper()}:"]
        for p in posts:
            title = (p.get("title") or "").replace("\n", " ").strip()
            score = p.get("score", 0)
            comments = p.get("num_comments", 0)
            created = p.get("created_utc")
            created_str = time.strftime("%Y-%m-%d", time.gmtime(created)) if created else "?"
            selftext = (p.get("selftext") or "").replace("\n", " ").strip()
            if len(selftext) > 240:
                selftext = selftext[:240] + "…"
            lines.append(
                f"  [{created_str} · {score:>4}↑ · {comments:>3}c] {title}"
                + (f"\n    body excerpt: {selftext}" if selftext else "")
            )
        blocks.append("\n".join(lines))
    if total_posts == 0:
        return (
            f"<no Reddit posts found mentioning {ticker.upper()} across "
            f"{', '.join(f'r/{s}' for s in subreddits)} in the past 7 days>"
        )
    return "\n\n".join(blocks)


def fetch_stocktwits_messages(ticker: str, limit: int = 30, timeout: float = 10.0) -> dict:
    """Fetch recent StockTwits messages for ticker as structured dict."""
    base: dict = {
        "ticker": ticker.upper(),
        "bullish": 0, "bearish": 0, "unlabeled": 0, "total": 0,
        "bullish_pct": 0, "bearish_pct": 0,
        "messages": [],
    }
    url = _STOCKTWITS_API.format(ticker=ticker.upper())
    try:
        resp = requests.get(url, headers=_HTTP_HEADERS, timeout=_http_timeout(timeout))
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        logger.warning("StockTwits fetch failed for %s: %s", ticker, exc)
        base["error"] = f"stocktwits unavailable: {type(exc).__name__}"
        return base
    messages = data.get("messages", []) if isinstance(data, dict) else []
    if not messages:
        return base

    bullish = bearish = unlabeled = 0
    out: list = []
    for m in messages[:limit]:
        created = m.get("created_at", "")
        user = (m.get("user") or {}).get("username", "?")
        entities = m.get("entities") or {}
        sentiment_obj = entities.get("sentiment") or {}
        sentiment = sentiment_obj.get("basic") if isinstance(sentiment_obj, dict) else None
        body = (m.get("body") or "").replace("\n", " ").strip()
        if len(body) > 280:
            body = body[:280] + "…"
        if sentiment == "Bullish":
            bullish += 1
        elif sentiment == "Bearish":
            bearish += 1
        else:
            unlabeled += 1
        out.append({
            "created_at": created,
            "user": user,
            "sentiment": sentiment,
            "body": body,
        })
    total = bullish + bearish + unlabeled
    base.update({
        "bullish": bullish, "bearish": bearish, "unlabeled": unlabeled, "total": total,
        "bullish_pct": round(100 * bullish / total) if total else 0,
        "bearish_pct": round(100 * bearish / total) if total else 0,
        "messages": out,
    })
    return base
