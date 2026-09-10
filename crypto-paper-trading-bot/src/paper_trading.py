import json
from typing import List
from datetime import datetime


class PaperTradingPortfolio:
    def __init__(self, initial_capital: float = 30000.0):
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.trades: List[dict] = []

    def record_trade(
        self,
        timestamp: str,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        quantity: float,
    ) -> None:
        """トレードを記録"""
        pnl = (exit_price - entry_price) * quantity
        self.trades.append({
            "timestamp": timestamp,
            "symbol": symbol,
            "side": side,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "pnl": pnl,
        })
        self.equity += pnl

    def get_pnl(self) -> float:
        """累積PnLを取得"""
        return sum(trade["pnl"] for trade in self.trades)

    def get_equity(self) -> float:
        """現在の資金を取得"""
        return self.equity

    def get_total_trades(self) -> int:
        """トレード数を取得"""
        return len(self.trades)

    def get_win_rate(self) -> float:
        """勝率を取得（勝利トレード数 / 総トレード数）"""
        if not self.trades:
            return 0.0
        wins = sum(1 for trade in self.trades if trade["pnl"] > 0)
        return wins / len(self.trades)

    def save_to_json(self, filepath: str) -> None:
        """ポートフォリオをJSON保存"""
        data = {
            "initial_capital": self.initial_capital,
            "current_equity": self.equity,
            "total_pnl": self.get_pnl(),
            "total_trades": self.get_total_trades(),
            "win_rate": self.get_win_rate(),
            "timestamp": datetime.utcnow().isoformat(),
            "trades": self.trades,
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_from_json(filepath: str) -> "PaperTradingPortfolio":
        """JSONからポートフォリオを復元"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        portfolio = PaperTradingPortfolio(initial_capital=data["initial_capital"])
        portfolio.equity = data["current_equity"]
        portfolio.trades = data["trades"]
        return portfolio
