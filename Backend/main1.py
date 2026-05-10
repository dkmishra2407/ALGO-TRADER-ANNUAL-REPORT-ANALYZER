from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models.request_models import BacktestRequest, CustomStrategyRequest, StrategyList
from engine.backtest_engine import run_backtest, get_available_strategies, register_custom_strategy
from engine.custom_strategy_engine import save_custom_strategy

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Algo Trading Backtest API"}

@app.post("/run_backtest")
def run_strategy(request: BacktestRequest):
    try:
        result = run_backtest(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/strategies", response_model=StrategyList)
def list_strategies():
    strategies = get_available_strategies()
    return {"strategies": strategies}

@app.post("/custom_strategy")
def create_custom_strategy(request: CustomStrategyRequest):
    try:
        # Register the strategy in memory
        strategy_class = register_custom_strategy(request.code, request.name)

        # Optionally save to file
        save_custom_strategy(request.code, request.name)

        return {
            "message": f"Custom strategy '{request.name}' created successfully",
            "strategy_name": request.name
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/run_custom_backtest")
def run_custom_strategy(request: BacktestRequest):
    """Run backtest with a custom strategy"""
    try:
        # First register the custom strategy if it's provided in strategy_params
        if request.strategy_params and "code" in request.strategy_params:
            register_custom_strategy(request.strategy_params["code"], request.strategy)

        result = run_backtest(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# python -m uvicorn main:app --reload