---
name: ticker
description: Multi-agent stock analysis using Claude Code sub-agents — no LLM API key required
argument-hint: "[TICKER] [--date YYYY-MM-DD] [--rounds N] [--format html|md|both] [--lang ko|en]"
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

### Step 0: Parse Arguments & Confirm Settings

> **⚠️ 필수 규칙 (절대 위반 금지):**
> 사용자가 **명시적 플래그로 지정하지 않은** 모든 설정값은 반드시 `AskUserQuestion`으로 확인받습니다.
> 인수가 일부만 주어졌더라도, 임의로 기본값(오늘 날짜, 1라운드 등)을 가정해서 진행하지 마세요.
> 이 규칙은 Step 1로 진행하기 전에 **무조건** 충족되어야 합니다.

**1) 인수 토큰화**

`$ARGUMENTS`를 파싱하여 다음 4가지 변수를 결정합니다:

| 변수 | 출처 | 미지정 시 |
|------|------|-----------|
| `TICKER` | 첫 번째 비플래그 토큰 (대문자 변환) | `TICKER_GIVEN = false` |
| `DATE` | `--date YYYY-MM-DD` 플래그 값 | `DATE_GIVEN = false` |
| `DEBATE_ROUNDS` | `--rounds N` 플래그 값 | `ROUNDS_GIVEN = false` |
| `FORMAT` | `--format html\|md\|both` 플래그 값 | `FORMAT_GIVEN = false` |
| `LANG` | `--lang ko\|en` 플래그 값 | `LANG_GIVEN = false` |

**2) 누락된 설정값 일괄 질문**

`TICKER_GIVEN`, `DATE_GIVEN`, `ROUNDS_GIVEN`, `FORMAT_GIVEN`, `LANG_GIVEN` **중 하나라도 false면**, 누락된 항목만 골라 `AskUserQuestion` **단일 호출**로 한꺼번에 물어봅니다.

> 모든 플래그(`<티커> --date ... --rounds ...`)가 명시된 경우에만 질문을 건너뛸 수 있습니다.

**질문 1 — `TICKER_GIVEN = false`일 때만:**
```
question: "분석할 티커 심볼을 입력하세요 (예: CEG, AAPL, 005930.KS)"
header:   "티커 심볼"
options:  자유 입력 (사용자가 'Other'로 직접 입력)
```

**질문 2 — `DATE_GIVEN = false`일 때만:**
```
question: "기준 날짜를 선택하세요"
header:   "기준 날짜"
options:
  - "오늘 ({TODAY})"        → 오늘 날짜 사용
  - "직접 입력 (YYYY-MM-DD)" → 사용자 입력값 사용
```

**질문 3 — `ROUNDS_GIVEN = false`일 때만:**
```
question: "리서치팀 토론 라운드 수를 선택하세요"
header:   "토론 라운드"
options:
  - "1라운드 — 빠른 분석 (권장)" → DEBATE_ROUNDS = 1
  - "2라운드 — 균형 잡힌 분석"   → DEBATE_ROUNDS = 2
  - "3라운드 — 심층 분석"        → DEBATE_ROUNDS = 3
```

**질문 4 — `FORMAT_GIVEN = false`일 때만:**
```
question: "보고서 출력 형식을 선택하세요"
header:   "출력 형식"
options:
  - "HTML + Markdown 둘 다 (권장)" → FORMAT = "both"
  - "HTML — 인터랙티브 차트 포함"  → FORMAT = "html"
  - "Markdown — 텍스트 보고서"     → FORMAT = "md"
```

**질문 5 — `LANG_GIVEN = false`일 때만:**
```
question: "보고서 출력 언어를 선택하세요"
header:   "출력 언어"
options:
  - "한국어 (권장)" → LANG = "ko"
  - "English"      → LANG = "en"
```

**3) 한국 종목 코드 자동 보정**

`TICKER`가 6자리 숫자(예: `005930`)인 경우 → `005930.KS`로 자동 변환 후 사용자에게 알립니다.

**4) 설정값 확정 출력**

```
🔍 분석 설정
  티커: {TICKER}
  기준일: {DATE}
  토론 라운드: {DEBATE_ROUNDS}회
  출력 형식: {FORMAT}
  출력 언어: {LANG}
```

**5) 언어 지시문(`LANG_INSTRUCTION`) 준비**

`LANG` 값에 따라 다음 텍스트를 `LANG_INSTRUCTION` 변수에 저장합니다. 이 텍스트는 이후 Step 2~6에서 모든 sub-agent 프롬프트 끝에 부착됩니다.

`LANG = "ko"`인 경우 (한국어):
```
**언어 지시**: 모든 분석 내용과 출력을 **한국어**로 작성하세요.
- 전문 용어(RSI, MACD, Forward PE, PEG, ATR, Bollinger Band, EBITDA, FCF, ROE, EPS, HBM, DRAM 등)는 영어 원형을 그대로 유지하세요.
- 숫자와 티커 심볼은 그대로 유지하세요.
- 섹션명(Executive Summary → 핵심 요약, Technical Verdict → 기술적 판정, Decision Rationale → 결정 근거, Risk/Reward Summary → 리스크/보상 요약, Key Catalysts → 주요 촉매, Supporting Evidence → 근거, Investment Thesis → 투자 논거, Approved Trade Parameters → 승인된 거래 파라미터, Bull Case / Bear Case → 강세 시나리오 / 약세 시나리오 등)은 **반드시 한국어로 번역**하세요.
```

`LANG = "en"`인 경우 (영어):
```
**Language Instruction**: Write all analysis content and output in **English**. Use standard professional financial terminology. Keep ticker symbols and numbers as-is. Keep section names in English exactly as shown in the Output Format template.
```

Set `PROJECT_ROOT` = the directory containing this SKILL.md file's project (e.g., `~/TradingAgentsCC`).

Verify the data library is available:
```bash
python -c "from tools.lib import get_YFin_data_online; print('OK')"
```
If this fails, print: `ERROR: Dependencies not installed. Run: pip install .` and stop.

---

### Step 1: Fetch All Data (Parallel Bash)

Each fetch script now emits **a single JSON object** on stdout. Pipe each to a per-ticker temp file so downstream steps can load them without re-running yfinance.

Run all four fetch scripts **simultaneously** (parallel Bash calls):

```bash
python $PROJECT_ROOT/tools/fetch_market.py       {TICKER} {DATE} > /tmp/tac_{TICKER}_market.json
python $PROJECT_ROOT/tools/fetch_news.py         {TICKER} {DATE} > /tmp/tac_{TICKER}_news.json
python $PROJECT_ROOT/tools/fetch_fundamentals.py {TICKER} {DATE} > /tmp/tac_{TICKER}_fundamentals.json
python $PROJECT_ROOT/tools/fetch_sentiment.py    {TICKER} {DATE} > /tmp/tac_{TICKER}_sentiment.json
```

Store file paths as:
- `MARKET_JSON_PATH`        = `/tmp/tac_{TICKER}_market.json`
- `NEWS_JSON_PATH`          = `/tmp/tac_{TICKER}_news.json`
- `FUNDAMENTALS_JSON_PATH`  = `/tmp/tac_{TICKER}_fundamentals.json`
- `SENTIMENT_JSON_PATH`     = `/tmp/tac_{TICKER}_sentiment.json`

Print: `✓ Data fetched for {TICKER} as of {DATE}`

---

### Step 1.5: Format Agent Context (Parallel Bash)

Each sub-agent expects a markdown context block in the same shape the old fetch scripts produced. Generate those with `format_agent_context.py` (parallel Bash calls):

```bash
python $PROJECT_ROOT/tools/format_agent_context.py market       $MARKET_JSON_PATH
python $PROJECT_ROOT/tools/format_agent_context.py news         $NEWS_JSON_PATH
python $PROJECT_ROOT/tools/format_agent_context.py fundamentals $FUNDAMENTALS_JSON_PATH
python $PROJECT_ROOT/tools/format_agent_context.py sentiment    $SENTIMENT_JSON_PATH
```

Capture each stdout as:
- `MARKET_DATA`        ← market context markdown
- `NEWS_DATA`          ← news context markdown
- `FUNDAMENTALS_DATA`  ← fundamentals context markdown
- `SENTIMENT_DATA`     ← sentiment context markdown

These variables feed Step 2 exactly as before — agents/*.md prompts remain unchanged.

---

### Step 2: Phase 1 — Analyst Team (Parallel Agents)

Read all four agent prompt files **simultaneously**:
- `$PROJECT_ROOT/agents/market_analyst.md`
- `$PROJECT_ROOT/agents/news_analyst.md`
- `$PROJECT_ROOT/agents/fundamentals_analyst.md`
- `$PROJECT_ROOT/agents/social_analyst.md`

Replace `{TICKER}` and `{DATE}` placeholders in each prompt with actual values.

> **언어 부착 규칙 (Step 2~6 공통):** 모든 sub-agent 프롬프트는 다음 패턴으로 조립합니다:
> ```
> prompt = agent_prompt_with_placeholders_replaced
>         + "\n\n" + LANG_INSTRUCTION
>         + "\n\n---\n\n" + DATA_BLOCK
> ```
> 즉 agent 프롬프트 본문 → LANG_INSTRUCTION → 데이터 블록 순.

Then spawn all four agents **in parallel** using the Agent tool (single message, four tool calls):

**Market Analyst Agent:**
```
prompt = market_analyst_prompt + "\n\n" + LANG_INSTRUCTION + "\n\n---\n\n" + MARKET_DATA
subagent_type = "claude"
description = "Market technical analysis for {TICKER}"
```

**News Analyst Agent:**
```
prompt = news_analyst_prompt + "\n\n" + LANG_INSTRUCTION + "\n\n---\n\n" + NEWS_DATA
subagent_type = "claude"
description = "News and events analysis for {TICKER}"
```

**Fundamentals Analyst Agent:**
```
prompt = fundamentals_analyst_prompt + "\n\n" + LANG_INSTRUCTION + "\n\n---\n\n" + FUNDAMENTALS_DATA
subagent_type = "claude"
description = "Fundamental financial analysis for {TICKER}"
```

**Social Analyst Agent:**
```
prompt = social_analyst_prompt + "\n\n" + LANG_INSTRUCTION + "\n\n---\n\n" + SENTIMENT_DATA
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
          + "\n\n" + LANG_INSTRUCTION
          + "\n\n---\n\n## 애널리스트 보고서\n\n" + ALL_ANALYST_REPORTS
          + (R > 1 이면: "\n\n---\n\n## 이전 라운드 Bear 주장 (반박 대상)\n\n" + PREV_BEAR)
  ```
  → `BULL_REPORTS[R]` 에 저장

  **Bear Researcher** (spawn Agent, wait):
  ```
  prompt = bear_researcher_prompt
          + "\n\n" + LANG_INSTRUCTION
          + "\n\n---\n\n## 애널리스트 보고서\n\n" + ALL_ANALYST_REPORTS
          + "\n\n---\n\n## 이번 라운드 Bull 주장 (반박 대상)\n\n" + BULL_REPORTS[R]
  ```
  → `BEAR_REPORTS[R]` 에 저장

  `PREV_BULL = BULL_REPORTS[R]`, `PREV_BEAR = BEAR_REPORTS[R]`

**Research Manager** — 최종 라운드 결과로 합성 (spawn Agent, wait):
```
prompt = research_manager_prompt
        + "\n\n" + LANG_INSTRUCTION
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
        + "\n\n" + LANG_INSTRUCTION
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
prompt = aggressive_risk_prompt (agents/aggressive_risk.md) + "\n\n" + LANG_INSTRUCTION + "\n\n---\n\n" + FULL_CONTEXT
```

**Conservative Risk Agent:**
```
prompt = conservative_risk_prompt (agents/conservative_risk.md) + "\n\n" + LANG_INSTRUCTION + "\n\n---\n\n" + FULL_CONTEXT
```

**Neutral Risk Agent:**
```
prompt = neutral_risk_prompt (agents/neutral_risk.md) + "\n\n" + LANG_INSTRUCTION + "\n\n---\n\n" + FULL_CONTEXT
```

Wait for all three. Store as `AGGRESSIVE_RISK`, `CONSERVATIVE_RISK`, `NEUTRAL_RISK`.

Print: `✓ Phase 4 complete — risk assessments done`

---

### Step 6: Phase 5 — Portfolio Manager (Final Decision)

Spawn one Agent (wait for result):
```
prompt = portfolio_manager_prompt (agents/portfolio_manager.md, {TICKER}/{DATE} replaced)
        + "\n\n" + LANG_INSTRUCTION
        + "\n\n---\n\n## Analyst Reports\n\n" + ALL_ANALYST_REPORTS
        + "\n\n---\n\n## Investment Plan\n\n" + INVESTMENT_PLAN
        + "\n\n---\n\n## Trading Plan\n\n" + TRADING_PLAN
        + "\n\n---\n\n## Risk Assessments\n\n### Aggressive\n" + AGGRESSIVE_RISK
        + "\n\n### Conservative\n" + CONSERVATIVE_RISK
        + "\n\n### Neutral\n" + NEUTRAL_RISK
```
Store result as `FINAL_DECISION`.

---

### Step 7: Assemble Report JSON & Render

**trading_checklist 추출:** TRADING_PLAN 텍스트에서 구체적인 행동 항목을 최대 10개 배열로 추출하세요.  
예시: `["RSI 60 이하 진입 확인", "1차 목표가 $210 설정", "손절선 $185 설정"]`

**decision_reasons 추출:** FINAL_DECISION 텍스트에서 핵심 근거를 최대 8개 배열로 추출하세요.  
예시: `["강한 기술적 모멘텀", "견조한 매출 성장", "AI 사업 확장"]`

**최종 JSON 조립** — Step 1의 fetch JSON 4개를 그대로 임베드하고, 분석 보고서를 합쳐 `/tmp/tradingagentscc_report_{TICKER}.json`에 저장합니다. fetch JSON은 Read 도구로 각 `*_JSON_PATH` 파일을 읽어 그대로 객체로 끼워 넣으세요.

> ⚠️ `market_data`, `news_data`, `fundamentals_data`, `sentiment_data` 네 필드는 **반드시 Step 1에서 만든 `/tmp/tac_{TICKER}_*.json` 파일을 Read 도구로 읽어 JSON 객체 그대로 임베드**해야 합니다. 문자열·요약·마크다운 변환본을 넣으면 `render_html.py`의 차트 파서가 빈 배열을 반환하고 차트가 빈 캔버스로 표시됩니다 (stderr에 `[warn] market_data.price_history.close not found ...` 류 경고 출력).

```json
{
  "ticker": "{TICKER}",
  "date": "{DATE}",
  "market_data":       { ...MARKET_JSON_PATH 내용 그대로... },
  "news_data":         { ...NEWS_JSON_PATH 내용 그대로... },
  "fundamentals_data": { ...FUNDAMENTALS_JSON_PATH 내용 그대로... },
  "sentiment_data":    { ...SENTIMENT_JSON_PATH 내용 그대로... },
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

**렌더러 분기** — `FORMAT` 값에 따라 Bash 도구로 실행 (`both`는 둘 다 실행). 두 렌더러는 동일한 입력 JSON을 소비합니다.

```bash
# FORMAT in ("html", "both")
python {PROJECT_ROOT}/tools/render_html.py \
  /tmp/tradingagentscc_report_{TICKER}.json \
  {PROJECT_ROOT}/outputs/{DATE}_{TICKER}.html \
  --lang {LANG}

# FORMAT in ("md", "both")
python {PROJECT_ROOT}/tools/render_md.py \
  /tmp/tradingagentscc_report_{TICKER}.json \
  {PROJECT_ROOT}/outputs/{DATE}_{TICKER}.md \
  --lang {LANG}
```

성공 시 — 생성된 산출물 경로를 모두 출력하세요:

```
✅ HTML 보고서: outputs/{DATE}_{TICKER}.html
✅ Markdown 보고서: outputs/{DATE}_{TICKER}.md
브라우저에서 열기: open outputs/{DATE}_{TICKER}.html
```

(FORMAT에 해당하지 않는 줄은 생략.)

렌더러가 non-zero exit으로 실패하면 stderr를 그대로 보여주고 멈춥니다. 마크다운 출력은 이제 정식 출력이므로 별도 폴백을 두지 않습니다.
