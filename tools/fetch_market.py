"""Fetch price history and technical indicators for a ticker as JSON."""
import json
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import get_YFin_data_online, get_stock_stats_indicators_window

INDICATORS = [
    "close_50_sma", "close_200_sma", "close_10_ema",
    "rsi", "macd", "macds", "macdh",
    "boll", "boll_ub", "boll_lb", "atr",
]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: fetch_market.py <TICKER> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1].upper()
    date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")

    result = {
        "ticker": ticker,
        "date": date,
        "price_history": get_YFin_data_online(ticker, start_date, date),
        "indicators": {},
    }

    for key in INDICATORS:
        try:
            result["indicators"][key] = get_stock_stats_indicators_window(ticker, key, date, 30)
        except Exception as e:
            result["indicators"][key] = {
                "indicator": key, "symbol": ticker,
                "error": f"Unavailable: {e}",
                "dates": [], "values": [],
            }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
