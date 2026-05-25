# TradingAgentsCC

**English** | [한국어](README.ko.md)

> Multi-agent stock analysis on Claude Code — no separate LLM API key required.

[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Based on TradingAgents](https://img.shields.io/badge/based%20on-TauricResearch%2FTradingAgents-orange)](https://github.com/TauricResearch/TradingAgents)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-7C3AED)](https://docs.claude.com/en/docs/claude-code/plugins)

---

## What is TradingAgentsCC?

**TradingAgentsCC** is a Claude-Code-native port of [TradingAgents](https://github.com/TauricResearch/TradingAgents) by [Tauric Research](https://github.com/TauricResearch). It runs a 12-agent stock-analysis pipeline — analysts, bull/bear researchers, a trader, three risk reviewers, and a portfolio manager — entirely as Claude Code sub-agents.

A single command (`/tradingagentscc:ticker AAPL`) fans the work out across five phases of parallel and sequential agent calls and produces a self-contained HTML report with interactive charts and a Markdown digest.

The pipeline mirrors the original TradingAgents architecture, but the orchestration layer has been rebuilt from LangGraph to Claude Code's native sub-agent dispatch.

## Why Claude Code?

| | Original [TradingAgents](https://github.com/TauricResearch/TradingAgents) | **TradingAgentsCC** |
|---|---|---|
| LLM access | Requires API keys (OpenAI, Anthropic, Google, …) | **Uses your Claude Code subscription — no extra API key** |
| Orchestration | LangGraph state machine | Claude Code sub-agent dispatch (native `Task` tool) |
| Install footprint | Python + LangGraph + chosen LLM SDKs | Python + yfinance only |
| Output | Logs + decision records | Bilingual HTML report (interactive charts) + Markdown |
| Bilingual | English | **Korean / English** via `--lang` |

**No separate LLM API key required.** Every LLM call in the pipeline goes through Claude Code itself, so a Claude Pro / Max / Team subscription is all you need.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/JaeHye0k/TradingAgentsCC
cd TradingAgentsCC

# 2. Install Python dependencies (yfinance, stockstats, pandas, …)
pip install .

# 3. Open Claude Code in this directory and run:
/tradingagentscc:ticker CEG
/tradingagentscc:ticker AAPL --date 2026-05-01 --lang en --format html
/tradingagentscc:ticker 005930 --rounds 2 --lang ko          # Korean ticker auto-suffixed to .KS
```

> The plugin reads `.claude/skills/ticker/SKILL.md` and `agents/*.md` from the repository root. Run the command from the project directory (or install it as a Claude Code plugin).

## Architecture

```
/tradingagentscc:ticker <symbol>
  │
  ├─ Step 1   Fetch data (parallel bash) ── market · news · fundamentals · sentiment
  │
  ├─ Phase 1  Analyst Team (parallel)   ── market · news · fundamentals · social
  ├─ Phase 2  Research Team (sequential)── bull ⇄ bear  (N debate rounds) → research_manager
  ├─ Phase 3  Trader                    ── investment plan → executable trade plan
  ├─ Phase 4  Risk Review (parallel)    ── aggressive · conservative · neutral
  └─ Phase 5  Portfolio Manager         ── final decision (Buy / Overweight / Hold / Underweight / Sell)
                │
                └─ Render → outputs/{DATE}_{TICKER}.html  +  outputs/{DATE}_{TICKER}.md
```

## Agents

| # | Agent | Role | Phase |
|---|---|---|---|
| 1 | `market_analyst` | Technical analysis — RSI, MACD, Bollinger Bands, SMA / EMA | 1 |
| 2 | `news_analyst` | Event-driven and macro context | 1 |
| 3 | `fundamentals_analyst` | Income statement, balance sheet, cash flow, valuation | 1 |
| 4 | `social_analyst` | Retail sentiment from Reddit + StockTwits | 1 |
| 5 | `bull_researcher` | Strongest bullish thesis | 2 |
| 6 | `bear_researcher` | Strongest bearish counter-thesis | 2 |
| 7 | `research_manager` | Synthesises the debate into a balanced recommendation | 2 |
| 8 | `trader` | Converts the plan into an executable trade strategy | 3 |
| 9 | `aggressive_risk` | Risk review with a return-maximising posture | 4 |
| 10 | `conservative_risk` | Risk review with a capital-preservation posture | 4 |
| 11 | `neutral_risk` | Risk review with a balanced posture | 4 |
| 12 | `portfolio_manager` | Final decision with entry / exit parameters | 5 |

Each agent is a single markdown prompt under `agents/`. Edit the file to change the agent's behaviour — no code change required.

## Tools & Data Sources

| Tool | Purpose |
|---|---|
| `tools/fetch_market.py` | Price history + technicals (yfinance, stockstats) |
| `tools/fetch_news.py` | Articles + insider transactions (yfinance News API) |
| `tools/fetch_fundamentals.py` | Income statement / balance sheet / cash flow (yfinance) |
| `tools/fetch_sentiment.py` | Reddit (r/wallstreetbets, r/stocks, r/investing) + StockTwits |
| `tools/format_agent_context.py` | Converts fetch JSON to per-agent markdown context blocks |
| `tools/render_html.py` | Interactive HTML report (Chart.js) |
| `tools/render_md.py` | Markdown report |

**Not used (by design):** FinnHub, Tushare, or any paid news API — the goal is a zero-cost-credentials install beyond Claude Code itself.

## Configuration & Flags

```
/tradingagentscc:ticker TICKER [--date YYYY-MM-DD] [--rounds N] [--format html|md|both] [--lang ko|en]
```

| Flag | Values | Default | Notes |
|---|---|---|---|
| `TICKER` | e.g. `AAPL`, `CEG`, `005930` | _required_ | 6-digit numbers are auto-suffixed to `.KS` (KRX) |
| `--date` | `YYYY-MM-DD` | Today | Analysis is anchored to this date (look-back window for prices/news) |
| `--rounds` | `1` / `2` / `3` | `1` | Bull ↔ Bear debate rounds. Higher = deeper, slower |
| `--format` | `html` / `md` / `both` | `both` | HTML includes interactive charts |
| `--lang` | `ko` / `en` | `ko` | Output language of the final report |

When a flag is omitted, the skill **asks you interactively** before running — it does **not** silently fill in defaults.

## Output Examples

After a run, look in `outputs/`:

```
outputs/
├── 2026-05-01_AAPL.html      # interactive report with price chart, indicators, debate transcript
└── 2026-05-01_AAPL.md        # plain-text digest for terminals / Git diffs
```

The HTML report's final block looks roughly like:

```
═══ Portfolio Manager — Final Decision ═══
Verdict:        Overweight
Conviction:     7 / 10
Entry:          $182 – $186
Stop Loss:      $174
Target (4w):    $205
Position Size:  3.5 % of portfolio
```

## FAQ

**Do I need an LLM API key?**
No. Every model call is routed through your Claude Code session, so a Claude Pro / Max / Team subscription is the only credential required. yfinance, Reddit, and StockTwits are accessed anonymously.

**Which markets are supported?**
Anything yfinance covers — US equities, ETFs, indices, and most international tickers. Korean tickers can be entered as a 6-digit code (`005930`) and the skill auto-suffixes `.KS`.

**Is this financial advice?**
**No.** TradingAgentsCC is an educational and research tool. It is not investment advice, and the authors accept no liability for trading decisions based on its output. Always do your own research.

**How is this different from the upstream TradingAgents?**
Same agent architecture, different runtime. See [`NOTICE`](./NOTICE) for the full list of modifications.

**Can I edit the agents?**
Yes. Each agent is a plain markdown prompt under `agents/`. Edit, save, run again.

## Attribution

This project is a derivative work of [**TradingAgents**](https://github.com/TauricResearch/TradingAgents) by **Tauric Research** (Yijia Xiao, Edward Sun, Di Luo, Wei Wang), licensed under Apache-2.0.

If you use this software in academic work, please cite the original paper:

```bibtex
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
  title         = {TradingAgents: Multi-Agents LLM Financial Trading Framework},
  author        = {Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
  year          = {2025},
  eprint        = {2412.20138},
  archivePrefix = {arXiv},
  primaryClass  = {q-fin.TR}
}
```

See [`NOTICE`](./NOTICE) for the complete attribution and the list of modifications from the original work.

## License

Licensed under the [**Apache License, Version 2.0**](./LICENSE). See [`NOTICE`](./NOTICE) for required attribution.
