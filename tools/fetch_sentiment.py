"""Fetch social sentiment data for a ticker."""
import sys
import os
from datetime import datetime

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
        print("Usage: fetch_sentiment.py <TICKER> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)

    setup()

    ticker = sys.argv[1].upper()
    date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")

    print(f"# Social Sentiment: {ticker} as of {date}\n")

    # Reddit
    print("## Reddit Sentiment\n")
    try:
        from tradingagents.dataflows.reddit import fetch_reddit_posts
        print(fetch_reddit_posts(ticker))
    except Exception as e:
        print(f"Reddit data unavailable: {e}")

    # StockTwits
    print("\n## StockTwits Sentiment\n")
    try:
        from tradingagents.dataflows.stocktwits import fetch_stocktwits_messages
        print(fetch_stocktwits_messages(ticker))
    except Exception as e:
        print(f"StockTwits data unavailable: {e}")

if __name__ == "__main__":
    main()
