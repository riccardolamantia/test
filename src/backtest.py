"""Simple long-only backtest of the SMA crossover strategy over historical OHLCV data.

Usage: python -m src.backtest
"""
import pandas as pd

from src import config
from src.exchange import build_exchange, fetch_ohlcv
from src.strategy import add_signals


def run_backtest(df: pd.DataFrame, starting_balance: float = 1000.0) -> dict:
    df = add_signals(df)

    quote_balance = starting_balance
    base_balance = 0.0
    in_position = False
    trades = []

    for _, row in df.iterrows():
        if row["signal"] == "BUY" and not in_position:
            base_balance = quote_balance / row["close"]
            quote_balance = 0.0
            in_position = True
            trades.append(("BUY", row["timestamp"], row["close"]))
        elif row["signal"] == "SELL" and in_position:
            quote_balance = base_balance * row["close"]
            base_balance = 0.0
            in_position = False
            trades.append(("SELL", row["timestamp"], row["close"]))

    final_price = df.iloc[-1]["close"]
    final_value = quote_balance + base_balance * final_price

    return {
        "trades": trades,
        "starting_balance": starting_balance,
        "final_value": final_value,
        "return_pct": (final_value / starting_balance - 1) * 100,
    }


if __name__ == "__main__":
    exchange = build_exchange()
    data = fetch_ohlcv(exchange, limit=500)
    result = run_backtest(data)

    print(f"Symbol: {config.SYMBOL} | Timeframe: {config.TIMEFRAME}")
    print(f"Trades executed: {len(result['trades'])}")
    for side, ts, price in result["trades"]:
        print(f"  {side:4s} {ts} @ {price}")
    print(f"Starting balance: {result['starting_balance']:.2f}")
    print(f"Final value:      {result['final_value']:.2f}")
    print(f"Return:           {result['return_pct']:.2f}%")
