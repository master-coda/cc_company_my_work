import pandas as pd
import pytest
from src.evaluator import evaluate


def test_evaluate_computes_expected_metrics():
    trades = pd.DataFrame({"pnl": [100.0, -50.0, 200.0, -50.0, -100.0]})

    metrics = evaluate(trades)

    assert metrics["total_trades"] == 5
    assert metrics["win_rate"] == pytest.approx(0.4)
    assert metrics["avg_win"] == pytest.approx(150.0)
    assert metrics["avg_loss"] == pytest.approx(-200.0 / 3)
    assert metrics["risk_reward_ratio"] == pytest.approx(2.25)
    assert metrics["profit_factor"] == pytest.approx(1.5)
    assert metrics["max_drawdown"] == pytest.approx(150.0)
    assert metrics["expectancy"] == pytest.approx(20.0)


def test_evaluate_handles_empty_trades():
    trades = pd.DataFrame({"pnl": []})

    metrics = evaluate(trades)

    assert metrics["total_trades"] == 0
    assert metrics["win_rate"] == 0.0
    assert metrics["risk_reward_ratio"] == 0.0
    assert metrics["profit_factor"] == 0.0
