from dotenv import load_dotenv
import os
import re
import time
import json
import logging
import requests
import tempfile
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import pdfplumber
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import OpenAI

from models.request_models import BacktestRequest, CustomStrategyRequest, StrategyList
from engine.backtest_engine import run_backtest, get_available_strategies, register_custom_strategy
from engine.custom_strategy_engine import save_custom_strategy

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# CONFIGURATION  (prefer env-vars; fall back to literals for local dev)
# ─────────────────────────────────────────────

load_dotenv()

OPENROUTER_BASE_URL =  os.getenv("OPENROUTER_BASE_URL")
OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY")

NSE_BASE_URL = "https://www.nseindia.com"
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "application/json, text/plain, */*",
    "Referer": NSE_BASE_URL,
}

# Models to race — free/cheap models available via OpenRouter
RACE_MODELS = [
    "openai/gpt-4o-mini",
    "mistralai/mistral-small-2501",
    "meta-llama/llama-3-8b-instruct",
    "google/gemma-2-9b-it",
    "cohere/command-r-plus-08-2024",
    "anthropic/claude-3.5-mini",
    "openrouter/auto",
    "deepseek/deepseek-chat",
    "deepseek/deepseek-coder",
    "google/gemma-3-27b-it",
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-small-3.2-24b-instruct",
    "nvidia/llama-3.1-nemotron-nano-8b-instruct",
    "z-ai/glm-4-32b",
    "arcee-ai/arcee-nova",
    "qwen/qwen-2.5-72b-instruct",
    "qwen/qwen-2.5-coder-32b-instruct",
    "allenai/olmo-2-0325-32b-instruct",
    "mistralai/mistral-small-2501",
    "meta-llama/llama-3-8b-instruct",
    "google/gemma-2-9b-it",
    "deepseek/deepseek-r1",
    "cohere/command-r-plus-08-2024",
    "anthropic/claude-haiku-3-5",
    "mistralai/mixtral-8x7b-instruct",
]

# ─────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────

ANALYSIS_PROMPT = """
You are a highly rigorous financial analyst specializing in equity research.

Your task is to analyze the given annual report text and produce a structured, data-driven fundamental analysis.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Use ONLY information explicitly available in the provided text.
2. Do NOT assume, estimate, or fabricate any financial data.
3. If any metric is missing, clearly state: DATA UNAVAILABLE.
4. Avoid vague language. Be precise, analytical, and evidence-based.
5. No stock recommendations or target prices.
6. Keep analysis concise but insightful.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT (STRICT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. Key Financial Highlights
- Revenue: [value + trend or DATA UNAVAILABLE]
- Net Profit: [value + trend]
- EBITDA / Operating Margin: [value + trend]
- Net Profit Margin: [value + trend]
- EPS (if available): [value + trend]

---

## 2. Business Performance Summary
Provide a 4–6 sentence summary covering:
- Core business segments and performance
- Growth drivers
- Cost structure and efficiency
- Any notable operational improvements or declines

---

## 3. Growth Assessment
Classify overall growth as:
ACCELERATING / STEADY / SLOWING / DECLINING

Support with:
- Revenue trend
- Profit trend
- Margin trend

---

## 4. Financial Health Assessment
Evaluate based on available data:
- Leverage (Debt levels)
- Liquidity (if mentioned)
- Cash flow trends

Classify:
STRONG / MODERATE / WEAK

---

## 5. Major Risks and Opportunities

### Risks:
- List 3–5 key risks (macroeconomic, operational, regulatory, financial)

### Opportunities:
- List 3–5 growth opportunities (market expansion, new products, efficiency gains)

---

## 6. Management Commentary & Outlook
Summarize management's tone and direction:
- Expansion plans
- Strategic priorities
- Industry outlook
- Capital allocation approach

(Do NOT convert into predictions)

---

## 7. Overall Investment View (Fundamental Only)

Provide:
- One-line summary of business quality
- 3 key strengths
- 2 key concerns

Final classification:
BULLISH / BEARISH / NEUTRAL

---

## 8. Data Confidence Level
HIGH / MODERATE / LOW

---

Annual Report Text:
{text}
"""

# ─────────────────────────────────────────────
# PYDANTIC MODELS
# ─────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    stock_name: str = Field(
        ...,
        min_length=1,
        description="NSE stock symbol, e.g. RELIANCE or TATATECH.",
    )
    no_of_agents: int = Field(
        1,
        ge=1,
        le=len(RACE_MODELS),
        description="Number of analysis agents/models to race.",
    )


class AnalysisResponse(BaseModel):
    stock_name: str
    no_of_agents: int
    analysis: str


# ─────────────────────────────────────────────
# APP  (single instance — previously defined twice)
# ─────────────────────────────────────────────

app = FastAPI(
    title="Algo Trading + Annual Report Analyzer API",
    description="Backtest strategies and race AI agents over NSE annual reports.",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# OPENROUTER CLIENT
# ─────────────────────────────────────────────

def get_client() -> OpenAI:
    """Returns an OpenAI-compatible client pointed at OpenRouter."""
    if not OPENROUTER_API_KEY:
        raise ValueError(
            "OPENROUTER_API_KEY is not set. "
            "Export it as an env-var or set it in the config block."
        )
    return OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": "https://github.com/annual-report-analyzer",
            "X-Title": "Annual Report Analyzer",
        },
    )


# ─────────────────────────────────────────────
# STEP 1: Scrape Annual Report PDF Link from NSE
# ─────────────────────────────────────────────

def scrape_annual_report_link(symbol: str) -> str:
    """
    Scrapes the latest annual report PDF link for a given NSE stock symbol.
    NSE requires a cookie handshake before API calls will succeed.
    """
    log.info("[Step 1] Scraping annual report link for: %s", symbol)

    session = requests.Session()
    # Warm-up: NSE sets required cookies on the homepage
    try:
        session.get(NSE_BASE_URL, headers=NSE_HEADERS, timeout=10)
    except requests.RequestException:
        pass  # Proceed even if warm-up fails; cookies may still be set
    time.sleep(1)

    api_url = f"{NSE_BASE_URL}/api/annual-reports?index=equities&symbol={symbol}"
    response = session.get(api_url, headers=NSE_HEADERS, timeout=15)
    response.raise_for_status()

    data = response.json()
    reports = data.get("data", [])

    if not reports:
        raise ValueError(f"No annual reports found for symbol: {symbol}")

    # Most recent report is first in the list
    latest = reports[0]

    # NSE has used different key names across API versions — try all known ones
    pdf_url = (
        latest.get("fileName")
        or latest.get("pdfLink")
        or latest.get("link")
        or latest.get("fileUrl")
    )

    if not pdf_url:
        raise ValueError(
            f"Could not extract PDF URL from NSE response. "
            f"Available keys: {list(latest.keys())}"
        )

    if not pdf_url.startswith("http"):
        pdf_url = NSE_BASE_URL + pdf_url

    log.info("  ✓ Found PDF: %s  (year: %s)", pdf_url, latest.get("year", "N/A"))
    return pdf_url


# ─────────────────────────────────────────────
# STEP 2: Download PDF and Extract Text
# ─────────────────────────────────────────────

def download_pdf(pdf_url: str, save_path: str) -> str:
    """Downloads a PDF from url and writes it to save_path."""
    log.info("[Step 2a] Downloading PDF from %s", pdf_url)

    session = requests.Session()
    # Re-warm cookies so NSE doesn't reject the direct PDF request
    try:
        session.get(NSE_BASE_URL, headers=NSE_HEADERS, timeout=10)
    except requests.RequestException:
        pass

    response = session.get(pdf_url, headers=NSE_HEADERS, stream=True, timeout=60)
    response.raise_for_status()

    with open(save_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    size_mb = os.path.getsize(save_path) / (1024 * 1024)
    log.info("  ✓ Downloaded %.1f MB → %s", size_mb, save_path)
    return save_path


def extract_text_from_pdf(pdf_path: str, max_pages: int = 50) -> str:
    """
    Extracts text from a PDF using pdfplumber.
    Caps at max_pages pages and 50 000 characters (~12k tokens) to stay
    within model context limits.
    """
    log.info("[Step 2b] Extracting text (up to %d pages)…", max_pages)

    text_parts: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        to_read = min(total, max_pages)
        log.info("  Total pages: %d | Reading: %d", total, to_read)

        for i, page in enumerate(pdf.pages[:to_read]):
            page_text = page.extract_text()
            if page_text:
                text_parts.append(f"--- Page {i + 1} ---\n{page_text}")

    full_text = "\n\n".join(text_parts)
    # Hard cap to avoid blowing model context windows
    full_text = full_text[:50_000]
    log.info("  ✓ Extracted %d characters", len(full_text))
    return full_text


# ─────────────────────────────────────────────
# STEP 3: Race N Models in parallel — Score & Rank
# ─────────────────────────────────────────────

def query_model(client: OpenAI, model: str, text: str) -> dict:
    """Sends the analysis prompt to a single model and returns the result dict."""
    log.info("  → Racing: %s", model)
    start = time.time()

    try:
        completion = client.chat.completions.create(
            model=model,
            max_tokens=1500,
            messages=[{"role": "user", "content": ANALYSIS_PROMPT.format(text=text)}],
        )
        elapsed = time.time() - start
        content  = completion.choices[0].message.content or ""
        usage    = completion.usage

        log.info(
            "     ✓ %s — %.1fs | tokens in/out: %d/%d",
            model, elapsed,
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
        )
        return {
            "model":         model,
            "response":      content,
            "latency":       elapsed,
            "input_tokens":  usage.prompt_tokens  if usage else 0,
            "output_tokens": usage.completion_tokens if usage else 0,
        }

    except Exception as exc:
        log.warning("     ✗ %s failed: %s", model, exc)
        return {"model": model, "response": None, "error": str(exc)}


def _score_response_text(query: str, response: str) -> dict:
    """
    Heuristic scoring (0–100) of a model response.
    No external calls — fully deterministic.
    """
    content     = response.lower()
    query_words = [w for w in re.sub(r"[^a-z0-9 ]", " ", query.lower()).split() if len(w) > 3]

    # 1. Length score — reward substantive responses, cap at 25
    S_len = min(len(content) / 40, 25)

    # 2. Structure score — markdown headers, bullets, code blocks
    headers     = len(re.findall(r"^#{1,6} ", response, re.MULTILINE))
    bullets     = len(re.findall(r"^\s*[-*] ", response, re.MULTILINE))
    code_blocks = len(re.findall(r"```", response)) // 2
    S_struct    = min(3 * headers + 1.5 * bullets + 5 * code_blocks, 20)

    # 3. Anti-refusal score — penalise refusals/apologies
    refusal_patterns = ["i can't", "i cannot", "not allowed", "sorry", "i am unable", "as an ai"]
    refusal_count    = sum(1 for p in refusal_patterns if p in content)
    S_anti           = max(25 - 8 * refusal_count, 0)

    # 4. Directness score — penalise filler preambles
    preamble_patterns = ["sure!", "great question", "let's dive", "here's what", "absolutely!"]
    has_preamble      = any(content.startswith(p.lower()) for p in preamble_patterns)
    S_dir             = 8 if has_preamble else 15

    # 5. Relevance score — keyword overlap with prompt
    match_count = sum(1 for w in query_words if w in content)
    S_rel       = 15 * (match_count / len(query_words)) if query_words else 0

    total = min(S_len + S_struct + S_anti + S_dir + S_rel, 100)

    return {
        "total": round(total, 2),
        "breakdown": {
            "S_len":    round(S_len,    2),
            "S_struct": round(S_struct, 2),
            "S_anti":   round(S_anti,   2),
            "S_dir":    round(S_dir,    2),
            "S_rel":    round(S_rel,    2),
        },
    }


def score_response(query: str, response: dict) -> dict:
    """Attaches a heuristic score to a model result dict."""
    if not response.get("response"):
        return {**response, "score": 0, "score_breakdown": {}}

    score_data = _score_response_text(query, response["response"])
    return {**response, "score": score_data["total"], "score_breakdown": score_data["breakdown"]}


def race_models(text: str, n_models: int = 1) -> list[dict]:
    """
    Races the first n_models from RACE_MODELS **in parallel** using a
    ThreadPoolExecutor (I/O-bound network calls benefit from threading).

    Returns results sorted best-score-first.
    """
    n_models      = max(1, min(n_models, len(RACE_MODELS)))
    models_to_use = RACE_MODELS[:n_models]

    log.info("[Step 3] Racing %d model(s) via OpenRouter (parallel)…", len(models_to_use))

    client = get_client()
    # Strip the {text} placeholder from the prompt so the query words reflect
    # only the instruction, not the report body.
    query = ANALYSIS_PROMPT.replace("{text}", "").strip()

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(n_models, 10)) as pool:
        futures = {pool.submit(query_model, client, m, text): m for m in models_to_use}
        for future in as_completed(futures):
            results.append(future.result())

    scored = [score_response(query, r) for r in results]
    scored.sort(key=lambda x: x.get("score", 0), reverse=True)

    log.info("  ┌─ Leaderboard ──────────────────────────────┐")
    for r in scored:
        short = r["model"].split("/")[-1]
        log.info("  │ %-28s %5.1f/100 │", short, r.get("score", 0))
    log.info("  └────────────────────────────────────────────┘")

    return scored


# ─────────────────────────────────────────────
# STEP 4: Select Best Response
# ─────────────────────────────────────────────

def select_best_response(scored_responses: list[dict]) -> dict:
    """Returns the highest-scoring response that actually has content."""
    log.info("[Step 4] Selecting best response…")

    valid = [r for r in scored_responses if r.get("response")]
    if not valid:
        raise ValueError("All models failed — no valid responses to select from.")

    best = valid[0]  # already sorted descending by score
    log.info("  ✓ Winner: %s (score: %.1f/100)", best["model"], best.get("score", 0))
    return best


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────

def analyze_annual_report(symbol: str, n_models: int = 1) -> str:
    """
    Full pipeline:
      1. Scrape annual report PDF link from NSE
      2. Download PDF, extract text
      3. Race n_models in parallel, score & rank
      4. Return the best analysis as a string
    """
    log.info("=" * 60)
    log.info("Annual Report Analysis  |  symbol=%s  models=%d", symbol, n_models)
    log.info("=" * 60)

    pdf_url = scrape_annual_report_link(symbol)

    # Use a named temp file so cleanup is guaranteed via try/finally
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        download_pdf(pdf_url, tmp_path)
        text = extract_text_from_pdf(tmp_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    scored = race_models(text, n_models=n_models)
    best   = select_best_response(scored)

    log.info("=" * 60)
    log.info("PIPELINE COMPLETE — winner: %s", best["model"])
    log.info("=" * 60)

    return best["response"]


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def home() -> dict:
    return {"message": "Algo Trading Backtest API"}


@app.get("/strategies", response_model=StrategyList)
def list_strategies() -> dict:
    strategies = get_available_strategies()
    return {"strategies": strategies}


@app.post("/run_backtest")
def run_strategy(request: BacktestRequest):
    try:
        return run_backtest(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/custom_strategy")
def create_custom_strategy(request: CustomStrategyRequest):
    try:
        register_custom_strategy(request.code, request.name)
        save_custom_strategy(request.code, request.name)
        return {
            "message": f"Custom strategy '{request.name}' created successfully.",
            "strategy_name": request.name,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/run_custom_backtest")
def run_custom_strategy(request: BacktestRequest):
    """Run a backtest with a one-off strategy supplied inline via strategy_params.code."""
    try:
        if request.strategy_params and "code" in request.strategy_params:
            register_custom_strategy(request.strategy_params["code"], request.strategy)
        return run_backtest(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/analyze", response_model=AnalysisResponse)
def analyze_endpoint(request: AnalysisRequest) -> AnalysisResponse:
    symbol = request.stock_name.strip().upper()
    if not symbol:
        raise HTTPException(status_code=400, detail="stock_name must not be empty.")

    try:
        analysis = analyze_annual_report(symbol=symbol, n_models=request.no_of_agents)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except requests.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"NSE fetch failed: {exc}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return AnalysisResponse(
        stock_name=symbol,
        no_of_agents=request.no_of_agents,
        analysis=analysis,
    )


# ─────────────────────────────────────────────
# ENTRYPOINT  (uvicorn main:app --reload)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)