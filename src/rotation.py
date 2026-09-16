"""Cross-sectional momentum rotation: rank a whole universe of coins, hold the strongest few,
rebalance periodically.

The selection at each rebalance uses ONLY candles up to that moment, and the return is
measured on what happens afterwards, so the test cannot peek into the future.

Usage: python -m src.rotation
"""
import pandas as pd

from src import config
from src.exchange import build_exchange, fetch_ohlcv_history
from src.universe import top_symbols_by_volume


def build_price_panel(exchange, symbols: list[str], candles: int) -> pd.DataFrame:
    """Close prices for every symbol, aligned on a shared timestamp index."""
    series = {}
    for symbol in symbols:
        df = fetch_ohlcv_history(exchange, symbol, candles, timeframe=config.ROTATION_TIMEFRAME)
        if len(df) < candles * 0.9:
            continue
        series[symbol] = df.set_index("timestamp")["close"]

    panel = pd.DataFrame(series)
    return panel.dropna(axis=1, thresh=int(len(panel) * 0.9)).dropna()


def select_basket(panel: pd.DataFrame, as_of: int) -> list[str]:
    """Ranks symbols by trailing return, keeping only those in an uptrend. Uses no data past as_of."""
    history = panel.iloc[: as_of + 1]
    if len(history) <= config.MOMENTUM_LOOKBACK:
        return []

    momentum = history.iloc[-1] / history.iloc[-1 - config.MOMENTUM_LOOKBACK] - 1
    trend_ma = history.tail(config.TREND_FILTER_MA).mean()
    in_uptrend = history.iloc[-1] > trend_ma

    ranked = momentum[in_uptrend & (momentum > 0)].sort_values(ascending=False)
    return list(ranked.head(config.TOP_K).index)


def run_rotation(panel: pd.DataFrame, starting_balance: float = 1000.0) -> dict:
    fee_rate = config.FEE_PCT / 100
    equity = starting_balance
    held: list[str] = []
    curve = []
    rebalances = 0

    start = max(config.MOMENTUM_LOOKBACK, config.TREND_FILTER_MA)
    for i in range(start, len(panel) - 1, config.HOLD_PERIODS):
        basket = select_basket(panel, i)

        turnover = 1.0 if not held and basket else len(set(held) ^ set(basket)) / max(len(set(held) | set(basket)), 1)
        equity *= 1 - turnover * fee_rate * 2
        rebalances += 1

        end = min(i + config.HOLD_PERIODS, len(panel) - 1)
        if basket:
            leg_returns = panel[basket].iloc[end] / panel[basket].iloc[i]
            equity *= leg_returns.mean()

        held = basket
        curve.append((panel.index[end], equity, len(basket)))

    return {
        "final_value": equity,
        "return_pct": (equity / starting_balance - 1) * 100,
        "rebalances": rebalances,
        "curve": curve,
    }


def equal_weight_hold_return_pct(panel: pd.DataFrame) -> float:
    fee_rate = config.FEE_PCT / 100
    legs = panel.iloc[-1] / panel.iloc[0]
    return ((1 - fee_rate) * legs.mean() - 1) * 100


if __name__ == "__main__":
    exchange = build_exchange()

    print(f"Scanning the {config.UNIVERSE_SIZE} most liquid {config.QUOTE_CURRENCY} pairs...")
    symbols = top_symbols_by_volume(exchange, limit=config.UNIVERSE_SIZE)
    print(f"Universe: {len(symbols)} symbols")

    print(f"Downloading {config.ROTATION_CANDLES} candles ({config.ROTATION_TIMEFRAME}) each, may take a while...")
    panel = build_price_panel(exchange, symbols, config.ROTATION_CANDLES)
    print(f"Usable history: {len(panel)} candles x {len(panel.columns)} symbols")
    print(f"Period: {panel.index[0]} -> {panel.index[-1]}")

    result = run_rotation(panel)
    hold_return = equal_weight_hold_return_pct(panel)
    btc_symbol = f"BTC/{config.QUOTE_CURRENCY}"
    btc_return = (panel[btc_symbol].iloc[-1] / panel[btc_symbol].iloc[0] - 1) * 100 if btc_symbol in panel else None

    print(f"\n=== ROTAZIONE MOMENTUM (top {config.TOP_K} su {len(panel.columns)}) ===")
    print(f"Lookback: {config.MOMENTUM_LOOKBACK} candele | Ribilanciamento ogni {config.HOLD_PERIODS} candele")
    print(f"Fee per trade: {config.FEE_PCT}% | Ribilanciamenti: {result['rebalances']}")
    print(f"Capitale finale:      {result['final_value']:.2f}")
    print(f"Return (rotazione):   {result['return_pct']:.2f}%")
    print(f"Return (tutte le monete, equipesate): {hold_return:.2f}%")
    if btc_return is not None:
        print(f"Return (solo BTC):    {btc_return:.2f}%")

    curve = result["curve"]
    per_segment = len(curve) // config.BACKTEST_SEGMENTS
    print(f"\n=== CONSISTENZA PER PERIODO ({config.BACKTEST_SEGMENTS} segmenti) ===")
    for i in range(config.BACKTEST_SEGMENTS):
        lo = i * per_segment
        hi = min((i + 1) * per_segment, len(curve) - 1)
        start_eq = curve[lo][1]
        end_eq = curve[hi][1]
        avg_held = sum(c[2] for c in curve[lo:hi + 1]) / max(hi - lo + 1, 1)
        print(f"{curve[lo][0].date()} -> {curve[hi][0].date()} | rotazione {(end_eq / start_eq - 1) * 100:7.2f}% | monete in media: {avg_held:.1f}")

    print(
        "\nATTENZIONE - bias di sopravvivenza: l'universo e' scelto tra le monete piu' scambiate OGGI.\n"
        "Le monete crollate o delistate in passato non compaiono, quindi questo test e' comunque\n"
        "piu' ottimista della realta'. Tienine conto prima di dare peso al risultato."
    )
