import pandas as pd


def run_backtest(
    df: pd.DataFrame,
    strategy,
    strategy_params: dict,
    initial_capital: float = 50000.0,
    risk_per_trade: float = 0.005,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.0005,
) -> pd.DataFrame:
    df = strategy.add_entry_signals(df, **strategy_params)
    trades = []
    equity = initial_capital
    position = None

    for i in range(len(df) - 1):
        bar = df.iloc[i]
        next_bar = df.iloc[i + 1]

        if position is not None:
            exit_price = None

            # ターゲット価格チェック
            if position.target_price is not None:
                if position.direction == "long" and bar["high"] >= position.target_price:
                    exit_price = position.target_price
                elif position.direction == "short" and bar["low"] <= position.target_price:
                    exit_price = position.target_price

            # ストップロス/トレイリングストップチェック（ターゲット未達なら）
            if exit_price is None:
                strategy_exit = strategy.check_exit(position, bar, **strategy_params)
                if strategy_exit is not None:
                    exit_price = strategy_exit

            if exit_price is not None:
                trade = _close_trade(position, exit_price, equity, risk_per_trade, fee_rate, slippage_rate, i)
                trades.append(trade)
                equity += trade["pnl"]
                position = None
                continue

        if position is None and bar["entry_signal"] in ("long", "short"):
            position = strategy.open_position(i + 1, next_bar, bar["entry_signal"], **strategy_params)

    return pd.DataFrame(trades)


def _close_trade(position, exit_price, equity, risk_per_trade, fee_rate, slippage_rate, exit_index):
    direction_sign = 1 if position.direction == "long" else -1
    entry_price = position.entry_price * (1 + direction_sign * slippage_rate)
    exit_price = exit_price * (1 - direction_sign * slippage_rate)

    stop_distance = abs(position.entry_price - position.stop_price)
    risk_amount = equity * risk_per_trade
    position_size = risk_amount / stop_distance if stop_distance > 0 else 0.0

    gross_pnl = direction_sign * (exit_price - entry_price) * position_size
    fees = (entry_price + exit_price) * position_size * fee_rate
    pnl = gross_pnl - fees

    return {
        "direction": position.direction,
        "entry_index": position.entry_index,
        "exit_index": exit_index,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "position_size": position_size,
        "pnl": pnl,
    }
