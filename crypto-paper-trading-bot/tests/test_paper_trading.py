import json
import tempfile
from src.paper_trading import PaperTradingPortfolio


def test_portfolio_initializes_with_initial_capital():
    """初期資金で初期化"""
    portfolio = PaperTradingPortfolio(initial_capital=30000.0)
    assert portfolio.get_equity() == 30000.0
    assert len(portfolio.trades) == 0


def test_record_trade_updates_equity():
    """トレード記録で資金更新"""
    portfolio = PaperTradingPortfolio(initial_capital=30000.0)
    # entry: BTC 1 @ $100
    portfolio.record_trade(
        timestamp="2026-09-10T23:00:00Z",
        symbol="BTC/USDT",
        side="buy",
        entry_price=100.0,
        exit_price=120.0,
        quantity=1.0,
    )

    pnl = portfolio.get_pnl()
    assert pnl == 20.0  # (120 - 100) * 1
    assert portfolio.get_equity() == 30020.0


def test_portfolio_saves_to_json():
    """ポートフォリオをJSON保存"""
    portfolio = PaperTradingPortfolio(initial_capital=30000.0)
    portfolio.record_trade(
        timestamp="2026-09-10T23:00:00Z",
        symbol="BTC/USDT",
        side="buy",
        entry_price=100.0,
        exit_price=120.0,
        quantity=1.0,
    )

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    portfolio.save_to_json(filepath)

    # ファイルが作成されたことを確認
    with open(filepath, 'r') as f:
        data = json.load(f)

    assert data["initial_capital"] == 30000.0
    assert len(data["trades"]) == 1
    assert data["trades"][0]["pnl"] == 20.0


def test_portfolio_loads_from_json():
    """JSONからポートフォリオを復元"""
    # オリジナルを作成・保存
    original = PaperTradingPortfolio(initial_capital=30000.0)
    original.record_trade(
        timestamp="2026-09-10T23:00:00Z",
        symbol="BTC/USDT",
        side="buy",
        entry_price=100.0,
        exit_price=120.0,
        quantity=1.0,
    )

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        filepath = f.name

    original.save_to_json(filepath)

    # 復元
    restored = PaperTradingPortfolio.load_from_json(filepath)

    assert restored.get_equity() == original.get_equity()
    assert restored.get_pnl() == original.get_pnl()
    assert len(restored.trades) == 1
