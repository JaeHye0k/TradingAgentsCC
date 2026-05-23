---
name: ticker
description: Multi-agent stock analysis using Claude Code sub-agents — no LLM API key required
argument-hint: "<TICKER> [--date YYYY-MM-DD]"
triggers:
  - analyze ticker
  - stock analysis
  - 종목 분석
  - 주식 분석
  - ticker analysis
level: 4
---

# Ticker Analysis

Runs a full multi-agent stock analysis pipeline for a given ticker symbol.
All agents are Claude Code sub-agents — no external LLM API key required.

## Execution Instructions

Follow these phases exactly when invoked.

---

### Step 0: Parse Arguments & Setup

Parse `$ARGUMENTS`:
- First token = TICKER symbol (uppercase)
- If `--date YYYY-MM-DD` is present, use that date; otherwise use today's date

Set `PROJECT_ROOT` = the directory containing this SKILL.md file's project (e.g., `~/TradingAgentsCC`).

Verify the `tradingagents` package is available:
```bash
conda run -n tradingagents python -c "from tradingagents.dataflows.y_finance import get_YFin_data_online; print('OK')"
```
If this fails, print: `ERROR: tradingagents conda env not found. Run: conda activate tradingagents && pip install -e ~/TradingAgents` and stop.

Set `PYTHON = conda run -n tradingagents python` for all subsequent script calls.

---

### Step 1: Fetch All Data (Parallel Bash)

Run all four fetch scripts **simultaneously** (parallel Bash calls):

```bash
conda run -n tradingagents python $PROJECT_ROOT/tools/fetch_market.py {TICKER} {DATE}
conda run -n tradingagents python $PROJECT_ROOT/tools/fetch_news.py {TICKER} {DATE}
conda run -n tradingagents python $PROJECT_ROOT/tools/fetch_fundamentals.py {TICKER} {DATE}
conda run -n tradingagents python $PROJECT_ROOT/tools/fetch_sentiment.py {TICKER} {DATE}
```

Store each output as:
- `MARKET_DATA` ← output of fetch_market.py
- `NEWS_DATA` ← output of fetch_news.py
- `FUNDAMENTALS_DATA` ← output of fetch_fundamentals.py
- `SENTIMENT_DATA` ← output of fetch_sentiment.py

Print: `✓ Data fetched for {TICKER} as of {DATE}`

---

### Step 2: Phase 1 — Analyst Team (Parallel Agents)

Read all four agent prompt files **simultaneously**:
- `$PROJECT_ROOT/agents/market_analyst.md`
- `$PROJECT_ROOT/agents/news_analyst.md`
- `$PROJECT_ROOT/agents/fundamentals_analyst.md`
- `$PROJECT_ROOT/agents/social_analyst.md`

Replace `{TICKER}` and `{DATE}` placeholders in each prompt with actual values.

Then spawn all four agents **in parallel** using the Agent tool (single message, four tool calls):

**Market Analyst Agent:**
```
prompt = market_analyst_prompt + "\n\n---\n\n" + MARKET_DATA
subagent_type = "claude"
description = "Market technical analysis for {TICKER}"
```

**News Analyst Agent:**
```
prompt = news_analyst_prompt + "\n\n---\n\n" + NEWS_DATA
subagent_type = "claude"
description = "News and events analysis for {TICKER}"
```

**Fundamentals Analyst Agent:**
```
prompt = fundamentals_analyst_prompt + "\n\n---\n\n" + FUNDAMENTALS_DATA
subagent_type = "claude"
description = "Fundamental financial analysis for {TICKER}"
```

**Social Analyst Agent:**
```
prompt = social_analyst_prompt + "\n\n---\n\n" + SENTIMENT_DATA
subagent_type = "claude"
description = "Social sentiment analysis for {TICKER}"
```

Wait for all four to complete. Store results as:
- `MARKET_REPORT`, `NEWS_REPORT`, `FUNDAMENTALS_REPORT`, `SENTIMENT_REPORT`

Print: `✓ Phase 1 complete — 4 analyst reports generated`

---

### Step 3: Phase 2 — Research Team (Sequential)

Combine all Phase 1 reports:
```
ALL_ANALYST_REPORTS = MARKET_REPORT + "\n\n---\n\n" + NEWS_REPORT + "\n\n---\n\n" + FUNDAMENTALS_REPORT + "\n\n---\n\n" + SENTIMENT_REPORT
```

**3a. Bull Researcher** (spawn Agent, wait for result):
```
prompt = bull_researcher_prompt (from agents/bull_researcher.md, {TICKER}/{DATE} replaced)
        + "\n\n---\n\n## All Analyst Reports\n\n" + ALL_ANALYST_REPORTS
```
Store result as `BULL_REPORT`.

**3b. Bear Researcher** (spawn Agent, wait for result):
```
prompt = bear_researcher_prompt (from agents/bear_researcher.md, {TICKER}/{DATE} replaced)
        + "\n\n---\n\n## All Analyst Reports\n\n" + ALL_ANALYST_REPORTS
```
Store result as `BEAR_REPORT`.

**3c. Research Manager** (spawn Agent, wait for result):
```
prompt = research_manager_prompt (from agents/research_manager.md, {TICKER}/{DATE} replaced)
        + "\n\n---\n\n## Bull Case\n\n" + BULL_REPORT
        + "\n\n---\n\n## Bear Case\n\n" + BEAR_REPORT
```
Store result as `INVESTMENT_PLAN`.

Print: `✓ Phase 2 complete — research debate resolved`

---

### Step 4: Phase 3 — Trader

Spawn one Agent (wait for result):
```
prompt = trader_prompt (from agents/trader.md, {TICKER}/{DATE} replaced)
        + "\n\n---\n\n## Investment Plan\n\n" + INVESTMENT_PLAN
        + "\n\n---\n\n## Analyst Context\n\n" + ALL_ANALYST_REPORTS
```
Store result as `TRADING_PLAN`.

Print: `✓ Phase 3 complete — trading plan created`

---

### Step 5: Phase 4 — Risk Management (Parallel Agents)

Build shared context:
```
FULL_CONTEXT = ALL_ANALYST_REPORTS + "\n\n---\n\n" + INVESTMENT_PLAN + "\n\n---\n\n" + TRADING_PLAN
```

Spawn three agents **in parallel**:

**Aggressive Risk Agent:**
```
prompt = aggressive_risk_prompt (agents/aggressive_risk.md) + "\n\n---\n\n" + FULL_CONTEXT
```

**Conservative Risk Agent:**
```
prompt = conservative_risk_prompt (agents/conservative_risk.md) + "\n\n---\n\n" + FULL_CONTEXT
```

**Neutral Risk Agent:**
```
prompt = neutral_risk_prompt (agents/neutral_risk.md) + "\n\n---\n\n" + FULL_CONTEXT
```

Wait for all three. Store as `AGGRESSIVE_RISK`, `CONSERVATIVE_RISK`, `NEUTRAL_RISK`.

Print: `✓ Phase 4 complete — risk assessments done`

---

### Step 6: Phase 5 — Portfolio Manager (Final Decision)

Spawn one Agent (wait for result):
```
prompt = portfolio_manager_prompt (agents/portfolio_manager.md, {TICKER}/{DATE} replaced)
        + "\n\n---\n\n## Analyst Reports\n\n" + ALL_ANALYST_REPORTS
        + "\n\n---\n\n## Investment Plan\n\n" + INVESTMENT_PLAN
        + "\n\n---\n\n## Trading Plan\n\n" + TRADING_PLAN
        + "\n\n---\n\n## Risk Assessments\n\n### Aggressive\n" + AGGRESSIVE_RISK
        + "\n\n### Conservative\n" + CONSERVATIVE_RISK
        + "\n\n### Neutral\n" + NEUTRAL_RISK
```
Store result as `FINAL_DECISION`.

---

### Step 7: Assemble & Output Final Report

Print the complete markdown report in this order:

```markdown
# TradingAgentsCC Analysis: {TICKER}
**Date**: {DATE} | **Generated by**: Claude Code Multi-Agent System

---

## 📊 Phase 1: Analyst Team

{MARKET_REPORT}

---

{NEWS_REPORT}

---

{FUNDAMENTALS_REPORT}

---

{SENTIMENT_REPORT}

---

## 🔬 Phase 2: Research Team

### Bull Case
{BULL_REPORT}

### Bear Case
{BEAR_REPORT}

### Research Manager Synthesis
{INVESTMENT_PLAN}

---

## 💹 Phase 3: Trading Plan

{TRADING_PLAN}

---

## ⚖️ Phase 4: Risk Management

### Aggressive Perspective
{AGGRESSIVE_RISK}

### Conservative Perspective
{CONSERVATIVE_RISK}

### Neutral Perspective
{NEUTRAL_RISK}

---

## 🎯 Phase 5: Final Decision

{FINAL_DECISION}
```
