import pandas as pd
from src.parameter_search import grid_search
from src.position import Position


class FakeStrategyForGridSearch:
    def add_entry_signals(self, df, **params):
        df = df.copy()
        df["entry_signal"] = [None, "long", None, None]
        return df

    def open_position(self, entry_index, entry_bar, direction, **params):
        return Position(
            direction=direction,
            entry_index=entry_index,
            entry_price=entry_bar["open"],
            stop_price=entry_bar["open"] - 10.0,
            target_price=None,
        )

    def check_exit(self, position, bar, threshold=1, **params):
        # Payoff peaks at threshold == 2 by construction, so the search
        # must actually compare all three, not just pick an endpoint.
        payoff = {1: 5.0, 2: 50.0, 3: 20.0}
        if bar.name == 2:
            return position.entry_price + payoff[threshold]
        return None


def test_grid_search_picks_best_scoring_params():
    df = pd.DataFrame({
        "open":  [100.0, 101.0, 102.0, 103.0],
        "high":  [100.5, 101.5, 102.5, 103.5],
        "low":   [99.5, 100.5, 101.5, 102.5],
        "close": [100.2, 101.2, 102.2, 103.2],
    })

    best = grid_search(df, FakeStrategyForGridSearch(), param_grid={"threshold": [1, 2, 3]})

    assert best == {"threshold": 2}


class FakeStrategyForTradeCountFloor:
    """One mode produces a single, huge-expectancy trade; the other produces
    many trades with modest but positive expectancy each. Without a min_trades
    floor, grid_search would chase the lucky single trade."""

    def add_entry_signals(self, df, mode):
        df = df.copy()
        if mode == "lucky":
            signals = [None] * len(df)
            signals[0] = "long"
        else:
            signals = ["long"] * len(df)
        df["entry_signal"] = signals
        return df

    def open_position(self, entry_index, entry_bar, direction, mode=None, **params):
        return Position(
            direction=direction,
            entry_index=entry_index,
            entry_price=entry_bar["open"],
            stop_price=entry_bar["open"] - 10.0,
            target_price=None,
        )

    def check_exit(self, position, bar, mode=None, **params):
        if mode == "lucky":
            return position.entry_price + 1000.0
        return position.entry_price + 3.0


def test_grid_search_prefers_high_trade_count_over_lucky_single_trade():
    df = pd.DataFrame({"open": [100.0] * 80})

    best = grid_search(
        df,
        FakeStrategyForTradeCountFloor(),
        param_grid={"mode": ["lucky", "consistent"]},
    )

    assert best == {"mode": "consistent"}
