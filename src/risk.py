from src import config


def check_exit(entry_price: float, current_price: float) -> tuple[bool, str | None]:
    """Returns (should_exit, reason) based on stop-loss / take-profit thresholds."""
    change_pct = (current_price / entry_price - 1) * 100

    if change_pct <= -config.STOP_LOSS_PCT:
        return True, "STOP_LOSS"
    if change_pct >= config.TAKE_PROFIT_PCT:
        return True, "TAKE_PROFIT"
    return False, None
