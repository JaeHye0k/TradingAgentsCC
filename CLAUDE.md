# TradingAgentsCC

Multi-agent stock analysis powered entirely by Claude Code sub-agents.
No external LLM API key required — uses your Claude Code subscription.

## Prerequisites

```bash
pip install .
```

## Usage

```
/oh-my-claudecode:ticker CEG
/oh-my-claudecode:ticker AAPL --date 2026-05-01
```

## Project Structure

```
.claude/skills/ticker/SKILL.md   ← Orchestrator (spawns all sub-agents)
agents/                          ← Role prompts for each sub-agent
tools/                           ← Data fetching scripts
tools/lib.py                     ← Shared dataflow library (yfinance, stockstats)
```

## Architecture

```
/ticker <symbol>
  │
  ├─ Phase 1 (parallel):  market_analyst, news_analyst, fundamentals_analyst, social_analyst
  ├─ Phase 2 (sequential): bull_researcher → bear_researcher → research_manager
  ├─ Phase 3:              trader
  ├─ Phase 4 (parallel):  aggressive_risk, conservative_risk, neutral_risk
  └─ Phase 5:              portfolio_manager → final decision
```

## Data Sources

- Price & Technicals: yfinance (OHLCV, RSI, MACD, Bollinger Bands, SMA/EMA)
- News: yfinance News API + global macro queries
- Fundamentals: yfinance (income statement, balance sheet, cash flow)
- Sentiment: Reddit (wallstreetbets, stocks, investing) + StockTwits
