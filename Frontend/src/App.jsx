import { useEffect, useMemo, useState, useCallback } from "react";
import { API_BASE_URL } from "./config/api.js";

/* ─────────────────────────────────────────────
   Constants
───────────────────────────────────────────── */
const defaultParamsByStrategy = {
  sma:       { fast: 10, slow: 30 },
  rsi:       { rsi_period: 14, overbought: 70, oversold: 30 },
  macd:      { fast: 12, slow: 26, signal: 9 },
  bollinger: { period: 20, devfactor: 2 },
};

const defaultCustomCode = `import backtrader as bt

class MyCustomStrategy(bt.Strategy):
    params = (("threshold", 0.01),)

    def __init__(self):
        self.trade_log = []

    def next(self):
        if not self.position and self.data.close[0] > self.data.open[0] * (1 + self.params.threshold):
            self.buy()
            self.trade_log.append({"action": "BUY", "price": self.data.close[0]})
        elif self.position and self.data.close[0] < self.data.open[0] * (1 - self.params.threshold):
            self.sell()
            self.trade_log.append({"action": "SELL", "price": self.data.close[0]})
`;

const oneOffCustomCode = `import backtrader as bt

class TempStrategy(bt.Strategy):
    def __init__(self):
        self.trade_log = []

    def next(self):
        if not self.position and self.data.close[0] > self.data.open[0]:
            self.buy()
            self.trade_log.append({"action": "BUY", "price": self.data.close[0]})
        elif self.position and self.data.close[0] < self.data.open[0]:
            self.sell()
            self.trade_log.append({"action": "SELL", "price": self.data.close[0]})
`;

const TABS = [
  { id: "backtest", label: "Backtest" },
  { id: "builder",  label: "Strategy Builder" },
  { id: "sandbox",  label: "Quick Sandbox" },
  { id: "analyzer", label: "Report Analyzer" },
];

/* ─────────────────────────────────────────────
   Helpers
───────────────────────────────────────────── */
function tryParseJson(text) {
  try {
    return JSON.parse(text.trim() || "{}");
  } catch {
    return null;
  }
}

/** Format a metric value for display */
function formatMetricValue(key, val) {
  if (typeof val !== "number") return String(val);
  const isPercent = key.includes("return") || key.includes("rate") || key.includes("drawdown");
  if (isPercent) return `${(val * 100).toFixed(2)}%`;
  if (Math.abs(val) > 1000) return val.toLocaleString(undefined, { maximumFractionDigits: 2 });
  return val.toFixed(4);
}

/** Is a metric value "positive" (green) or "negative" (red)? */
function metricSentiment(key, val) {
  if (typeof val !== "number") return "neutral";
  const isInverse = key.includes("drawdown") || key.includes("loss");
  return isInverse ? (val <= 0 ? "positive" : "negative") : (val >= 0 ? "positive" : "negative");
}

/**
 * Render analysis text: split on double-newlines, detect section headers
 * (lines ending with ":" or all-caps short lines), bold key terms, etc.
 */
function parseAnalysisText(text) {
  if (!text || typeof text !== "string") return [];
  const blocks = text.split(/\n{2,}/);
  return blocks.map((block, i) => {
    const lines = block.trim().split("\n");
    // Detect heading: single short line ending with colon, or ALL CAPS
    if (
      lines.length === 1 &&
      (lines[0].endsWith(":") || lines[0] === lines[0].toUpperCase()) &&
      lines[0].length < 80
    ) {
      return { type: "heading", text: lines[0].replace(/:$/, ""), key: i };
    }
    // Detect bullet list
    if (lines.every(l => /^[-•*]\s/.test(l.trim()))) {
      return { type: "bullets", items: lines.map(l => l.replace(/^[-•*]\s/, "").trim()), key: i };
    }
    // Detect numbered list
    if (lines.every(l => /^\d+[.)]\s/.test(l.trim()))) {
      return { type: "numbered", items: lines.map(l => l.replace(/^\d+[.)]\s/, "").trim()), key: i };
    }
    // Plain paragraph
    return { type: "paragraph", text: block.trim(), key: i };
  }).filter(b => (b.text || b.items?.length));
}

/* ─────────────────────────────────────────────
   Sub-components
───────────────────────────────────────────── */
function Field({ label, children, style }) {
  return (
    <label className="field" style={style}>
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}

function StatusMsg({ s }) {
  if (!s.msg) return null;
  return <span className={`status-msg ${s.ok ? "ok" : "err"}`}>{s.msg}</span>;
}

/** Render structured analysis text */
function AnalysisRenderer({ text }) {
  const blocks = parseAnalysisText(text);
  if (!blocks.length) return <p className="analysis-empty">No analysis content.</p>;
  return (
    <div className="analysis-body">
      {blocks.map(b => {
        if (b.type === "heading") {
          return <h4 className="analysis-heading" key={b.key}>{b.text}</h4>;
        }
        if (b.type === "bullets") {
          return (
            <ul className="analysis-list" key={b.key}>
              {b.items.map((item, j) => <li key={j}>{item}</li>)}
            </ul>
          );
        }
        if (b.type === "numbered") {
          return (
            <ol className="analysis-list analysis-list--ordered" key={b.key}>
              {b.items.map((item, j) => <li key={j}>{item}</li>)}
            </ol>
          );
        }
        return <p className="analysis-para" key={b.key}>{b.text}</p>;
      })}
    </div>
  );
}

/** Render trade log table */
function TradeLog({ trades }) {
  if (!Array.isArray(trades) || trades.length === 0) return null;
  return (
    <div className="trade-log">
      <h4 className="section-subhead">Trade Log <span className="badge">{trades.length}</span></h4>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              {Object.keys(trades[0]).map(k => <th key={k}>{k.replace(/_/g, " ")}</th>)}
            </tr>
          </thead>
          <tbody>
            {trades.map((row, i) => (
              <tr key={i}>
                {Object.entries(row).map(([k, v]) => (
                  <td key={k} className={
                    (k === "action" && v === "BUY") ? "cell-buy" :
                    (k === "action" && v === "SELL") ? "cell-sell" : ""
                  }>
                    {typeof v === "number" ? v.toLocaleString(undefined, { maximumFractionDigits: 4 }) : String(v)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/** Render metrics grid with color-coded values */
function MetricsGrid({ metrics }) {
  if (!metrics || typeof metrics !== "object") return null;
  const entries = Object.entries(metrics);
  if (!entries.length) return null;
  return (
    <div className="metrics-section">
      <h4 className="section-subhead">Performance Metrics</h4>
      <div className="metrics-grid">
        {entries.map(([k, v]) => {
          const sentiment = metricSentiment(k, v);
          return (
            <div className="metric" key={k}>
              <span className={`metric-val metric-val--${sentiment}`}>
                {formatMetricValue(k, v)}
              </span>
              <span className="metric-key">{k.replace(/_/g, " ")}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Render generic result payload intelligently */
function ResultRenderer({ payload, title }) {
  if (!payload) return null;

  const { metrics, analysis, trade_log, trades, message, stock_name, ...rest } = payload;

  // Remove internal/noisy keys from "other" display
  const otherKeys = Object.keys(rest).filter(
    k => !["status", "strategy", "ticker"].includes(k)
  );

  return (
    <div className="results-card">
      <div className="results-header">
        <span className="results-badge">
          {analysis ? "📊 Analysis" : "🔬 Backtest"}
        </span>
        <p className="results-title">{title}</p>
        {message && <p className="results-message">{message}</p>}
      </div>

      {/* Metrics */}
      <MetricsGrid metrics={metrics} />

      {/* AI Analysis text — properly structured */}
      {analysis && (
        <div className="analysis-section">
          <h4 className="section-subhead">
            AI Analysis
            {stock_name && <span className="badge" style={{ marginLeft: "0.5rem" }}>{stock_name}</span>}
          </h4>
          <AnalysisRenderer text={analysis} />
        </div>
      )}

      {/* Trade log */}
      <TradeLog trades={trade_log ?? trades} />

      {/* Remaining fields as collapsible JSON */}
      {otherKeys.length > 0 && (
        <details className="raw-details">
          <summary>Raw response data</summary>
          <pre className="result-pre">
            {JSON.stringify(
              Object.fromEntries(otherKeys.map(k => [k, rest[k]])),
              null, 2
            )}
          </pre>
        </details>
      )}
    </div>
  );
}

/* ─────────────────────────────────────────────
   App
───────────────────────────────────────────── */
export default function App() {
  const [activeTab, setActiveTab]       = useState("backtest");
  const [apiStatus, setApiStatus]       = useState("connecting");
  const [strategies, setStrategies]     = useState([]);
  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [strategyParamsText, setStrategyParamsText] = useState("{}");
  const [resultPayload, setResultPayload] = useState(null);
  const [resultTitle, setResultTitle]     = useState("");
  const [lastMetrics, setLastMetrics]     = useState(null);

  const [backtestStatus, setBacktestStatus] = useState({ msg: "", ok: true });
  const [customStatus,   setCustomStatus]   = useState({ msg: "", ok: true });
  const [oneOffStatus,   setOneOffStatus]   = useState({ msg: "", ok: true });
  const [analyzerStatus, setAnalyzerStatus] = useState({ msg: "", ok: true });

  const [loading, setLoading] = useState({
    backtest: false, custom: false, oneoff: false, analyzer: false,
  });

  const [backtestForm, setBacktestForm] = useState({
    ticker: "AAPL", start_date: "2020-01-01", end_date: "2023-01-01",
    cash: "100000", plot: false,
  });

  const [customForm, setCustomForm] = useState({ name: "", code: defaultCustomCode });

  const [oneOffForm, setOneOffForm] = useState({
    ticker: "MSFT", start_date: "2021-01-01", end_date: "2022-01-01",
    strategy: "temp_strategy", cash: "50000", plot: false, code: oneOffCustomCode,
  });

  const [analyzerForm, setAnalyzerForm] = useState({ stock_name: "IRCTC", no_of_agents: 3 });

  const stats = useMemo(() => [
    { label: "Available Strategies", value: strategies.length || "—" },
    {
      label: "Last Total Return",
      value: lastMetrics
        ? formatMetricValue("total_return", lastMetrics.total_return)
        : "—",
    },
    {
      label: "Last Win Rate",
      value: lastMetrics
        ? formatMetricValue("win_rate", lastMetrics.win_rate)
        : "—",
    },
  ], [strategies, lastMetrics]);

  /* ── API helpers ── */
  const apiRequest = useCallback(async (path, options = {}) => {
    const res = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data?.detail ?? `HTTP ${res.status}`;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
    }
    return data;
  }, []);

  const loadStrategies = useCallback(async () => {
    const data = await apiRequest("/strategies");
    const list = Array.isArray(data.strategies) ? data.strategies : [];
    setStrategies(list);
    if (list.length > 0 && !selectedStrategy) {
      setSelectedStrategy(list[0]);
      setStrategyParamsText(JSON.stringify(defaultParamsByStrategy[list[0]] ?? {}, null, 2));
    }
    return list;
  }, [apiRequest, selectedStrategy]);

  const connectWorkspace = useCallback(async () => {
    setApiStatus("connecting");
    try {
      await loadStrategies();
      setApiStatus("online");
    } catch (err) {
      setApiStatus(`offline: ${err.message}`);
      setStrategies([]);
    }
  }, [loadStrategies]);

  useEffect(() => { connectWorkspace(); }, [connectWorkspace]);

  function onStrategyChange(name) {
    setSelectedStrategy(name);
    setStrategyParamsText(JSON.stringify(defaultParamsByStrategy[name] ?? {}, null, 2));
  }

  function showResult(title, payload) {
    setLastMetrics(payload?.metrics ?? null);
    setResultTitle(title);
    setResultPayload(payload);
  }

  /* ── Form submissions ── */
  async function submitBacktest(e) {
    e.preventDefault();
    if (!selectedStrategy) {
      setBacktestStatus({ msg: "No strategy selected — check backend connection.", ok: false });
      return;
    }
    const params = tryParseJson(strategyParamsText);
    if (params === null) {
      setBacktestStatus({ msg: "Strategy Parameters JSON is invalid.", ok: false });
      return;
    }
    setLoading(l => ({ ...l, backtest: true }));
    setBacktestStatus({ msg: "Running simulation…", ok: true });
    try {
      const data = await apiRequest("/run_backtest", {
        method: "POST",
        body: JSON.stringify({
          ticker: backtestForm.ticker.trim(), start_date: backtestForm.start_date,
          end_date: backtestForm.end_date, strategy: selectedStrategy,
          cash: Number(backtestForm.cash), strategy_params: params, plot: backtestForm.plot,
        }),
      });
      setBacktestStatus({ msg: "Completed successfully.", ok: true });
      showResult("Backtest Result", data);
    } catch (err) {
      setBacktestStatus({ msg: `Failed: ${err.message}`, ok: false });
    } finally {
      setLoading(l => ({ ...l, backtest: false }));
    }
  }

  async function submitCustomStrategy(e) {
    e.preventDefault();
    setLoading(l => ({ ...l, custom: true }));
    setCustomStatus({ msg: "Publishing strategy…", ok: true });
    try {
      const data = await apiRequest("/custom_strategy", {
        method: "POST",
        body: JSON.stringify({ name: customForm.name.trim(), code: customForm.code }),
      });
      setCustomStatus({ msg: data.message || "Strategy saved.", ok: true });
      showResult("Custom Strategy Created", data);
      await loadStrategies();
    } catch (err) {
      setCustomStatus({ msg: `Failed: ${err.message}`, ok: false });
    } finally {
      setLoading(l => ({ ...l, custom: false }));
    }
  }

  async function submitOneOffBacktest(e) {
    e.preventDefault();
    setLoading(l => ({ ...l, oneoff: true }));
    setOneOffStatus({ msg: "Running one-off simulation…", ok: true });
    try {
      const data = await apiRequest("/run_custom_backtest", {
        method: "POST",
        body: JSON.stringify({
          ticker: oneOffForm.ticker.trim(), start_date: oneOffForm.start_date,
          end_date: oneOffForm.end_date, strategy: oneOffForm.strategy.trim(),
          cash: Number(oneOffForm.cash), plot: oneOffForm.plot,
          strategy_params: { code: oneOffForm.code },
        }),
      });
      setOneOffStatus({ msg: "Completed successfully.", ok: true });
      showResult("One-off Backtest Result", data);
    } catch (err) {
      setOneOffStatus({ msg: `Failed: ${err.message}`, ok: false });
    } finally {
      setLoading(l => ({ ...l, oneoff: false }));
    }
  }

  async function submitAnalysis(e) {
    e.preventDefault();
    setLoading(l => ({ ...l, analyzer: true }));
    setAnalyzerStatus({ msg: "Analyzing annual report…", ok: true });
    try {
      const data = await apiRequest("/analyze", {
        method: "POST",
        body: JSON.stringify({
          stock_name: analyzerForm.stock_name.trim(),
          no_of_agents: Number(analyzerForm.no_of_agents) || 1,
        }),
      });
      setAnalyzerStatus({ msg: "Analysis complete.", ok: true });
      showResult(`Annual Report Analysis — ${data.stock_name}`, data);
    } catch (err) {
      setAnalyzerStatus({ msg: `Failed: ${err.message}`, ok: false });
    } finally {
      setLoading(l => ({ ...l, analyzer: false }));
    }
  }

  const statusColor =
    apiStatus === "online"     ? "#22c55e" :
    apiStatus === "connecting" ? "#f59e0b" : "#ef4444";

  /* ── Render ── */
  return (
    <>
      <style>{CSS}</style>
      <div className="app">
        {/* Topbar */}
        <nav className="topbar">
          <span className="brand">⬡ AlgoTrader</span>
          <div className="topbar-right">
            <span className="status-dot" style={{ background: statusColor }} />
            <span className="status-label">
              {apiStatus === "connecting" ? "Connecting…"
               : apiStatus === "online"  ? "Online"
               : "Offline"}
            </span>
          </div>
        </nav>

        {/* Hero */}
        <header className="hero">
          <p className="eyebrow">Algorithmic Trading Studio</p>
          <h1>Design, test, and launch<br />strategy ideas with confidence.</h1>
          <p className="hero-sub">
            Professional-grade backtests, custom Python strategies, and AI-powered annual report analysis — all in one place.
          </p>
          <div className="hero-actions">
            <button className="btn-primary" onClick={() => setActiveTab("backtest")}>Start Backtesting</button>
            <button className="btn-ghost"   onClick={() => setActiveTab("builder")}>Build a Strategy</button>
            <button className="btn-ghost"   onClick={() => setActiveTab("analyzer")}>Analyze Reports</button>
          </div>
        </header>

        {/* Stats */}
        <section className="stats-row">
          {stats.map(s => (
            <div className="stat-card" key={s.label}>
              <span className="stat-value">{s.value}</span>
              <span className="stat-label">{s.label}</span>
            </div>
          ))}
        </section>

        {/* Feature strip */}
        <section className="features">
          {[
            { icon: "⚡", title: "Reliable engine", body: "Consistent historical tests across built-in and custom strategies." },
            { icon: "🐍", title: "Custom Python strategies", body: "Write backtrader code directly and keep reusable strategies in your workspace." },
            { icon: "📊", title: "Actionable metrics", body: "Portfolio value, total return, win rate, drawdown, and full trade logs." },
          ].map(f => (
            <div className="feature-card" key={f.title}>
              <span className="feature-icon">{f.icon}</span>
              <h3>{f.title}</h3>
              <p>{f.body}</p>
            </div>
          ))}
        </section>

        {/* Studio */}
        <section className="studio">
          <div className="studio-head">
            <h2>Trading Studio</h2>
            <div className="tabs" role="tablist">
              {TABS.map(t => (
                <button
                  key={t.id} role="tab"
                  aria-selected={activeTab === t.id}
                  className={`tab ${activeTab === t.id ? "active" : ""}`}
                  onClick={() => setActiveTab(t.id)}
                >{t.label}</button>
              ))}
            </div>
          </div>

          <div className="panel" role="tabpanel">
            {/* BACKTEST */}
            {activeTab === "backtest" && (
              <form onSubmit={submitBacktest}>
                <div className="grid-3">
                  <Field label="Symbol">
                    <input required value={backtestForm.ticker}
                      onChange={e => setBacktestForm(f => ({ ...f, ticker: e.target.value }))} />
                  </Field>
                  <Field label="Start Date">
                    <input type="date" required value={backtestForm.start_date}
                      onChange={e => setBacktestForm(f => ({ ...f, start_date: e.target.value }))} />
                  </Field>
                  <Field label="End Date">
                    <input type="date" required value={backtestForm.end_date}
                      onChange={e => setBacktestForm(f => ({ ...f, end_date: e.target.value }))} />
                  </Field>
                </div>
                <div className="grid-3">
                  <Field label="Strategy">
                    <select required value={selectedStrategy} onChange={e => onStrategyChange(e.target.value)}
                      disabled={strategies.length === 0}>
                      {strategies.length === 0
                        ? <option value="">No strategies loaded — check connection</option>
                        : strategies.map(s => <option key={s} value={s}>{s}</option>)
                      }
                    </select>
                  </Field>
                  <Field label="Initial Capital ($)">
                    <input type="number" min="0" step="0.01" required value={backtestForm.cash}
                      onChange={e => setBacktestForm(f => ({ ...f, cash: e.target.value }))} />
                  </Field>
                  <Field label=" ">
                    <label className="checkbox-row">
                      <input type="checkbox" checked={backtestForm.plot}
                        onChange={e => setBacktestForm(f => ({ ...f, plot: e.target.checked }))} />
                      Open chart preview
                    </label>
                  </Field>
                </div>
                <Field label="Strategy Parameters (JSON)">
                  <textarea rows={6} value={strategyParamsText}
                    onChange={e => setStrategyParamsText(e.target.value)}
                    style={{ fontFamily: "monospace", fontSize: "0.85rem" }} />
                  {tryParseJson(strategyParamsText) === null && (
                    <span className="field-error">⚠ Invalid JSON</span>
                  )}
                </Field>
                <div className="form-footer">
                  <button className="btn-primary" type="submit" disabled={loading.backtest}>
                    {loading.backtest ? "Running…" : "Run Backtest"}
                  </button>
                  <StatusMsg s={backtestStatus} />
                </div>
              </form>
            )}

            {/* BUILDER */}
            {activeTab === "builder" && (
              <form onSubmit={submitCustomStrategy}>
                <Field label="Strategy Name">
                  <input required placeholder="my_custom_strategy" value={customForm.name}
                    onChange={e => setCustomForm(f => ({ ...f, name: e.target.value }))} />
                </Field>
                <Field label="Strategy Code (Python / backtrader)">
                  <textarea rows={16} required value={customForm.code}
                    onChange={e => setCustomForm(f => ({ ...f, code: e.target.value }))}
                    style={{ fontFamily: "monospace", fontSize: "0.85rem" }} />
                </Field>
                <div className="form-footer">
                  <button className="btn-primary" type="submit" disabled={loading.custom}>
                    {loading.custom ? "Saving…" : "Save Strategy"}
                  </button>
                  <StatusMsg s={customStatus} />
                </div>
              </form>
            )}

            {/* SANDBOX */}
            {activeTab === "sandbox" && (
              <form onSubmit={submitOneOffBacktest}>
                <div className="grid-3">
                  <Field label="Symbol">
                    <input required value={oneOffForm.ticker}
                      onChange={e => setOneOffForm(f => ({ ...f, ticker: e.target.value }))} />
                  </Field>
                  <Field label="Start Date">
                    <input type="date" required value={oneOffForm.start_date}
                      onChange={e => setOneOffForm(f => ({ ...f, start_date: e.target.value }))} />
                  </Field>
                  <Field label="End Date">
                    <input type="date" required value={oneOffForm.end_date}
                      onChange={e => setOneOffForm(f => ({ ...f, end_date: e.target.value }))} />
                  </Field>
                </div>
                <div className="grid-3">
                  <Field label="Temporary Strategy Name">
                    <input required value={oneOffForm.strategy}
                      onChange={e => setOneOffForm(f => ({ ...f, strategy: e.target.value }))} />
                  </Field>
                  <Field label="Initial Capital ($)">
                    <input type="number" min="0" step="0.01" required value={oneOffForm.cash}
                      onChange={e => setOneOffForm(f => ({ ...f, cash: e.target.value }))} />
                  </Field>
                  <Field label=" ">
                    <label className="checkbox-row">
                      <input type="checkbox" checked={oneOffForm.plot}
                        onChange={e => setOneOffForm(f => ({ ...f, plot: e.target.checked }))} />
                      Open chart preview
                    </label>
                  </Field>
                </div>
                <Field label="One-off Code (Python / backtrader)">
                  <textarea rows={14} required value={oneOffForm.code}
                    onChange={e => setOneOffForm(f => ({ ...f, code: e.target.value }))}
                    style={{ fontFamily: "monospace", fontSize: "0.85rem" }} />
                </Field>
                <div className="form-footer">
                  <button className="btn-primary" type="submit" disabled={loading.oneoff}>
                    {loading.oneoff ? "Running…" : "Run Sandbox Backtest"}
                  </button>
                  <StatusMsg s={oneOffStatus} />
                </div>
              </form>
            )}

            {/* ANALYZER */}
            {activeTab === "analyzer" && (
              <form onSubmit={submitAnalysis}>
                <div className="grid-3">
                  <Field label="Stock Symbol">
                    <input required value={analyzerForm.stock_name}
                      onChange={e => setAnalyzerForm(f => ({ ...f, stock_name: e.target.value }))} />
                  </Field>
                  <Field label="Number of Agents (1–20)">
                    <input type="number" min="1" max="20" required
                      value={analyzerForm.no_of_agents}
                      onChange={e => setAnalyzerForm(f => ({ ...f, no_of_agents: e.target.value }))} />
                  </Field>
                </div>
                <div className="form-footer">
                  <button className="btn-primary" type="submit" disabled={loading.analyzer}>
                    {loading.analyzer ? "Analyzing…" : "Analyze Annual Report"}
                  </button>
                  <StatusMsg s={analyzerStatus} />
                </div>
              </form>
            )}
          </div>
        </section>

        {/* Results — now uses ResultRenderer */}
        <section className="results-section">
          <h2>Run Results</h2>
          {resultPayload
            ? <ResultRenderer payload={resultPayload} title={resultTitle} />
            : (
              <div className="results-card empty">
                <p>Run a backtest or analysis to see results here.</p>
              </div>
            )
          }
        </section>
      </div>
    </>
  );
}

/* ─────────────────────────────────────────────
   CSS
───────────────────────────────────────────── */
const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@600;700;800&family=DM+Sans:wght@400;500&display=swap');

  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --bg:       #0b0e14;
    --surface:  #111620;
    --border:   #1e2534;
    --accent:   #7effa0;
    --accent2:  #4f9eff;
    --text:     #e8ecf4;
    --muted:    #6b7793;
    --danger:   #ff6b6b;
    --positive: #22c55e;
    --negative: #ff6b6b;
    --radius:   10px;
    --font-head: 'Syne', sans-serif;
    --font-body: 'DM Sans', sans-serif;
    --font-mono: 'DM Mono', monospace;
  }

  body { background: var(--bg); color: var(--text); font-family: var(--font-body); }
  .app { max-width: 1100px; margin: 0 auto; padding: 0 1.5rem 5rem; }

  /* Topbar */
  .topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1.1rem 0; border-bottom: 1px solid var(--border);
    position: sticky; top: 0; background: var(--bg); z-index: 10;
  }
  .brand { font-family: var(--font-head); font-size: 1.15rem; font-weight: 800; color: var(--accent); letter-spacing: -0.02em; }
  .topbar-right { display: flex; align-items: center; gap: 0.5rem; }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .status-label { font-size: 0.8rem; color: var(--muted); font-family: var(--font-mono); }

  /* Hero */
  .hero { padding: 5rem 0 3.5rem; border-bottom: 1px solid var(--border); }
  .eyebrow { font-family: var(--font-mono); font-size: 0.75rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--accent); margin-bottom: 1.1rem; }
  .hero h1 { font-family: var(--font-head); font-size: clamp(2.2rem, 5vw, 3.5rem); font-weight: 800; line-height: 1.1; letter-spacing: -0.03em; color: var(--text); margin-bottom: 1.2rem; }
  .hero-sub { color: var(--muted); max-width: 560px; line-height: 1.7; margin-bottom: 2rem; }
  .hero-actions { display: flex; gap: 0.75rem; flex-wrap: wrap; }

  /* Buttons */
  .btn-primary { background: var(--accent); color: #0b0e14; font-family: var(--font-head); font-weight: 700; font-size: 0.88rem; border: none; border-radius: var(--radius); padding: 0.65rem 1.4rem; cursor: pointer; transition: opacity .15s; white-space: nowrap; }
  .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-primary:hover:not(:disabled) { opacity: 0.85; }

  .btn-ghost { background: transparent; color: var(--text); font-family: var(--font-head); font-weight: 600; font-size: 0.88rem; border: 1px solid var(--border); border-radius: var(--radius); padding: 0.65rem 1.4rem; cursor: pointer; transition: border-color .15s, color .15s; white-space: nowrap; }
  .btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-ghost:hover:not(:disabled) { border-color: var(--accent); color: var(--accent); }

  /* Stats */
  .stats-row { display: grid; grid-template-columns: repeat(3,1fr); gap: 1rem; padding: 2.5rem 0; }
  .stat-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.4rem 1.6rem; display: flex; flex-direction: column; gap: 0.35rem; }
  .stat-value { font-family: var(--font-head); font-size: 1.9rem; font-weight: 800; color: var(--accent); }
  .stat-label { font-size: 0.78rem; color: var(--muted); letter-spacing: 0.04em; text-transform: uppercase; }

  /* Features */
  .features { display: grid; grid-template-columns: repeat(3,1fr); gap: 1rem; padding-bottom: 3rem; border-bottom: 1px solid var(--border); }
  .feature-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.4rem 1.5rem; }
  .feature-icon { font-size: 1.5rem; display: block; margin-bottom: 0.7rem; }
  .feature-card h3 { font-family: var(--font-head); font-size: 1rem; font-weight: 700; margin-bottom: 0.5rem; }
  .feature-card p  { font-size: 0.85rem; color: var(--muted); line-height: 1.6; }

  /* Studio */
  .studio { padding: 3rem 0; border-bottom: 1px solid var(--border); }
  .studio-head { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 1rem; margin-bottom: 1.5rem; }
  .studio-head h2 { font-family: var(--font-head); font-size: 1.4rem; font-weight: 800; }
  .tabs { display: flex; gap: 0.25rem; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 4px; flex-wrap: wrap; }
  .tab { background: transparent; border: none; color: var(--muted); font-family: var(--font-body); font-size: 0.83rem; font-weight: 500; padding: 0.45rem 0.9rem; border-radius: 7px; cursor: pointer; transition: all .15s; }
  .tab.active { background: var(--accent); color: #0b0e14; font-weight: 700; }
  .tab:hover:not(.active) { color: var(--text); }
  .panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.75rem; }

  /* Form Elements */
  .grid-3 { display: grid; grid-template-columns: repeat(3,1fr); gap: 1rem; margin-bottom: 1rem; }
  .field { display: flex; flex-direction: column; gap: 0.45rem; margin-bottom: 1rem; }
  .field-label { font-size: 0.77rem; font-weight: 500; color: var(--muted); letter-spacing: 0.05em; text-transform: uppercase; }
  .field-error { font-size: 0.75rem; color: var(--danger); margin-top: 0.2rem; }
  input, select, textarea { width: 100%; background: var(--bg); color: var(--text); border: 1px solid var(--border); border-radius: 7px; padding: 0.6rem 0.75rem; font-family: var(--font-body); font-size: 0.9rem; transition: border-color .15s; outline: none; }
  input:focus, select:focus, textarea:focus { border-color: var(--accent2); }
  textarea { resize: vertical; }
  select option { background: var(--surface); }
  .checkbox-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.88rem; color: var(--muted); cursor: pointer; padding-top: 0.25rem; }
  .checkbox-row input { width: auto; }
  .form-footer { display: flex; align-items: center; gap: 1rem; margin-top: 0.5rem; }
  .status-msg { font-size: 0.83rem; font-family: var(--font-mono); }
  .status-msg.ok  { color: var(--accent); }
  .status-msg.err { color: var(--danger); }

  /* Results section */
  .results-section { padding: 3rem 0; border-bottom: 1px solid var(--border); }
  .results-section h2 { font-family: var(--font-head); font-size: 1.4rem; font-weight: 800; margin-bottom: 1.25rem; }
  .results-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); padding: 1.75rem; }
  .results-card.empty { color: var(--muted); font-size: 0.9rem; text-align: center; padding: 3rem; }

  .results-header { margin-bottom: 1.5rem; }
  .results-badge { font-family: var(--font-mono); font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; background: rgba(79,158,255,0.12); color: var(--accent2); border: 1px solid rgba(79,158,255,0.25); border-radius: 5px; padding: 0.2rem 0.55rem; display: inline-block; margin-bottom: 0.6rem; }
  .results-title { font-family: var(--font-head); font-size: 1.1rem; font-weight: 700; color: var(--text); margin-bottom: 0.35rem; }
  .results-message { font-size: 0.85rem; color: var(--accent); font-family: var(--font-mono); }

  /* Section subheads */
  .section-subhead { font-family: var(--font-head); font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--muted); margin-bottom: 0.85rem; display: flex; align-items: center; gap: 0.5rem; }
  .badge { font-family: var(--font-mono); font-size: 0.7rem; background: var(--border); color: var(--text); border-radius: 4px; padding: 0.15rem 0.45rem; font-weight: 400; letter-spacing: 0; }

  /* Metrics */
  .metrics-section { margin-bottom: 1.75rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border); }
  .metrics-grid { display: flex; flex-wrap: wrap; gap: 0.65rem; }
  .metric { background: var(--bg); border: 1px solid var(--border); border-radius: 7px; padding: 0.65rem 1rem; display: flex; flex-direction: column; gap: 0.2rem; min-width: 110px; }
  .metric-val { font-family: var(--font-mono); font-size: 1rem; font-weight: 500; }
  .metric-val--positive { color: var(--positive); }
  .metric-val--negative { color: var(--negative); }
  .metric-val--neutral  { color: var(--text); }
  .metric-key { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); }

  /* Analysis */
  .analysis-section { margin-bottom: 1.75rem; padding-bottom: 1.5rem; border-bottom: 1px solid var(--border); }
  .analysis-body { background: var(--bg); border: 1px solid var(--border); border-radius: 8px; padding: 1.25rem 1.4rem; display: flex; flex-direction: column; gap: 0.85rem; max-height: 520px; overflow-y: auto; }
  .analysis-heading { font-family: var(--font-head); font-size: 0.95rem; font-weight: 700; color: var(--accent2); padding-top: 0.35rem; border-top: 1px solid var(--border); margin-top: 0.35rem; }
  .analysis-heading:first-child { border-top: none; margin-top: 0; padding-top: 0; }
  .analysis-para { font-size: 0.9rem; color: var(--text); line-height: 1.75; }
  .analysis-list { padding-left: 1.3rem; display: flex; flex-direction: column; gap: 0.35rem; }
  .analysis-list li { font-size: 0.88rem; color: var(--text); line-height: 1.65; }
  .analysis-list--ordered { list-style-type: decimal; }
  .analysis-empty { color: var(--muted); font-size: 0.9rem; }

  /* Trade log */
  .trade-log { margin-bottom: 1.75rem; }
  .table-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 0.83rem; font-family: var(--font-mono); }
  thead tr { background: var(--bg); border-bottom: 1px solid var(--border); }
  th { padding: 0.6rem 0.9rem; text-align: left; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); font-weight: 500; white-space: nowrap; }
  td { padding: 0.55rem 0.9rem; border-bottom: 1px solid var(--border); color: var(--text); white-space: nowrap; }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr:hover { background: rgba(255,255,255,0.025); }
  .cell-buy  { color: var(--positive); font-weight: 600; }
  .cell-sell { color: var(--negative); font-weight: 600; }

  /* Raw details */
  .raw-details { margin-top: 0.5rem; }
  .raw-details summary { font-size: 0.8rem; color: var(--muted); cursor: pointer; padding: 0.4rem 0; font-family: var(--font-mono); }
  .raw-details summary:hover { color: var(--text); }
  .result-pre { font-family: var(--font-mono); font-size: 0.78rem; color: var(--muted); white-space: pre-wrap; word-break: break-all; line-height: 1.7; max-height: 320px; overflow-y: auto; padding-top: 0.75rem; }

  /* Responsive */
  @media (max-width: 700px) {
    .stats-row, .features, .grid-3 { grid-template-columns: 1fr; }
    .studio-head { flex-direction: column; }
    .tabs { width: 100%; }
  }
`;