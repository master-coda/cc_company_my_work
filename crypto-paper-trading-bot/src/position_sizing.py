def calculate_dynamic_risk(recent_trades: list[dict], base_risk: float = 0.005) -> float:
    """
    直近取引の勝敗に基づいて動的にリスク率を調整する。

    連敗中（直近3取引で1勝以下）: 0.25% に低下
    好調時（直近5取引で4勝以上）: 1.0% に上昇
    通常: base_risk をそのまま返す

    Args:
        recent_trades: 直近取引のリスト（各要素は {"pnl": float, ...}）
        base_risk: ベースリスク率（デフォルト 0.005 = 0.5%）

    Returns:
        調整後の risk_per_trade（0.0025～0.01 の範囲）
    """
    if not recent_trades:
        return base_risk

    # 直近3取引での勝敗カウント（連敗判定）
    recent_3 = recent_trades[-3:] if len(recent_trades) >= 3 else recent_trades
    wins_3 = sum(1 for trade in recent_3 if trade["pnl"] > 0)

    if len(recent_3) >= 3 and wins_3 <= 1:
        # 連敗中
        return 0.0025

    # 直近5取引での勝敗カウント（好調判定）
    recent_5 = recent_trades[-5:] if len(recent_trades) >= 5 else recent_trades
    wins_5 = sum(1 for trade in recent_5 if trade["pnl"] > 0)

    if len(recent_5) >= 5 and wins_5 >= 4:
        # 好調
        return 0.01

    # 通常
    return base_risk
