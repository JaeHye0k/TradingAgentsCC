---
name: ticker
description: Multi-agent stock analysis using Claude Code sub-agents — no LLM API key required
argument-hint: "[TICKER] [--date YYYY-MM-DD] [--rounds N]"
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

**인수 파싱:**

`$ARGUMENTS`가 비어있거나 TICKER가 없으면, `AskUserQuestion` 도구로 아래 3가지를 한 번에 질문하세요:

```
질문 1 — "분석할 티커 심볼을 입력하세요 (예: CEG, AAPL, 005930.KS)"
  header: "티커 심볼"
  options: 없음 (자유 입력)

질문 2 — "기준 날짜를 선택하세요"
  header: "기준 날짜"
  options:
    - "오늘 ({TODAY})" → 오늘 날짜 사용
    - "직접 입력 (YYYY-MM-DD)" → 사용자 입력값 사용

질문 3 — "리서치팀 토론 라운드 수를 선택하세요"
  header: "토론 라운드"
  options:
    - "1라운드 — 빠른 분석 (권장)" → DEBATE_ROUNDS = 1
    - "2라운드 — 균형 잡힌 분석" → DEBATE_ROUNDS = 2
    - "3라운드 — 심층 분석" → DEBATE_ROUNDS = 3
```

`$ARGUMENTS`가 있으면 파싱:
- 첫 번째 토큰 = TICKER (대문자 변환)
- `--date YYYY-MM-DD` → DATE (없으면 오늘 날짜)
- `--rounds N` → DEBATE_ROUNDS (없으면 1)

설정값을 확정한 뒤 출력:
```
🔍 분석 설정
  티커: {TICKER}
  기준일: {DATE}
  토론 라운드: {DEBATE_ROUNDS}회
```

Set `PROJECT_ROOT` = the directory containing this SKILL.md file's project (e.g., `~/TradingAgentsCC`).

Verify the data library is available:
```bash
python -c "from tools.lib import get_YFin_data_online; print('OK')"
```
If this fails, print: `ERROR: Dependencies not installed. Run: pip install .` and stop.

---

### Step 1: Fetch All Data (Parallel Bash)

Run all four fetch scripts **simultaneously** (parallel Bash calls):

```bash
python $PROJECT_ROOT/tools/fetch_market.py {TICKER} {DATE}
python $PROJECT_ROOT/tools/fetch_news.py {TICKER} {DATE}
python $PROJECT_ROOT/tools/fetch_fundamentals.py {TICKER} {DATE}
python $PROJECT_ROOT/tools/fetch_sentiment.py {TICKER} {DATE}
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

### Step 3: Phase 2 — Research Team (Multi-Round Debate)

Combine all Phase 1 reports:
```
ALL_ANALYST_REPORTS = MARKET_REPORT + "\n\n---\n\n" + NEWS_REPORT + "\n\n---\n\n" + FUNDAMENTALS_REPORT + "\n\n---\n\n" + SENTIMENT_REPORT
```

Read agent prompt files:
- `$PROJECT_ROOT/agents/bull_researcher.md` → `bull_researcher_prompt`
- `$PROJECT_ROOT/agents/bear_researcher.md` → `bear_researcher_prompt`
- `$PROJECT_ROOT/agents/research_manager.md` → `research_manager_prompt`

Replace `{TICKER}` and `{DATE}` in all prompts.

**다중 라운드 토론 루프 (`DEBATE_ROUNDS`회 반복):**

초기값: `PREV_BULL = ""`, `PREV_BEAR = ""`

각 라운드 R = 1, 2, ..., DEBATE_ROUNDS:

Print: `🔄 토론 라운드 {R}/{DEBATE_ROUNDS} 진행 중...`

  **Bull Researcher** (spawn Agent, wait):
  ```
  prompt = bull_researcher_prompt
          + "\n\n---\n\n## 애널리스트 보고서\n\n" + ALL_ANALYST_REPORTS
          + (R > 1 이면: "\n\n---\n\n## 이전 라운드 Bear 주장 (반박 대상)\n\n" + PREV_BEAR)
  ```
  → `BULL_REPORTS[R]` 에 저장

  **Bear Researcher** (spawn Agent, wait):
  ```
  prompt = bear_researcher_prompt
          + "\n\n---\n\n## 애널리스트 보고서\n\n" + ALL_ANALYST_REPORTS
          + "\n\n---\n\n## 이번 라운드 Bull 주장 (반박 대상)\n\n" + BULL_REPORTS[R]
  ```
  → `BEAR_REPORTS[R]` 에 저장

  `PREV_BULL = BULL_REPORTS[R]`, `PREV_BEAR = BEAR_REPORTS[R]`

**Research Manager** — 최종 라운드 결과로 합성 (spawn Agent, wait):
```
prompt = research_manager_prompt
        + "\n\n---\n\n## 전체 토론 요약 ({DEBATE_ROUNDS}라운드)\n\n"
        + (각 라운드 Bull/Bear 보고서를 "### 라운드 N Bull\n...\n### 라운드 N Bear\n..." 형식으로 전부 포함)
```
Store result as `INVESTMENT_PLAN`.

Print: `✓ Phase 2 complete — {DEBATE_ROUNDS}라운드 토론 완료`

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

### Step 7: Generate HTML Report

**trading_checklist 추출:** TRADING_PLAN 텍스트에서 구체적인 행동 항목을 최대 10개 배열로 추출하세요.  
예시: `["RSI 60 이하 진입 확인", "1차 목표가 $210 설정", "손절선 $185 설정"]`

**decision_reasons 추출:** FINAL_DECISION 텍스트에서 핵심 근거를 최대 8개 배열로 추출하세요.  
예시: `["강한 기술적 모멘텀", "견조한 매출 성장", "AI 사업 확장"]`

**JSON 페이로드 저장** — Write 도구로 `/tmp/tradingagentscc_report_{TICKER}.json`에 저장:

```json
{
  "ticker": "{TICKER}",
  "date": "{DATE}",
  "market_data": "(MARKET_DATA 전체 텍스트)",
  "sentiment_data": "(SENTIMENT_DATA 전체 텍스트)",
  "reports": {
    "market": "(MARKET_REPORT)",
    "news": "(NEWS_REPORT)",
    "fundamentals": "(FUNDAMENTALS_REPORT)",
    "social": "(SENTIMENT_REPORT)",
    "bull": ["(BULL_REPORTS[1])", "(BULL_REPORTS[2])", "..."],
    "bear": ["(BEAR_REPORTS[1])", "(BEAR_REPORTS[2])", "..."],
    "investment_plan": "(INVESTMENT_PLAN)",
    "trading_plan": "(TRADING_PLAN)",
    "aggressive_risk": "(AGGRESSIVE_RISK)",
    "conservative_risk": "(CONSERVATIVE_RISK)",
    "neutral_risk": "(NEUTRAL_RISK)",
    "final_decision": "(FINAL_DECISION)",
    "trading_checklist": ["추출된 항목 배열"],
    "decision_reasons": ["추출된 근거 배열"]
  }
}
```

**HTML 생성** — Bash 도구로 실행:

```bash
python {PROJECT_ROOT}/tools/generate_report.py \
  /tmp/tradingagentscc_report_{TICKER}.json \
  {PROJECT_ROOT}/outputs/{DATE}_{TICKER}.html
```

성공 시 출력:
```
✅ 보고서 저장됨: outputs/{DATE}_{TICKER}.html
브라우저에서 열기: open outputs/{DATE}_{TICKER}.html
```

실패(non-zero exit) 시 — 폴백으로 아래 마크다운 형식 출력:

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

## 🔬 Phase 2: Research Team Debate ({DEBATE_ROUNDS}라운드)

{각 라운드별 BULL_REPORTS[R] / BEAR_REPORTS[R] 을 순서대로 출력}

### Research Manager 최종 합성
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
