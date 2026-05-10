from pydantic import BaseModel
from typing import Dict, Any, Optional

class BacktestRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    strategy: str
    cash: float = 100000
    strategy_params: Optional[Dict[str, Any]] = None
    plot: bool = False

class CustomStrategyRequest(BaseModel):
    name: str
    code: str  # Python code for the strategy class

class StrategyList(BaseModel):
    strategies: list[str]