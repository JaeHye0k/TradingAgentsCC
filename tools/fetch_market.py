"""Fetch price history and technical indicators for a ticker."""
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
        print("Usage: fetch_market.py <TICKER> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)

    setup()
    from tradingagents.dataflows.y_finance import get_YFin_data_online, get_stock_stats_indicators_window

    ticker = sys.argv[1].upper()
    date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.strptime(date, "%Y-%m-%d") - timedelta(days=90)).strftime("%Y-%m-%d")

    print(f"# Market Data: {ticker} as of {date}\n")

    # Price history
    print("## Price History (90 days)\n")
    try:
        print(get_YFin_data_online(ticker, start_date, date))
    except Exception as e:
        print(f"Error fetching price data: {e}")

    # Technical indicators
    print("\n## Technical Indicators\n")
    indicators = [
        ("close_50_sma", "50-day SMA"),
        ("close_200_sma", "200-day SMA"),
        ("close_10_ema", "10-day EMA"),
        ("rsi", "RSI (14)"),
        ("macd", "MACD"),
        ("macds", "MACD Signal"),
        ("macdh", "MACD Histogram"),
        ("boll", "Bollinger Middle"),
        ("boll_ub", "Bollinger Upper"),
        ("boll_lb", "Bollinger Lower"),
        ("atr", "ATR"),
    ]
    for key, label in indicators:
        try:
            data = get_stock_stats_indicators_window(ticker, key, date, 30)
            print(f"### {label}\n{data}\n")
        except Exception as e:
            print(f"### {label}\nUnavailable: {e}\n")

if __name__ == "__main__":
    main()
