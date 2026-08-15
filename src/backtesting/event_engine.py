from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.backtesting.costs import apply_slippage, eight_hour_periods, funding_cost, taker_fee
from src.backtesting.metrics import compute_metrics
from src.execution.engine import build_execution_plan
from src.risk.circuit_breaker import CircuitBreaker, CircuitBreakerState
from src.risk.position_sizing import calculate_trade_levels
from src.strategy.regime_filter import RegimeThresholds, classify_regime
from src.strategy.signals import evaluate_signal


@dataclass
class OpenPosition:
    side: str
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    initial_risk: float
    entry_ts: pd.Timestamp
    regime: str
    breakeven_trigger: float
    trailing_trigger: float
    trailing_active: bool = False


class EventDrivenBacktester:
    def __init__(self, strategy_config: dict, risk_config: dict) -> None:
        self.strategy_config = strategy_config
        self.risk_config = risk_config

    def run(self, data: dict[str, pd.DataFrame], initial_equity: float | None = None) -> dict:
        equity = float(initial_equity or self.risk_config["equity"])
        equity_points: list[tuple[pd.Timestamp, float]] = []
        trades: list[dict] = []
        open_position: OpenPosition | None = None

        thresholds = RegimeThresholds(**self.strategy_config["regime"])
        breaker = CircuitBreaker(
            self.risk_config["daily_loss_limit"],
            self.risk_config["weekly_loss_limit"],
            self.risk_config["consecutive_loss_limit"],
            self.risk_config["pause_hours_after_loss_streak"],
        )
        state = CircuitBreakerState(start_equity_day=equity, start_equity_week=equity)

        df_15m = data["15m"]
        df_5m = data["5m"]
        df_1h = data["1h"]

        for ts, candle in df_15m.iloc[200:].iterrows():
            slice_15m = df_15m.loc[:ts].tail(250)
            slice_5m = df_5m.loc[:ts].tail(250)
            regime_row = df_1h.loc[:ts].tail(1)
            if regime_row.empty:
                continue
            regime = classify_regime(regime_row.iloc[-1], thresholds)

            if open_position is not None:
                exit_trade = self._manage_open_position(open_position, candle, ts, regime)
                if exit_trade is not None:
                    net_pnl = exit_trade["gross_pnl"] - exit_trade["fees"] - exit_trade["funding_cost"]
                    equity += net_pnl
                    exit_trade["net_pnl"] = net_pnl
                    trades.append(exit_trade)
                    breaker.register_trade(ts, net_pnl, equity, state)
                    open_position = None

            if open_position is None and breaker.can_trade(ts, equity, state):
                decision = evaluate_signal(regime, slice_15m, slice_5m, self.strategy_config["confluence"])
                if decision is None:
                    equity_points.append((ts, equity))
                    continue

                spread = (candle["high"] - candle["low"]) / candle["close"] if candle["close"] else 0.0
                if spread > self.strategy_config["execution"]["spread_limit_pct"]:
                    equity_points.append((ts, equity))
                    continue

                nearest_swing = (
                    slice_15m["swing_low"].dropna().iloc[-1]
                    if decision.side == "buy" and not slice_15m["swing_low"].dropna().empty
                    else slice_15m["swing_high"].dropna().iloc[-1]
                    if decision.side == "sell" and not slice_15m["swing_high"].dropna().empty
                    else None
                )
                levels = calculate_trade_levels(
                    side=decision.side,
                    entry=float(candle["close"]),
                    atr_value=float(candle["atr_14"]),
                    nearest_swing=float(nearest_swing) if nearest_swing is not None else None,
                    atr_stop_multiplier=self.risk_config["atr_stop_multiplier"],
                    structure_buffer_atr=self.risk_config["structure_buffer_atr"],
                    reward_risk_ratio=self.risk_config["reward_risk_ratio"],
                )
                plan = build_execution_plan(
                    side=decision.side,
                    score=decision.score,
                    entry_price=float(candle["close"]),
                    equity=equity,
                    trade_levels=levels,
                    risk_config=self.risk_config,
                )
                if plan is not None:
                    entry_fill = apply_slippage(plan.entry_price, plan.side, is_entry=True)
                    open_position = OpenPosition(
                        side=plan.side,
                        quantity=plan.quantity,
                        entry_price=entry_fill,
                        stop_loss=plan.stop_loss,
                        take_profit=plan.take_profit,
                        initial_risk=levels.risk_per_unit,
                        entry_ts=ts,
                        regime=decision.regime,
                        breakeven_trigger=levels.breakeven_trigger,
                        trailing_trigger=levels.trailing_trigger,
                    )

            equity_points.append((ts, equity))

        equity_curve = pd.Series({ts: value for ts, value in equity_points}).sort_index()
        metrics = compute_metrics(trades, equity_curve)
        return {"trades": trades, "equity_curve": equity_curve, "metrics": metrics}

    def _manage_open_position(self, position: OpenPosition, candle: pd.Series, ts: pd.Timestamp, regime: str) -> dict | None:
        if position.side == "buy":
            if candle["high"] >= position.breakeven_trigger:
                position.stop_loss = max(position.stop_loss, position.entry_price)
            if candle["high"] >= position.trailing_trigger:
                atr_mult = self.risk_config["vol_spike_trailing_atr_multiplier"] if regime == "VOLATILITY_SPIKE" else self.risk_config["trailing_atr_multiplier"]
                position.stop_loss = max(position.stop_loss, candle["close"] - candle["atr_14"] * atr_mult)
                position.trailing_active = True
            exit_price = None
            reason = None
            if candle["low"] <= position.stop_loss:
                exit_price = position.stop_loss
                reason = "stop_loss"
            elif candle["high"] >= position.take_profit:
                exit_price = position.take_profit
                reason = "take_profit"
            if exit_price is None:
                return None
            exit_fill = apply_slippage(exit_price, position.side, is_entry=False)
            gross_pnl = (exit_fill - position.entry_price) * position.quantity
        else:
            if candle["low"] <= position.breakeven_trigger:
                position.stop_loss = min(position.stop_loss, position.entry_price)
            if candle["low"] <= position.trailing_trigger:
                atr_mult = self.risk_config["vol_spike_trailing_atr_multiplier"] if regime == "VOLATILITY_SPIKE" else self.risk_config["trailing_atr_multiplier"]
                position.stop_loss = min(position.stop_loss, candle["close"] + candle["atr_14"] * atr_mult)
                position.trailing_active = True
            exit_price = None
            reason = None
            if candle["high"] >= position.stop_loss:
                exit_price = position.stop_loss
                reason = "stop_loss"
            elif candle["low"] <= position.take_profit:
                exit_price = position.take_profit
                reason = "take_profit"
            if exit_price is None:
                return None
            exit_fill = apply_slippage(exit_price, position.side, is_entry=False)
            gross_pnl = (position.entry_price - exit_fill) * position.quantity

        notional_entry = position.entry_price * position.quantity
        notional_exit = exit_fill * position.quantity
        fees = taker_fee(notional_entry) + taker_fee(notional_exit)
        funding = funding_cost(notional_entry, eight_hour_periods(position.entry_ts, ts), self.risk_config["funding_rate_per_8h"])
        return {
            "entry_ts": position.entry_ts,
            "exit_ts": ts,
            "side": position.side,
            "entry_price": position.entry_price,
            "exit_price": exit_fill,
            "quantity": position.quantity,
            "gross_pnl": gross_pnl,
            "fees": fees,
            "funding_cost": funding,
            "regime": position.regime,
            "exit_reason": reason,
        }
