"""Fetch social sentiment data for a ticker as JSON."""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import fetch_reddit_posts, fetch_stocktwits_messages


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: fetch_sentiment.py <TICKER> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1].upper()
    date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")

    result = {
        "ticker": ticker,
        "date": date,
        "reddit_md": fetch_reddit_posts(ticker),
        "stocktwits": fetch_stocktwits_messages(ticker),
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
