import pytest
from src.position_sizing import calculate_dynamic_risk


def test_calculate_dynamic_risk_normal_conditions():
    """通常時（混合勝敗）は base_risk をそのまま返す"""
    recent_trades = [
        {"pnl": 100.0},   # 勝ち
        {"pnl": -50.0},   # 負け
        {"pnl": 200.0},   # 勝ち
    ]

    result = calculate_dynamic_risk(recent_trades, base_risk=0.005)
    assert result == 0.005


def test_calculate_dynamic_risk_losing_streak():
    """連敗中（直近3取引で1勝以下）は 0.25% に低下"""
    recent_trades = [
        {"pnl": -50.0},
        {"pnl": -100.0},
        {"pnl": 50.0},   # 1勝のみ
    ]

    result = calculate_dynamic_risk(recent_trades, base_risk=0.005)
    assert result == 0.0025  # 0.5% → 0.25%


def test_calculate_dynamic_risk_winning_streak():
    """好調時（直近5取引で4勝以上）は 1.0% に上昇"""
    recent_trades = [
        {"pnl": 100.0},
        {"pnl": 150.0},
        {"pnl": 200.0},
        {"pnl": 80.0},
        {"pnl": -30.0},   # 4勝1負
    ]

    result = calculate_dynamic_risk(recent_trades, base_risk=0.005)
    assert result == 0.01  # 0.5% → 1.0%


def test_calculate_dynamic_risk_empty_trades():
    """取引履歴がない場合は base_risk を返す"""
    result = calculate_dynamic_risk([], base_risk=0.005)
    assert result == 0.005


def test_calculate_dynamic_risk_bounds():
    """調整後のリスクは [0.0025, 0.01] 範囲内"""
    # 最小値テスト
    losing = [{"pnl": -100.0} for _ in range(5)]
    assert calculate_dynamic_risk(losing, base_risk=0.001) == 0.0025

    # 最大値テスト
    winning = [{"pnl": 100.0} for _ in range(5)]
    assert calculate_dynamic_risk(winning, base_risk=0.01) == 0.01
