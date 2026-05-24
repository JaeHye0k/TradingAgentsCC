"""Fetch news articles and insider transactions for a ticker as JSON."""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import get_news_yfinance, get_global_news_yfinance, get_insider_transactions


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: fetch_news.py <TICKER> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1].upper()
    date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")

    result = {
        "ticker": ticker,
        "date": date,
        "company_news_md": get_news_yfinance(ticker, start_date, date),
        "global_news_md": get_global_news_yfinance(date, look_back_days=7, limit=10),
        "insider_transactions": get_insider_transactions(ticker),
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
