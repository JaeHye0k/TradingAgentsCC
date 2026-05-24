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

    rsi = _ind("rsi")
    macd_line = _ind("macd")
    macd_sig = _ind("macds")
    macd_hist = _ind("macdh")

    st = sentiment.get("stocktwits") or {}
    sent = {
        "bullish": st.get("bullish", 0),
        "bearish": st.get("bearish", 0),
        "unlabeled": st.get("unlabeled", 0),
    }

    if not price["labels"]:
        print("[warn] market_data.price_history.close not found — overview/price/sparkline charts disabled.", file=sys.stderr)
    if not rsi["labels"]:
        print("[warn] market_data.indicators.rsi not found — RSI chart disabled.", file=sys.stderr)
    if not macd_line["labels"]:
        print("[warn] market_data.indicators.macd not found — MACD chart disabled.", file=sys.stderr)
    if (sent["bullish"] + sent["bearish"] + sent["unlabeled"]) == 0:
        print("[warn] sentiment_data.stocktwits empty — sentiment doughnut will be blank.", file=sys.stderr)

    return {
        "price": price,
        "rsi": rsi,
        "macd": {
            "labels": macd_line["labels"],
            "macd": macd_line["values"],
            "signal": macd_sig["values"],
            "histogram": macd_hist["values"],
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


def _checklist_html(items: list[str], id_prefix: str) -> str:
    if not items:
        return '<p class="muted-text">항목이 없습니다.</p>'
    rows = "".join(
        f'<label class="check-item"><input type="checkbox" id="{id_prefix}-{i}"> <span>{item}</span></label>\n'
        for i, item in enumerate(items)
    )
    return f'<div class="checklist">{rows}</div>'


def _debate_html(bull_reports: list[str], bear_reports: list[str]) -> str:
    rounds = max(len(bull_reports), len(bear_reports))
    if rounds == 0:
        return '<p class="muted-text">토론 데이터가 없습니다.</p>'
    parts = []
    for r in range(rounds):
        parts.append(f'<details open><summary class="debate-summary">라운드 {r + 1}</summary>\n')
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
ol { list-style-position: inside; }
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


def generate_html(data: dict, chartjs_src: str | None) -> str:
    ticker = _html.escape(data["ticker"])
    date = _html.escape(data["date"])
    r = data["reports"]

    chart_data = build_chart_data(data)
    decision, dec_color = detect_decision(r.get("final_decision", ""))

    charts_ok = "true" if chartjs_src else "false"
    chartjs_tag = f"<script>{chartjs_src}</script>" if chartjs_src else ""

    checklist_html = _checklist_html(r.get("trading_checklist", []), "trade")
    reasons_html = _checklist_html(r.get("decision_reasons", []), "dec")
    debate_html = _debate_html(r.get("bull", []), r.get("bear", []))

    def section(content_key: str) -> str:
        return md_to_html(r.get(content_key, ""))

    return f"""<!DOCTYPE html>
<html lang="ko">
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
    <div class="label">최종 결정</div>
    <div class="big-badge">{decision}</div>
  </div>
  <p class="section-title">분석 요약</p>
  <div class="report-text">{section("final_decision")}</div>
</div>

<div id="market" class="tab-panel">
  <p class="section-title">주가 (90일)</p>
  <div class="chart-wrap"><canvas id="price-chart"></canvas></div>
  <p class="section-title">RSI</p>
  <div class="chart-wrap"><canvas id="rsi-chart"></canvas></div>
  <p class="section-title">MACD</p>
  <div class="chart-wrap"><canvas id="macd-chart"></canvas></div>
  <p class="section-title">시장 분석</p>
  <div class="report-text">{section("market")}</div>
</div>

<div id="news" class="tab-panel">
  <div class="report-text">{section("news")}</div>
</div>

<div id="fundamentals" class="tab-panel">
  <div class="report-text">{section("fundamentals")}</div>
</div>

<div id="sentiment" class="tab-panel">
  <p class="section-title">감성 분포 (StockTwits)</p>
  <div class="chart-wrap narrow"><canvas id="sentiment-chart"></canvas></div>
  <p class="section-title">소셜 분석</p>
  <div class="report-text">{section("social")}</div>
</div>

<div id="research" class="tab-panel">
  <p class="section-title">Bull / Bear 토론</p>
  {debate_html}
  <p class="section-title">Research Manager 합성</p>
  <div class="report-text">{section("investment_plan")}</div>
</div>

<div id="trading" class="tab-panel">
  <p class="section-title">트레이딩 체크리스트</p>
  {checklist_html}
  <p class="section-title">트레이딩 플랜</p>
  <div class="report-text">{section("trading_plan")}</div>
</div>

<div id="risk" class="tab-panel">
  <p class="section-title">리스크 관점 비교</p>
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
    <div class="label">최종 결정</div>
    <div class="big-badge">{decision}</div>
  </div>
  <p class="section-title">결정 근거</p>
  {reasons_html}
  <p class="section-title">전문</p>
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
    plugins: {{ legend: {{ labels: {{ color: textColor }} }} }},
    scales: {{
      x: {{ ticks: {{ color: textColor, maxTicksLimit: 8 }}, grid: {{ color: gridColor }} }},
      y: {{ ticks: {{ color: textColor }}, grid: {{ color: gridColor }} }}
    }}
  }};

  function lineDataset(label, data, color, fill) {{
    return {{ type:'line', label:label, data:data, borderColor:color,
              backgroundColor: fill ? color.replace(')',',0.12)').replace('rgb','rgba') : 'transparent',
              borderWidth:2, pointRadius:0, fill:!!fill }};
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
      data: {{ labels: CD.price.labels, datasets: [lineDataset('종가', CD.price.prices, '#6366f1', true)] }},
      options: baseOpts
    }});

    // Market price chart
    new Chart(document.getElementById('price-chart'), {{
      type: 'line',
      data: {{ labels: CD.price.labels, datasets: [lineDataset('종가 (90일)', CD.price.prices, '#06b6d4', true)] }},
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
        {{ type:'line', label:'과매수(70)', data: CD.rsi.labels.map(function(){{return 70;}}), borderColor:'rgba(244,63,94,0.4)', borderDash:[4,4], pointRadius:0, borderWidth:1 }},
        {{ type:'line', label:'과매도(30)', data: CD.rsi.labels.map(function(){{return 30;}}), borderColor:'rgba(16,185,129,0.4)', borderDash:[4,4], pointRadius:0, borderWidth:1 }}
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
    if len(sys.argv) != 3:
        print("Usage: render_html.py <input.json> <output.html>", file=sys.stderr)
        sys.exit(1)

    input_path, output_path = sys.argv[1], sys.argv[2]

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    chartjs_src = fetch_chartjs()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    html = generate_html(data, chartjs_src)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 보고서 저장됨: {output_path}")


if __name__ == "__main__":
    main()
