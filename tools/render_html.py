#!/usr/bin/env python3
"""Generate a self-contained interactive HTML report from TradingAgentsCC analysis JSON.

Input JSON schema (assembled by SKILL.md Step 7):
{
  "ticker": str, "date": str,
  "market_data":       <fetch_market.py JSON>,
  "news_data":         <fetch_news.py JSON>,
  "fundamentals_data": <fetch_fundamentals.py JSON>,
  "sentiment_data":    <fetch_sentiment.py JSON>,
  "reports": { ... markdown strings + arrays ... }
}
"""

import html as _html
import json
import os
import sys
from urllib.request import urlopen

import markdown as _md

CHARTJS_CDN = "https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"

LABELS = {
    "ko": {
        "final_decision": "최종 결정",
        "analysis_summary": "분석 요약",
        "price_90d": "주가 (90일)",
        "market_analysis": "시장 분석",
        "sentiment_dist": "감성 분포 (StockTwits)",
        "social_analysis": "소셜 분석",
        "bull_bear_debate": "Bull / Bear 토론",
        "rm_synthesis": "Research Manager 합성",
        "trading_checklist": "트레이딩 체크리스트",
        "trading_plan": "트레이딩 플랜",
        "risk_compare": "리스크 관점 비교",
        "decision_reasons": "결정 근거",
        "full_text": "전문",
        "close": "종가",
        "close_90d": "종가 (90일)",
        "overbought_70": "과매수 (70)",
        "oversold_30": "과매도 (30)",
        "round": "라운드",
        "empty_items": "항목이 없습니다",
        "empty_debate": "토론 데이터가 없습니다",
        "report_saved": "보고서 저장됨",
        "html_lang": "ko",
    },
    "en": {
        "final_decision": "Final Decision",
        "analysis_summary": "Analysis Summary",
        "price_90d": "Price (90 days)",
        "market_analysis": "Market Analysis",
        "sentiment_dist": "Sentiment Distribution (StockTwits)",
        "social_analysis": "Social Sentiment",
        "bull_bear_debate": "Bull / Bear Debate",
        "rm_synthesis": "Research Manager Synthesis",
        "trading_checklist": "Trading Checklist",
        "trading_plan": "Trading Plan",
        "risk_compare": "Risk Perspectives",
        "decision_reasons": "Decision Reasons",
        "full_text": "Full Text",
        "close": "Close",
        "close_90d": "Close (90 days)",
        "overbought_70": "Overbought (70)",
        "oversold_30": "Oversold (30)",
        "round": "Round",
        "empty_items": "No items",
        "empty_debate": "No debate data",
        "report_saved": "Report saved",
        "html_lang": "en",
    },
}


def fetch_chartjs() -> str | None:
    """Fetch Chart.js minified source from CDN for inline embedding. Returns None on failure."""
    try:
        with urlopen(CHARTJS_CDN, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except Exception as exc:
        print(f"[warn] Chart.js fetch failed ({exc}); charts will be disabled.", file=sys.stderr)
        return None


def build_chart_data(data: dict) -> dict:
    """Project the analysis JSON into the shape Chart.js needs."""
    market = data.get("market_data") or {}
    sentiment = data.get("sentiment_data") or {}

    ph = market.get("price_history") or {}
    price = {"labels": ph.get("dates", []), "prices": ph.get("close", [])}

    indicators = market.get("indicators") or {}

    def _ind(key: str) -> dict:
        i = indicators.get(key) or {}
        return {"labels": i.get("dates", []), "values": i.get("values", [])}

    # Drop non-trading days (None values) so Chart.js renders a continuous line.
    # Indicator arrays from lib.py include every calendar day with None for
    # weekends/holidays; the price chart already contains only trading days.
    def _drop_none(dates: list, *value_lists: list) -> tuple[list, list[list]]:
        keep = [
            i for i in range(len(dates))
            if all(i < len(v) and v[i] is not None for v in value_lists)
        ]
        return ([dates[i] for i in keep],
                [[v[i] for i in keep] for v in value_lists])

    rsi_raw = _ind("rsi")
    rsi_labels, (rsi_values,) = _drop_none(rsi_raw["labels"], rsi_raw["values"])
    rsi = {"labels": rsi_labels, "values": rsi_values}

    macd_line = _ind("macd")
    macd_sig = _ind("macds")
    macd_hist = _ind("macdh")
    macd_labels, (macd_vals, sig_vals, hist_vals) = _drop_none(
        macd_line["labels"],
        macd_line["values"], macd_sig["values"], macd_hist["values"],
    )

    st = sentiment.get("stocktwits") or {}
    sent = {
        "bullish": st.get("bullish", 0),
        "bearish": st.get("bearish", 0),
        "unlabeled": st.get("unlabeled", 0),
    }

    if not price["labels"]:
        print("[warn] market_data.price_history.close not found — overview/price/sparkline charts disabled.", file=sys.stderr)
    if not rsi_raw["labels"]:
        print("[warn] market_data.indicators.rsi not found — RSI chart disabled.", file=sys.stderr)
    if not macd_line["labels"]:
        print("[warn] market_data.indicators.macd not found — MACD chart disabled.", file=sys.stderr)
    if (sent["bullish"] + sent["bearish"] + sent["unlabeled"]) == 0:
        print("[warn] sentiment_data.stocktwits empty — sentiment doughnut will be blank.", file=sys.stderr)

    return {
        "price": price,
        "rsi": rsi,
        "macd": {
            "labels": macd_labels,
            "macd": macd_vals,
            "signal": sig_vals,
            "histogram": hist_vals,
        },
        "sentiment": sent,
    }


def detect_decision(final_decision: str) -> tuple[str, str]:
    """Return (label, css_color_var) for the final decision badge.

    css_color_var is one of 'emerald', 'amber', 'rose'.
    """
    upper = final_decision.upper()
    if "BUY" in upper or "매수" in final_decision:
        return "BUY", "emerald"
    if "SELL" in upper or "매도" in final_decision:
        return "SELL", "rose"
    return "HOLD", "amber"


def md_to_html(text: str) -> str:
    """Convert markdown to HTML using the python-markdown library."""
    if not text or not text.strip():
        return ""
    return _md.markdown(text, extensions=["extra", "sane_lists"])


def _checklist_html(items: list[str], id_prefix: str, L: dict) -> str:
    if not items:
        return f'<p class="muted-text">{L["empty_items"]}.</p>'
    rows = "".join(
        f'<label class="check-item"><input type="checkbox" id="{id_prefix}-{i}"> <span>{item}</span></label>\n'
        for i, item in enumerate(items)
    )
    return f'<div class="checklist">{rows}</div>'


def _debate_html(bull_reports: list[str], bear_reports: list[str], L: dict) -> str:
    rounds = max(len(bull_reports), len(bear_reports))
    if rounds == 0:
        return f'<p class="muted-text">{L["empty_debate"]}.</p>'
    parts = []
    for r in range(rounds):
        parts.append(f'<details open><summary class="debate-summary">{L["round"]} {r + 1}</summary>\n')
        if r < len(bull_reports):
            parts.append(f'<div class="debate-bull"><h4>🐂 Bull Researcher</h4><div class="report-text">{md_to_html(bull_reports[r])}</div></div>\n')
        if r < len(bear_reports):
            parts.append(f'<div class="debate-bear"><h4>🐻 Bear Researcher</h4><div class="report-text">{md_to_html(bear_reports[r])}</div></div>\n')
        parts.append("</details>\n")
    return "".join(parts)


CSS = """
:root {
  --bg: #0d1117; --surface: #161b22; --surface2: #21262d;
  --border: #30363d; --text: #e6edf3; --muted: #8b949e;
  --indigo: #6366f1; --cyan: #06b6d4; --amber: #f59e0b;
  --emerald: #10b981; --rose: #f43f5e; --purple: #a855f7;
  --font: -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: var(--bg); color: var(--text); font-family: var(--font); font-size: 14px; line-height: 1.7; min-height: 100vh; }

/* Header */
.header { padding: 1.25rem 2rem; border-bottom: 1px solid var(--border); background: linear-gradient(135deg,#0d1117,#161b22); display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap; }
.ticker-sym { font-size: 1.75rem; font-weight: 800; background: linear-gradient(135deg,var(--indigo),var(--purple)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.date-badge { color: var(--muted); font-size: 0.85rem; }
.decision-badge { padding: 0.3rem 0.8rem; border-radius: 20px; font-weight: 700; font-size: 0.9rem; }
.decision-badge.emerald { background: rgba(16,185,129,0.15); color: var(--emerald); border: 1px solid var(--emerald); }
.decision-badge.amber   { background: rgba(245,158,11,0.15); color: var(--amber);   border: 1px solid var(--amber); }
.decision-badge.rose    { background: rgba(244,63,94,0.15);  color: var(--rose);    border: 1px solid var(--rose); }
.sparkline-wrap { margin-left: auto; }

/* Tabs */
.tab-bar { display: flex; background: var(--surface); border-bottom: 1px solid var(--border); padding: 0 1.5rem; gap: 0.25rem; overflow-x: auto; }
.tab { padding: 0.65rem 1rem; background: none; border: none; border-bottom: 2px solid transparent; color: var(--muted); cursor: pointer; font-family: var(--font); font-size: 0.82rem; white-space: nowrap; transition: color 0.15s, border-color 0.15s; }
.tab:hover { color: var(--text); }
.tab.active { color: var(--text); border-bottom-color: var(--indigo); }

/* Tab panels */
.tab-panel { display: none; padding: 1.5rem 2rem; max-width: 1200px; margin: 0 auto; }
.tab-panel.active { display: block; }

/* Charts */
.chart-wrap { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 1.25rem; }
.chart-wrap.narrow { max-width: 400px; }
.chart-wrap canvas { width: 100% !important; }

/* Report text */
.report-text { color: var(--text); }
.report-text h1,.report-text h2,.report-text h3 { margin: 1rem 0 0.5rem; color: var(--text); }
.report-text h2 { font-size: 1rem; color: var(--cyan); }
.report-text h3 { font-size: 0.9rem; color: var(--muted); }
.report-text p  { margin-bottom: 0.75rem; }
.report-text ul, .report-text ol { padding-left: 1.25rem; margin-bottom: 0.75rem; }
.report-text strong { color: var(--amber); }

/* Cards */
.cards-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(180px,1fr)); gap: 0.75rem; margin-bottom: 1.25rem; }
.metric-card { background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 0.85rem 1rem; }
.metric-card .label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem; }
.metric-card .value { font-size: 1.1rem; font-weight: 700; color: var(--text); }

/* Decision card */
.decision-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 2rem; text-align: center; margin-bottom: 1.5rem; }
.decision-card .label { font-size: 0.75rem; color: var(--muted); text-transform: uppercase; margin-bottom: 0.5rem; }
.decision-card .big-badge { font-size: 2.5rem; font-weight: 900; }
.decision-card.emerald .big-badge { color: var(--emerald); }
.decision-card.amber   .big-badge { color: var(--amber); }
.decision-card.rose    .big-badge { color: var(--rose); }

/* Checklist */
.checklist { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1.25rem; }
.checklist h3 { font-size: 0.85rem; color: var(--muted); text-transform: uppercase; margin-bottom: 0.75rem; }
.check-item { display: flex; align-items: flex-start; gap: 0.6rem; padding: 0.4rem 0; cursor: pointer; }
.check-item input { margin-top: 3px; accent-color: var(--indigo); width: 14px; height: 14px; flex-shrink: 0; }
.check-item span { font-size: 0.88rem; }

/* Research debate */
details { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 0.75rem; overflow: hidden; }
.debate-summary { padding: 0.65rem 1rem; cursor: pointer; font-weight: 600; font-size: 0.85rem; user-select: none; }
.debate-bull { background: rgba(16,185,129,0.05); border-left: 3px solid var(--emerald); padding: 1rem 1.25rem; }
.debate-bear { background: rgba(244,63,94,0.05);  border-left: 3px solid var(--rose);    padding: 1rem 1.25rem; }
.debate-bull h4,.debate-bear h4 { font-size: 0.8rem; text-transform: uppercase; margin-bottom: 0.5rem; }
.debate-bull h4 { color: var(--emerald); }
.debate-bear h4 { color: var(--rose); }

/* Risk cards */
.risk-cards { display: grid; grid-template-columns: repeat(auto-fit,minmax(280px,1fr)); gap: 1rem; margin-top: 1.25rem; }
.risk-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.25rem; }
.risk-card h4 { font-size: 0.8rem; text-transform: uppercase; margin-bottom: 0.75rem; }
.risk-card.rose    h4 { color: var(--rose); }
.risk-card.amber   h4 { color: var(--amber); }
.risk-card.indigo  h4 { color: var(--indigo); }

/* Misc */
.muted-text { color: var(--muted); font-size: 0.85rem; }
.section-title { font-size: 0.75rem; font-weight: 700; color: var(--muted); text-transform: uppercase; letter-spacing: 0.06em; margin: 1.25rem 0 0.75rem; }
"""


def generate_html(data: dict, chartjs_src: str | None, lang: str = "ko") -> str:
    L = LABELS[lang]
    ticker = _html.escape(data["ticker"])
    date = _html.escape(data["date"])
    r = data["reports"]

    chart_data = build_chart_data(data)
    decision, dec_color = detect_decision(r.get("final_decision", ""))

    charts_ok = "true" if chartjs_src else "false"
    chartjs_tag = f"<script>{chartjs_src}</script>" if chartjs_src else ""

    checklist_html = _checklist_html(r.get("trading_checklist", []), "trade", L)
    reasons_html = _checklist_html(r.get("decision_reasons", []), "dec", L)
    debate_html = _debate_html(r.get("bull", []), r.get("bear", []), L)

    def section(content_key: str) -> str:
        return md_to_html(r.get(content_key, ""))

    return f"""<!DOCTYPE html>
<html lang="{L["html_lang"]}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{ticker} — TradingAgentsCC {date}</title>
<style>{CSS}</style>
{chartjs_tag}
</head>
<body>

<!-- ── Header ── -->
<header class="header">
  <span class="ticker-sym">{ticker}</span>
  <span class="date-badge">{date}</span>
  <span class="decision-badge {dec_color}">{decision}</span>
  <div class="sparkline-wrap">
    <canvas id="sparkline" width="180" height="44"></canvas>
  </div>
</header>

<!-- ── Tab bar ── -->
<nav class="tab-bar">
  <button class="tab active" data-tab="overview">Overview</button>
  <button class="tab" data-tab="market">📊 Market</button>
  <button class="tab" data-tab="news">📰 News</button>
  <button class="tab" data-tab="fundamentals">📈 Fundamentals</button>
  <button class="tab" data-tab="sentiment">💬 Sentiment</button>
  <button class="tab" data-tab="research">🔬 Research</button>
  <button class="tab" data-tab="trading">💹 Trading</button>
  <button class="tab" data-tab="risk">⚖️ Risk</button>
  <button class="tab" data-tab="decision">🎯 Decision</button>
</nav>

<!-- ── Tab panels ── -->

<div id="overview" class="tab-panel active">
  <div class="chart-wrap"><canvas id="overview-chart"></canvas></div>
  <div class="decision-card {dec_color}">
    <div class="label">{L["final_decision"]}</div>
    <div class="big-badge">{decision}</div>
  </div>
  <p class="section-title">{L["analysis_summary"]}</p>
  <div class="report-text">{section("final_decision")}</div>
</div>

<div id="market" class="tab-panel">
  <p class="section-title">{L["price_90d"]}</p>
  <div class="chart-wrap"><canvas id="price-chart"></canvas></div>
  <p class="section-title">RSI</p>
  <div class="chart-wrap"><canvas id="rsi-chart"></canvas></div>
  <p class="section-title">MACD</p>
  <div class="chart-wrap"><canvas id="macd-chart"></canvas></div>
  <p class="section-title">{L["market_analysis"]}</p>
  <div class="report-text">{section("market")}</div>
</div>

<div id="news" class="tab-panel">
  <div class="report-text">{section("news")}</div>
</div>

<div id="fundamentals" class="tab-panel">
  <div class="report-text">{section("fundamentals")}</div>
</div>

<div id="sentiment" class="tab-panel">
  <p class="section-title">{L["sentiment_dist"]}</p>
  <div class="chart-wrap narrow"><canvas id="sentiment-chart"></canvas></div>
  <p class="section-title">{L["social_analysis"]}</p>
  <div class="report-text">{section("social")}</div>
</div>

<div id="research" class="tab-panel">
  <p class="section-title">{L["bull_bear_debate"]}</p>
  {debate_html}
  <p class="section-title">{L["rm_synthesis"]}</p>
  <div class="report-text">{section("investment_plan")}</div>
</div>

<div id="trading" class="tab-panel">
  <p class="section-title">{L["trading_checklist"]}</p>
  {checklist_html}
  <p class="section-title">{L["trading_plan"]}</p>
  <div class="report-text">{section("trading_plan")}</div>
</div>

<div id="risk" class="tab-panel">
  <p class="section-title">{L["risk_compare"]}</p>
  <div class="chart-wrap"><canvas id="risk-chart"></canvas></div>
  <div class="risk-cards">
    <div class="risk-card rose">
      <h4>⚡ Aggressive</h4>
      <div class="report-text">{section("aggressive_risk")}</div>
    </div>
    <div class="risk-card amber">
      <h4>🛡️ Conservative</h4>
      <div class="report-text">{section("conservative_risk")}</div>
    </div>
    <div class="risk-card indigo">
      <h4>⚖️ Neutral</h4>
      <div class="report-text">{section("neutral_risk")}</div>
    </div>
  </div>
</div>

<div id="decision" class="tab-panel">
  <div class="decision-card {dec_color}">
    <div class="label">{L["final_decision"]}</div>
    <div class="big-badge">{decision}</div>
  </div>
  <p class="section-title">{L["decision_reasons"]}</p>
  {reasons_html}
  <p class="section-title">{L["full_text"]}</p>
  <div class="report-text">{section("final_decision")}</div>
</div>

<!-- ── Scripts ── -->
<script>
// Tab switching
document.querySelectorAll('.tab').forEach(function(tab) {{
  tab.addEventListener('click', function() {{
    document.querySelectorAll('.tab').forEach(function(t) {{ t.classList.remove('active'); }});
    document.querySelectorAll('.tab-panel').forEach(function(p) {{ p.classList.remove('active'); }});
    tab.classList.add('active');
    document.getElementById(tab.dataset.tab).classList.add('active');
  }});
}});

var CHARTS_OK = {charts_ok};
var CD = {json.dumps(chart_data)};

if (CHARTS_OK) {{
  var gridColor = 'rgba(48,54,61,0.6)';
  var textColor = '#8b949e';
  var baseOpts = {{
    responsive: true,
    interaction: {{ mode: 'index', intersect: false }},
    plugins: {{
      legend: {{ labels: {{ color: textColor }} }},
      tooltip: {{
        enabled: true,
        backgroundColor: 'rgba(22,27,34,0.95)',
        borderColor: '#30363d',
        borderWidth: 1,
        titleColor: '#e6edf3',
        bodyColor: '#e6edf3',
        padding: 10,
        cornerRadius: 6,
        displayColors: true,
        callbacks: {{
          label: function(ctx) {{
            var v = ctx.parsed.y;
            if (v === null || v === undefined) return ctx.dataset.label;
            return ctx.dataset.label + ': ' + (Math.abs(v) >= 100 ? v.toFixed(2) : v.toFixed(4));
          }}
        }}
      }}
    }},
    scales: {{
      x: {{ ticks: {{ color: textColor, maxTicksLimit: 8 }}, grid: {{ color: gridColor }} }},
      y: {{ ticks: {{ color: textColor }}, grid: {{ color: gridColor }} }}
    }}
  }};

  function lineDataset(label, data, color, fill) {{
    return {{ type:'line', label:label, data:data, borderColor:color,
              backgroundColor: fill ? color.replace(')',',0.12)').replace('rgb','rgba') : 'transparent',
              borderWidth:2, pointRadius:0, pointHoverRadius:5, pointHitRadius:20,
              pointHoverBackgroundColor:color, pointHoverBorderColor:'#fff', pointHoverBorderWidth:2,
              fill:!!fill }};
  }}

  // Sparkline (header)
  if (CD.price.labels.length > 0) {{
    new Chart(document.getElementById('sparkline'), {{
      type: 'line',
      data: {{ labels: CD.price.labels, datasets: [lineDataset('', CD.price.prices, '#6366f1', false)] }},
      options: {{ responsive:false, animation:false, plugins:{{ legend:{{display:false}} }}, scales:{{ x:{{display:false}}, y:{{display:false}} }} }}
    }});

    // Overview chart
    new Chart(document.getElementById('overview-chart'), {{
      type: 'line',
      data: {{ labels: CD.price.labels, datasets: [lineDataset('{L["close"]}', CD.price.prices, '#6366f1', true)] }},
      options: baseOpts
    }});

    // Market price chart
    new Chart(document.getElementById('price-chart'), {{
      type: 'line',
      data: {{ labels: CD.price.labels, datasets: [lineDataset('{L["close_90d"]}', CD.price.prices, '#06b6d4', true)] }},
      options: baseOpts
    }});
  }}

  // RSI chart
  if (CD.rsi.labels.length > 0) {{
    var rsiOpts = JSON.parse(JSON.stringify(baseOpts));
    rsiOpts.scales.y.min = 0; rsiOpts.scales.y.max = 100;
    new Chart(document.getElementById('rsi-chart'), {{
      type: 'line',
      data: {{ labels: CD.rsi.labels, datasets: [
        lineDataset('RSI', CD.rsi.values, '#f59e0b', false),
        {{ type:'line', label:'{L["overbought_70"]}', data: CD.rsi.labels.map(function(){{return 70;}}), borderColor:'rgba(244,63,94,0.4)', borderDash:[4,4], pointRadius:0, borderWidth:1 }},
        {{ type:'line', label:'{L["oversold_30"]}', data: CD.rsi.labels.map(function(){{return 30;}}), borderColor:'rgba(16,185,129,0.4)', borderDash:[4,4], pointRadius:0, borderWidth:1 }}
      ] }},
      options: rsiOpts
    }});
  }}

  // MACD chart
  if (CD.macd.labels.length > 0) {{
    new Chart(document.getElementById('macd-chart'), {{
      type: 'bar',
      data: {{ labels: CD.macd.labels, datasets: [
        {{ type:'bar', label:'Histogram', data: CD.macd.histogram,
           backgroundColor: CD.macd.histogram.map(function(v) {{ return v >= 0 ? 'rgba(16,185,129,0.5)' : 'rgba(244,63,94,0.5)'; }}) }},
        lineDataset('MACD', CD.macd.macd, '#6366f1', false),
        lineDataset('Signal', CD.macd.signal, '#f59e0b', false)
      ] }},
      options: baseOpts
    }});
  }}

  // Sentiment doughnut
  new Chart(document.getElementById('sentiment-chart'), {{
    type: 'doughnut',
    data: {{
      labels: ['Bullish', 'Bearish', 'Unlabeled'],
      datasets: [{{ data: [CD.sentiment.bullish, CD.sentiment.bearish, CD.sentiment.unlabeled],
                   backgroundColor: ['#10b981','#f43f5e','#8b949e'], borderWidth: 0 }}]
    }},
    options: {{ responsive:true, plugins:{{ legend:{{ labels:{{ color:textColor }} }} }} }}
  }});

  // Risk horizontal bar
  new Chart(document.getElementById('risk-chart'), {{
    type: 'bar',
    data: {{
      labels: ['Aggressive', 'Conservative', 'Neutral'],
      datasets: [{{ data:[3,1,2], backgroundColor:['#f43f5e','#10b981','#6366f1'], borderWidth:0 }}]
    }},
    options: {{
      indexAxis: 'y', responsive: true,
      plugins: {{ legend: {{ display: false }} }},
      scales: {{ x: {{ display:false }}, y: {{ ticks: {{ color: textColor }} }} }}
    }}
  }});
}}
</script>
</body>
</html>"""


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Render TradingAgentsCC HTML report.")
    parser.add_argument("input", help="Path to analysis JSON")
    parser.add_argument("output", help="Path to write HTML output")
    parser.add_argument("--lang", choices=["ko", "en"], default="ko",
                        help="Output language for section labels (default: ko)")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    chartjs_src = fetch_chartjs()

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    html = generate_html(data, chartjs_src, lang=args.lang)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ {LABELS[args.lang]['report_saved']}: {args.output}")


if __name__ == "__main__":
    main()
