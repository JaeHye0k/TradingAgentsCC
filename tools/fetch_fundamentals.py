"""Fetch fundamental financial data for a ticker as JSON."""
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import get_fundamentals, get_balance_sheet, get_cashflow, get_income_statement


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: fetch_fundamentals.py <TICKER> [YYYY-MM-DD]", file=sys.stderr)
        sys.exit(1)

    ticker = sys.argv[1].upper()
    date = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")

    result = {
        "ticker": ticker,
        "date": date,
        "fundamentals": get_fundamentals(ticker, date),
        "income_statement": get_income_statement(ticker, freq="quarterly", curr_date=date),
        "balance_sheet": get_balance_sheet(ticker, freq="quarterly", curr_date=date),
        "cashflow": get_cashflow(ticker, freq="quarterly", curr_date=date),
    }

    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
