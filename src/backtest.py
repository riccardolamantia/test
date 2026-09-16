"""Long-only backtest of the regime-filtered SMA crossover strategy over historical OHLCV data,
run independently across every symbol in config.SYMBOLS with an equal split of capital.
The window is also split into equal segments to check whether the edge holds consistently.

Usage: python -m src.backtest
"""
import pandas as pd

from src import config
from src.exchange import build_exchange, fetch_ohlcv_history
from src.risk import check_exit
from src.strategy import add_signals


def run_backtest(df: pd.DataFrame, starting_balance: float = 1000.0) -> dict:
    if "signal" not in df.columns:
        df = add_signals(df)
    fee_rate = config.FEE_PCT / 100

    quote_balance = starting_balance
    base_balance = 0.0
    in_position = False
    entry_price = None
    trades = []

    for _, row in df.iterrows():
        if in_position:
            should_exit, reason = check_exit(entry_price, row["close"])
            if should_exit or row["signal"] == "SELL":
                quote_balance = base_balance * row["close"] * (1 - fee_rate)
                base_balance = 0.0
                in_position = False
                trades.append((reason or "SELL", row["timestamp"], row["close"]))
        elif row["signal"] == "BUY":
            base_balance = (quote_balance * (1 - fee_rate)) / row["close"]
            quote_balance = 0.0
            in_position = True
            entry_price = row["close"]
            trades.append(("BUY", row["timestamp"], row["close"]))

    final_price = df.iloc[-1]["close"]
    final_value = quote_balance + base_balance * final_price

    return {
        "trades": trades,
        "starting_balance": starting_balance,
        "final_value": final_value,
        "return_pct": (final_value / starting_balance - 1) * 100,
    }


def buy_and_hold_return_pct(df: pd.DataFrame) -> float:
    """Benchmark: what a simple 'buy at the start, never sell' approach would have returned."""
    first_price = df.iloc[0]["close"]
    last_price = df.iloc[-1]["close"]
    fee_rate = config.FEE_PCT / 100
    final_value = (1 - fee_rate) * (last_price / first_price)
    return (final_value - 1) * 100


def split_segments(df: pd.DataFrame, n: int) -> list[pd.DataFrame]:
    size = len(df) // n
    return [df.iloc[i * size:(i + 1) * size].reset_index(drop=True) for i in range(n)]


if __name__ == "__main__":
    exchange = build_exchange()
    total_starting_balance = 1000.0
    per_symbol_balance = total_starting_balance / len(config.SYMBOLS)
    n_segments = config.BACKTEST_SEGMENTS

    portfolio_final_value = 0.0
    portfolio_hold_final_value = 0.0
    segment_bot_value = [0.0] * n_segments
    segment_hold_value = [0.0] * n_segments
    segment_periods = [None] * n_segments

    for symbol in config.SYMBOLS:
        data = add_signals(fetch_ohlcv_history(exchange, symbol, total_candles=config.BACKTEST_CANDLES))
        result = run_backtest(data, starting_balance=per_symbol_balance)
        hold_return = buy_and_hold_return_pct(data)

        portfolio_final_value += result["final_value"]
        portfolio_hold_final_value += per_symbol_balance * (1 + hold_return / 100)

        print(f"\n=== {symbol} ({config.TIMEFRAME}) ===")
        print(f"Period: {data.iloc[0]['timestamp']} -> {data.iloc[-1]['timestamp']} ({len(data)} candele)")
        print(f"Trades: {len(result['trades'])}")
        print(f"Return (bot):      {result['return_pct']:.2f}%")
        print(f"Return (buy&hold): {hold_return:.2f}%")

        for i, segment in enumerate(split_segments(data, n_segments)):
            seg_result = run_backtest(segment, starting_balance=per_symbol_balance)
            seg_hold = buy_and_hold_return_pct(segment)
            segment_bot_value[i] += seg_result["final_value"]
            segment_hold_value[i] += per_symbol_balance * (1 + seg_hold / 100)
            segment_periods[i] = (segment.iloc[0]["timestamp"], segment.iloc[-1]["timestamp"])

    portfolio_return = (portfolio_final_value / total_starting_balance - 1) * 100
    portfolio_hold_return = (portfolio_hold_final_value / total_starting_balance - 1) * 100

    print("\n=== PORTFOLIO (capitale diviso equamente tra i simboli) ===")
    print(f"Symbols: {', '.join(config.SYMBOLS)}")
    print(f"Fee per trade: {config.FEE_PCT}% | Trend filter: MA{config.TREND_FILTER_MA}")
    print(f"Starting balance: {total_starting_balance:.2f}")
    print(f"Final value:       {portfolio_final_value:.2f}")
    print(f"Return (bot):      {portfolio_return:.2f}%")
    print(f"Return (buy&hold): {portfolio_hold_return:.2f}%")

    print(f"\n=== CONSISTENZA PER PERIODO ({n_segments} segmenti) ===")
    wins = 0
    for i in range(n_segments):
        bot_pct = (segment_bot_value[i] / total_starting_balance - 1) * 100
        hold_pct = (segment_hold_value[i] / total_starting_balance - 1) * 100
        beat = bot_pct > hold_pct
        wins += beat
        start, end = segment_periods[i]
        print(f"{start.date()} -> {end.date()} | bot {bot_pct:7.2f}% | buy&hold {hold_pct:7.2f}% | {'bot meglio' if beat else 'buy&hold meglio'}")
    print(f"Il bot batte il buy&hold in {wins}/{n_segments} periodi")
