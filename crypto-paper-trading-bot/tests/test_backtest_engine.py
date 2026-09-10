import pandas as pd
from src.backtest_engine import run_backtest
from src.position import Position


class FakeStrategy:
    def add_entry_signals(self, df, **params):
        df = df.copy()
        df["entry_signal"] = [None, "long", None, None, None]
        return df

    def open_position(self, entry_index, entry_bar, direction, **params):
        return Position(
            direction=direction,
            entry_index=entry_index,
            entry_price=entry_bar["open"],
            stop_price=entry_bar["open"] - 10.0,
            target_price=None,
        )

    def check_exit(self, position, bar, **params):
        if bar.name == 3:
            return bar["close"]
        return None


def _make_df():
    return pd.DataFrame({
        "open":  [100.0, 101.0, 102.0, 103.0, 104.0],
        "high":  [100.5, 101.5, 102.5, 103.5, 104.5],
        "low":   [99.5, 100.5, 101.5, 102.5, 103.5],
        "close": [100.2, 101.2, 102.2, 103.2, 104.2],
    })


def test_run_backtest_opens_and_closes_single_trade_no_fees():
    trades = run_backtest(
        _make_df(),
        FakeStrategy(),
        strategy_params={},
        initial_capital=50000.0,
        risk_per_trade=0.005,
        fee_rate=0.0,
        slippage_rate=0.0,
    )

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["direction"] == "long"
    assert trade["entry_index"] == 2
    assert trade["exit_index"] == 3
    assert trade["entry_price"] == 102.0
    assert trade["exit_price"] == 103.2
    # risk_amount = 50000 * 0.005 = 250; stop_distance = 10 -> position_size = 25
    assert trade["position_size"] == 25.0
    # pnl = 25 * (103.2 - 102.0) = 30.0
    assert abs(trade["pnl"] - 30.0) < 1e-9


def test_run_backtest_exits_on_target_price():
    """target_price に到達したらエグジット"""
    class FakeStrategyWithTarget:
        def add_entry_signals(self, df, **params):
            df = df.copy()
            df["entry_signal"] = [None, "long", None, None, None]
            return df

        def open_position(self, entry_index, entry_bar, direction, **params):
            return Position(
                direction=direction,
                entry_index=entry_index,
                entry_price=entry_bar["open"],
                stop_price=entry_bar["open"] - 10.0,
                target_price=entry_bar["open"] + 20.0,
            )

        def check_exit(self, position, bar, **params):
            # ストップのみ（ターゲットは backtest_engine で処理）
            if bar["low"] <= position.stop_price:
                return position.stop_price
            return None

    df = pd.DataFrame({
        "open": [100.0, 101.0, 102.0, 125.0, 126.0],
        "high": [100.5, 101.5, 102.5, 125.5, 126.5],
        "low": [99.5, 100.5, 101.5, 124.5, 125.5],
        "close": [100.2, 101.2, 102.2, 125.2, 126.2],
    })

    trades = run_backtest(
        df,
        FakeStrategyWithTarget(),
        strategy_params={},
        initial_capital=50000.0,
        risk_per_trade=0.005,
        fee_rate=0.0,
        slippage_rate=0.0,
    )

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["entry_index"] == 2  # シグナルはi=1で出現、entry_indexはi+1=2
    assert trade["exit_index"] == 3  # バーi=3でターゲット到達
    assert trade["exit_price"] > 120.0  # ターゲット価格でエグジット


def test_run_backtest_with_dynamic_risk_parameter():
    """use_dynamic_risk パラメータが受け入れられることを確認"""
    trades = run_backtest(
        _make_df(),
        FakeStrategy(),
        strategy_params={},
        initial_capital=50000.0,
        risk_per_trade=0.005,
        fee_rate=0.0,
        slippage_rate=0.0,
        use_dynamic_risk=True,
    )

    assert len(trades) == 1
    trade = trades.iloc[0]
    assert trade["direction"] == "long"


def test_run_backtest_applies_fees_and_slippage():
    trades = run_backtest(
        _make_df(),
        FakeStrategy(),
        strategy_params={},
        initial_capital=50000.0,
        risk_per_trade=0.005,
        fee_rate=0.001,
        slippage_rate=0.0005,
    )

    trade = trades.iloc[0]
    # entry_price = 102 * 1.0005 = 102.051; exit_price = 103.2 * 0.9995 = 103.1484
    assert abs(trade["entry_price"] - 102.051) < 1e-9
    assert abs(trade["exit_price"] - 103.1484) < 1e-9
    gross_pnl = 25.0 * (103.1484 - 102.051)
    fees = (102.051 + 103.1484) * 25.0 * 0.001
    assert abs(trade["pnl"] - (gross_pnl - fees)) < 1e-9
