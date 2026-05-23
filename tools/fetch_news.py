"""Fetch news articles and insider transactions for a ticker."""
import sys
import os
from datetime import datetime, timedelta

def setup():
    ta_path = os.path.expanduser("~/TradingAgents")
    if ta_path not in sys.path:
        sys.path.insert(0, ta_path)
    from tradingagents.default_config import DEFAULT_CONFIG
    try:
        from tradingagents.dataflows.config import set_config
        set_config(DEFAULT_CONFIG)
    except Exception:
        pass

def main():
    if len(sys.argv) < 2:
        print("Usage: fetch_news.py <TICKER> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)

    setup()
    from tradingagents.dataflows.yfinance_news import get_news_yfinance, get_global_news_yfinance
    from tradingagents.dataflows.y_finance import get_insider_transactions

    ticker = sys.argv[1].upper()
    date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")

    print(f"# News & Events: {ticker} as of {date}\n")

    # Company news
    print("## Recent Company News\n")
    try:
        print(get_news_yfinance(ticker, start_date, date))
    except Exception as e:
        print(f"Error fetching news: {e}")

    # Global macro news
    print("\n## Global Macro News\n")
    try:
        print(get_global_news_yfinance(date, look_back_days=7, limit=10))
    except Exception as e:
        print(f"Error fetching global news: {e}")

    # Insider transactions
    print("\n## Insider Transactions\n")
    try:
        print(get_insider_transactions(ticker))
    except Exception as e:
        print(f"Error fetching insider transactions: {e}")

if __name__ == "__main__":
    main()
