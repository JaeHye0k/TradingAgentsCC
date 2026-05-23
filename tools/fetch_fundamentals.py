"""Fetch fundamental financial data for a ticker."""
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
        print("Usage: fetch_fundamentals.py <TICKER> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)

    setup()
    from tradingagents.dataflows.y_finance import (
        get_fundamentals,
        get_balance_sheet,
        get_cashflow,
        get_income_statement,
    )

    ticker = sys.argv[1].upper()
    date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")

    print(f"# Fundamental Data: {ticker} as of {date}\n")

    print("## Key Metrics\n")
    try:
        print(get_fundamentals(ticker, date))
    except Exception as e:
        print(f"Error fetching fundamentals: {e}")

    print("\n## Income Statement (Quarterly)\n")
    try:
        print(get_income_statement(ticker, freq="quarterly", curr_date=date))
    except Exception as e:
        print(f"Error fetching income statement: {e}")

    print("\n## Balance Sheet (Quarterly)\n")
    try:
        print(get_balance_sheet(ticker, freq="quarterly", curr_date=date))
    except Exception as e:
        print(f"Error fetching balance sheet: {e}")

    print("\n## Cash Flow (Quarterly)\n")
    try:
        print(get_cashflow(ticker, freq="quarterly", curr_date=date))
    except Exception as e:
        print(f"Error fetching cash flow: {e}")

if __name__ == "__main__":
    main()
