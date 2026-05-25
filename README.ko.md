# TradingAgentsCC

[English](README.md) | **한국어**

> Claude Code 위에서 동작하는 다중 에이전트 주식 분석 — **별도의 LLM API 키 불필요**

[![Python](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://www.python.org/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](./LICENSE)
[![Based on TradingAgents](https://img.shields.io/badge/based%20on-TauricResearch%2FTradingAgents-orange)](https://github.com/TauricResearch/TradingAgents)
[![Claude Code Plugin](https://img.shields.io/badge/Claude%20Code-Plugin-7C3AED)](https://docs.claude.com/en/docs/claude-code/plugins)

---

## TradingAgentsCC란?

**TradingAgentsCC**는 [Tauric Research](https://github.com/TauricResearch)의 [TradingAgents](https://github.com/TauricResearch/TradingAgents)를 Claude Code 네이티브 환경으로 포팅한 프로젝트입니다. 4명의 애널리스트, 강세/약세 리서처, 트레이더, 3명의 리스크 검토자, 포트폴리오 매니저까지 **총 12개의 sub-agent**가 협업하는 주식 분석 파이프라인을 Claude Code 위에서 그대로 실행합니다.

`/tradingagentscc:ticker AAPL` 명령 한 줄이면 5개 페이즈에 걸친 병렬·순차 에이전트 호출이 실행되며, 인터랙티브 차트가 포함된 HTML 보고서와 Markdown 요약본이 자동 생성됩니다.

파이프라인 자체의 아키텍처는 원본 TradingAgents와 동일하지만, **오케스트레이션 레이어를 LangGraph에서 Claude Code의 네이티브 sub-agent 디스패치(Task 툴)로 완전히 재구현** 했습니다.

## 왜 Claude Code인가?

| | 원본 [TradingAgents](https://github.com/TauricResearch/TradingAgents) | **TradingAgentsCC** |
|---|---|---|
| LLM 접근 | OpenAI/Anthropic/Google 등 API 키 필요 | **Claude Code 구독제만으로 동작 — 별도 API 키 불필요** |
| 오케스트레이션 | LangGraph 상태 머신 | Claude Code sub-agent 디스패치 (네이티브 `Task` 툴) |
| 설치 규모 | Python + LangGraph + 선택 LLM SDK들 | Python + yfinance만 |
| 출력 | 로그 + 결정 기록 | **이중 언어 HTML 보고서 (인터랙티브 차트)** + Markdown |
| 다국어 | 영어 | `--lang` 플래그로 **한국어 / 영어** 선택 |

**별도 LLM API 키가 필요 없습니다.** 파이프라인의 모든 LLM 호출이 Claude Code 자체를 통해 처리되므로, Claude Pro / Max / Team 구독만 있으면 바로 사용할 수 있습니다.

## 빠른 시작

```bash
# 1. 클론
git clone https://github.com/JaeHye0k/TradingAgentsCC
cd TradingAgentsCC

# 2. Python 의존성 설치 (yfinance, stockstats, pandas, …)
pip install .

# 3. 해당 디렉토리에서 Claude Code를 실행한 뒤:
/tradingagentscc:ticker CEG
/tradingagentscc:ticker AAPL --date 2026-05-01 --lang en --format html
/tradingagentscc:ticker 005930 --rounds 2 --lang ko          # 한국 종목 코드는 자동으로 .KS 접미사
```

> 플러그인은 레포지토리 루트의 `.claude/skills/ticker/SKILL.md`와 `agents/*.md`를 읽습니다. 프로젝트 디렉토리 안에서 명령을 실행하거나 Claude Code 플러그인으로 설치해 주세요.

## 아키텍처

```
/tradingagentscc:ticker <symbol>
  │
  ├─ Step 1   데이터 수집 (병렬 bash) ──── 시세 · 뉴스 · 펀더멘털 · 센티먼트
  │
  ├─ Phase 1  애널리스트팀 (병렬)        ── market · news · fundamentals · social
  ├─ Phase 2  리서치팀 (순차)            ── bull ⇄ bear  (N 라운드 토론) → research_manager
  ├─ Phase 3  트레이더                  ── 투자 플랜 → 실행 가능한 거래 플랜
  ├─ Phase 4  리스크 검토 (병렬)         ── aggressive · conservative · neutral
  └─ Phase 5  포트폴리오 매니저          ── 최종 결정 (Buy / Overweight / Hold / Underweight / Sell)
                │
                └─ 렌더링 → outputs/{DATE}_{TICKER}.html  +  outputs/{DATE}_{TICKER}.md
```

## 에이전트 구성

| # | Agent | 역할 | Phase |
|---|---|---|---|
| 1 | `market_analyst` | 기술적 분석 — RSI, MACD, Bollinger Bands, SMA / EMA | 1 |
| 2 | `news_analyst` | 이벤트 기반 + 매크로 컨텍스트 분석 | 1 |
| 3 | `fundamentals_analyst` | 손익계산서, 재무상태표, 현금흐름, 밸류에이션 | 1 |
| 4 | `social_analyst` | Reddit + StockTwits 기반 리테일 센티먼트 | 1 |
| 5 | `bull_researcher` | 가장 강한 강세 논거 구성 | 2 |
| 6 | `bear_researcher` | 가장 강한 약세 반론 구성 | 2 |
| 7 | `research_manager` | 토론을 균형 잡힌 권고안으로 합성 | 2 |
| 8 | `trader` | 투자 플랜을 실행 가능한 거래 전략으로 변환 | 3 |
| 9 | `aggressive_risk` | 수익 극대화 관점의 리스크 검토 | 4 |
| 10 | `conservative_risk` | 자본 보존 관점의 리스크 검토 | 4 |
| 11 | `neutral_risk` | 균형 관점의 리스크 검토 | 4 |
| 12 | `portfolio_manager` | 진입/청산 파라미터까지 포함한 최종 결정 | 5 |

각 에이전트는 `agents/` 아래의 단일 markdown 프롬프트 파일입니다. 동작을 바꾸려면 코드 수정 없이 해당 파일만 편집하면 됩니다.

## 도구 & 데이터 소스

| 도구 | 목적 |
|---|---|
| `tools/fetch_market.py` | 시세 + 기술지표 (yfinance, stockstats) |
| `tools/fetch_news.py` | 뉴스 기사 + 내부자 거래 (yfinance News API) |
| `tools/fetch_fundamentals.py` | 손익/재무/현금흐름 (yfinance) |
| `tools/fetch_sentiment.py` | Reddit (r/wallstreetbets, r/stocks, r/investing) + StockTwits |
| `tools/format_agent_context.py` | 수집한 JSON을 에이전트별 markdown 컨텍스트로 변환 |
| `tools/render_html.py` | 인터랙티브 HTML 보고서 (Chart.js) |
| `tools/render_md.py` | Markdown 보고서 |

**의도적으로 사용하지 않는 것:** FinnHub, Tushare, 유료 뉴스 API 등 — Claude Code 외에는 어떤 자격증명도 요구하지 않는 것이 목표입니다.

## 옵션 & 플래그

```
/tradingagentscc:ticker TICKER [--date YYYY-MM-DD] [--rounds N] [--format html|md|both] [--lang ko|en]
```

| 플래그 | 값 | 기본값 | 비고 |
|---|---|---|---|
| `TICKER` | 예: `AAPL`, `CEG`, `005930` | _필수_ | 6자리 숫자는 자동으로 `.KS`(KRX) 접미사 |
| `--date` | `YYYY-MM-DD` | 오늘 | 분석 기준일 (시세/뉴스 룩백 윈도우의 기준점) |
| `--rounds` | `1` / `2` / `3` | `1` | Bull ↔ Bear 토론 라운드 수. 클수록 심층적이지만 느림 |
| `--format` | `html` / `md` / `both` | `both` | HTML은 인터랙티브 차트 포함 |
| `--lang` | `ko` / `en` | `ko` | 최종 보고서의 출력 언어 |

플래그를 생략하면 스킬이 **실행 전 인터랙티브 질문**으로 누락 값을 확인합니다 — 임의의 기본값으로 무음 진행하지 **않습니다**.

## 출력 예시

실행 후 `outputs/` 디렉토리에 다음이 생성됩니다:

```
outputs/
├── 2026-05-01_AAPL.html      # 시세 차트 · 지표 · 토론 트랜스크립트가 포함된 인터랙티브 리포트
└── 2026-05-01_AAPL.md        # 터미널 / Git diff용 텍스트 요약
```

HTML 리포트의 마지막 블록은 대략 다음과 같이 표시됩니다:

```
═══ 포트폴리오 매니저 — 최종 결정 ═══
판정:           Overweight (비중 확대)
확신도:         7 / 10
진입가:         $182 – $186
손절선:         $174
4주 목표:       $205
포지션 크기:    포트폴리오의 3.5 %
```

## FAQ

**LLM API 키가 필요한가요?**
아니요. 모든 모델 호출이 Claude Code 세션을 통해 라우팅되므로 **Claude Pro / Max / Team 구독만 있으면** 됩니다. yfinance, Reddit, StockTwits는 익명으로 접근합니다.

**어느 시장을 지원하나요?**
yfinance가 지원하는 모든 종목 — 미국 주식, ETF, 지수, 대부분의 해외 종목. **한국 종목**은 6자리 코드(`005930`)로 입력하면 스킬이 자동으로 `.KS` 접미사를 붙입니다 (예: `005930` → `005930.KS`).

**투자 자문인가요?**
**아닙니다.** TradingAgentsCC는 교육·연구 목적의 도구입니다. 투자 자문이 아니며, 본 도구의 출력에 기반한 매매 결정에 대해 저자는 어떠한 책임도 지지 않습니다. 반드시 **본인의 판단과 책임 하에** 사용하세요.

**원본 TradingAgents와 무엇이 다른가요?**
에이전트 아키텍처는 동일하지만 런타임이 다릅니다. 전체 변경 내역은 [`NOTICE`](./NOTICE) 파일을 참고하세요.

**에이전트를 수정할 수 있나요?**
네. 각 에이전트는 `agents/` 아래의 일반 markdown 프롬프트입니다. 편집 후 저장하고 다시 실행하면 즉시 반영됩니다.

## 출처 표기 (Attribution)

본 프로젝트는 **Tauric Research** (Yijia Xiao, Edward Sun, Di Luo, Wei Wang)가 Apache-2.0 라이선스로 공개한 [**TradingAgents**](https://github.com/TauricResearch/TradingAgents)의 파생 저작물입니다.

학술 목적으로 본 소프트웨어를 사용할 경우 원논문을 인용해 주세요:

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

전체 출처 표기와 원본 대비 수정 사항 목록은 [`NOTICE`](./NOTICE) 파일을 확인하세요.

## 라이선스

본 프로젝트는 [**Apache License, Version 2.0**](./LICENSE)으로 배포됩니다. 필수 출처 표기 사항은 [`NOTICE`](./NOTICE) 파일을 참고하세요.
