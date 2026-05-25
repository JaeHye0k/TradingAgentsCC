"""Convert fetch_*.py JSON output to markdown strings for sub-agent context.

The markdown produced here is meant to be the LLM-facing equivalent of the
old fetch_*.py stdout, so existing `agents/*.md` prompts continue to work
without modification.

Usage:
    python format_agent_context.py <kind> <input.json>

Where <kind> is one of: market, news, fundamentals, sentiment.
The resulting markdown is written to stdout.
"""
from __future__ import annotations

import json
import sys
from typing import Any

INDICATOR_LABELS: list[tuple[str, str]] = [
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


def _fmt_num(v: Any) -> str:
    return "" if v is None else f"{v}"


def _fmt_int(v: Any) -> str:
    return "" if v is None else f"{int(v)}"


def _format_price_history(ph: dict) -> str:
    if ph.get("error"):
        return f"{ph['error']}\n"
    header = (
        f"# Stock data for {ph['symbol']} from {ph['start_date']} to {ph['end_date']}\n"
        f"# Total records: {ph.get('records', 0)}\n"
        f"# Data retrieved on: {ph.get('retrieved_at', '')}\n\n"
    )
    if not ph.get("dates"):
        return header + f"No data found for symbol '{ph['symbol']}' between {ph['start_date']} and {ph['end_date']}\n"
    lines = ["Date,Open,High,Low,Close,Volume"]
    for i, d in enumerate(ph["dates"]):
        lines.append(",".join([
            d,
            _fmt_num(ph["open"][i] if i < len(ph["open"]) else None),
            _fmt_num(ph["high"][i] if i < len(ph["high"]) else None),
            _fmt_num(ph["low"][i] if i < len(ph["low"]) else None),
            _fmt_num(ph["close"][i] if i < len(ph["close"]) else None),
            _fmt_int(ph["volume"][i] if i < len(ph["volume"]) else None),
        ]))
    return header + "\n".join(lines) + "\n"


def _format_indicator(label: str, ind: dict) -> str:
    out = [f"### {label}\n"]
    if ind.get("error"):
        out.append(f"Unavailable: {ind['error']}\n\n")
        return "".join(out)
    out.append(
        f"## {ind['indicator']} values from {ind['start_date']} to {ind['end_date']}:\n\n"
    )
    pairs = list(zip(ind.get("dates", []), ind.get("values", [])))
    for d, v in reversed(pairs):
        if v is None:
            out.append(f"{d}: N/A: Not a trading day (weekend or holiday)\n")
        else:
            out.append(f"{d}: {v}\n")
    out.append("\n\n" + ind.get("description", "") + "\n\n")
    return "".join(out)


def format_market_md(market_json: dict) -> str:
    ticker = market_json["ticker"]
    date = market_json["date"]
    out = [f"# Market Data: {ticker} as of {date}\n\n"]
    out.append("## Price History (90 days)\n\n")
    out.append(_format_price_history(market_json["price_history"]))
    out.append("\n## Technical Indicators\n\n")
    indicators = market_json.get("indicators", {})
    for key, label in INDICATOR_LABELS:
        if key in indicators:
            out.append(_format_indicator(label, indicators[key]))
    return "".join(out)


def _format_insider(ins: dict) -> str:
    if ins.get("error"):
        return f"{ins['error']}\n"
    if not ins.get("transactions"):
        return f"No insider transactions data found for symbol '{ins['ticker']}'\n"
    cols = ins.get("columns") or list(ins["transactions"][0].keys())
    header = (
        f"# Insider Transactions data for {ins['ticker']}\n"
        f"# Data retrieved on: {ins.get('retrieved_at', '')}\n\n"
    )
    rows = [",".join(cols)]
    for tx in ins["transactions"]:
        rows.append(",".join("" if tx.get(c) is None else str(tx.get(c)) for c in cols))
    return header + "\n".join(rows) + "\n"


def format_news_md(news_json: dict) -> str:
    ticker = news_json["ticker"]
    date = news_json["date"]
    out = [f"# News & Events: {ticker} as of {date}\n\n"]
    out.append("## Recent Company News\n\n")
    out.append(news_json.get("company_news_md", "") + "\n\n")
    out.append("## Global Macro News\n\n")
    out.append(news_json.get("global_news_md", "") + "\n\n")
    out.append("## Insider Transactions\n\n")
    out.append(_format_insider(news_json.get("insider_transactions", {})))
    return "".join(out)


def _format_fundamentals_block(f: dict) -> str:
    if f.get("error"):
        return f["error"] + "\n"
    lines = [
        f"# Company Fundamentals for {f['ticker']}",
        f"# Data retrieved on: {f.get('retrieved_at', '')}",
        "",
    ]
    for label, value in f.get("fields", {}).items():
        lines.append(f"{label}: {value}")
    return "\n".join(lines) + "\n"


def _format_statement(s: dict, name_pretty: str) -> str:
    if s.get("error"):
        return s["error"] + "\n"
    if not s.get("rows"):
        return f"No {name_pretty.lower()} data found for symbol '{s['ticker']}'\n"
    out = [
        f"# {name_pretty} data for {s['ticker']} ({s.get('freq', 'quarterly')})",
        f"# Data retrieved on: {s.get('retrieved_at', '')}",
        "",
    ]
    out.append("," + ",".join(s.get("periods", [])))
    for row in s.get("rows", []):
        vals = ["" if v is None else str(v) for v in row.get("values", [])]
        out.append(row["label"] + "," + ",".join(vals))
    return "\n".join(out) + "\n"


def format_fundamentals_md(fund_json: dict) -> str:
    ticker = fund_json["ticker"]
    date = fund_json["date"]
    out = [f"# Fundamental Data: {ticker} as of {date}\n\n"]
    out.append("## Key Metrics\n\n")
    out.append(_format_fundamentals_block(fund_json.get("fundamentals", {})))
    out.append("\n## Income Statement (Quarterly)\n\n")
    out.append(_format_statement(fund_json.get("income_statement", {}), "Income Statement"))
    out.append("\n## Balance Sheet (Quarterly)\n\n")
    out.append(_format_statement(fund_json.get("balance_sheet", {}), "Balance Sheet"))
    out.append("\n## Cash Flow (Quarterly)\n\n")
    out.append(_format_statement(fund_json.get("cashflow", {}), "Cash Flow"))
    return "".join(out)


def _format_stocktwits(st: dict) -> str:
    if st.get("error"):
        kind = st["error"].split(":", 1)[-1].strip() if ":" in st["error"] else st["error"]
        return f"<stocktwits unavailable: {kind}>\n"
    if not st.get("messages"):
        return f"<no StockTwits messages found for ${st['ticker']}>\n"
    summary = (
        f"Bullish: {st['bullish']} ({st['bullish_pct']}%) · "
        f"Bearish: {st['bearish']} ({st['bearish_pct']}%) · "
        f"Unlabeled: {st['unlabeled']} · "
        f"Total: {st['total']} most-recent messages"
    )
    lines = [summary, ""]
    for m in st["messages"]:
        tag = m["sentiment"] if m.get("sentiment") else "no-label"
        lines.append(f"[{m['created_at']} · @{m['user']} · {tag}] {m['body']}")
    return "\n".join(lines) + "\n"


def format_sentiment_md(sent_json: dict) -> str:
    ticker = sent_json["ticker"]
    date = sent_json["date"]
    out = [f"# Social Sentiment: {ticker} as of {date}\n\n"]
    out.append("## Reddit Sentiment\n\n")
    out.append(sent_json.get("reddit_md", "") + "\n\n")
    out.append("## StockTwits Sentiment\n\n")
    out.append(_format_stocktwits(sent_json.get("stocktwits", {})))
    return "".join(out)


FORMATTERS = {
    "market": format_market_md,
    "news": format_news_md,
    "fundamentals": format_fundamentals_md,
    "sentiment": format_sentiment_md,
}


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[1] not in FORMATTERS:
        print(
            "Usage: format_agent_context.py <market|news|fundamentals|sentiment> <input.json>",
            file=sys.stderr,
        )
        sys.exit(1)
    kind, path = sys.argv[1], sys.argv[2]
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    sys.stdout.write(FORMATTERS[kind](data))


if __name__ == "__main__":
    main()
