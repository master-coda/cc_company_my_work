import pandas as pd


def evaluate(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "risk_reward_ratio": 0.0,
            "profit_factor": 0.0,
            "max_drawdown": 0.0,
            "expectancy": 0.0,
        }

    wins = trades[trades["pnl"] > 0]["pnl"]
    losses = trades[trades["pnl"] < 0]["pnl"]

    total_trades = len(trades)
    win_rate = len(wins) / total_trades
    avg_win = wins.mean() if len(wins) > 0 else 0.0
    avg_loss = losses.mean() if len(losses) > 0 else 0.0
    if avg_loss != 0:
        risk_reward_ratio = avg_win / abs(avg_loss)
    elif len(wins) > 0:
        risk_reward_ratio = float("inf")
    else:
        risk_reward_ratio = 0.0

    gross_profit = wins.sum()
    gross_loss = abs(losses.sum())
    if gross_loss != 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    equity_curve = pd.concat([pd.Series([0.0]), trades["pnl"].cumsum()], ignore_index=True)
    running_max = equity_curve.cummax()
    drawdown = equity_curve - running_max
    max_drawdown = abs(drawdown.min())

    expectancy = trades["pnl"].mean()

    return {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "risk_reward_ratio": risk_reward_ratio,
        "profit_factor": profit_factor,
        "max_drawdown": max_drawdown,
        "expectancy": expectancy,
    }
