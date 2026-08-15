from __future__ import annotations

from dataclasses import dataclass

from src.risk.position_sizing import TradeLevels, position_size_from_risk


@dataclass(frozen=True)
class ExecutionPlan:
    side: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    score: float


def build_execution_plan(
    side: str,
    score: float,
    entry_price: float,
    equity: float,
    trade_levels: TradeLevels,
    risk_config: dict,
) -> ExecutionPlan | None:
    quantity = position_size_from_risk(
        equity=equity,
        risk_per_trade=risk_config["risk_per_trade"],
        entry=entry_price,
        stop_loss=trade_levels.stop_loss,
        max_leverage=risk_config["max_leverage"],
    )
    if quantity <= 0:
        return None
    return ExecutionPlan(
        side=side,
        quantity=quantity,
        entry_price=entry_price,
        stop_loss=trade_levels.stop_loss,
        take_profit=trade_levels.take_profit,
        score=score,
    )
