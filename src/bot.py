"""Live trading loop. Defaults to DRY_RUN (no real orders) until explicitly disabled in .env.

Usage: python -m src.bot
"""
import time

from src import config
from src.exchange import build_exchange, fetch_ohlcv, place_order
from src.risk import check_exit
from src.strategy import latest_signal


def run():
    exchange = build_exchange()
    position_open = False
    entry_price = None

    print(f"Starting bot on {config.SYMBOL} ({config.TIMEFRAME}) | DRY_RUN={config.DRY_RUN}")

    while True:
        df = fetch_ohlcv(exchange, limit=config.SLOW_MA + 10)
        signal = latest_signal(df)
        price = df.iloc[-1]["close"]
        timestamp = df.iloc[-1]["timestamp"]

        if position_open:
            should_exit, reason = check_exit(entry_price, price)
            if should_exit:
                place_order(exchange, "sell", price)
                position_open = False
                print(f"[{timestamp}] exit position: {reason} @ {price}")
            elif signal == "SELL":
                place_order(exchange, "sell", price)
                position_open = False
                print(f"[{timestamp}] exit position: SIGNAL @ {price}")
            else:
                print(f"[{timestamp}] holding position (entry={entry_price}) price={price}")
        elif signal == "BUY":
            place_order(exchange, "buy", price)
            position_open = True
            entry_price = price
            print(f"[{timestamp}] entered position @ {price}")
        else:
            print(f"[{timestamp}] signal={signal} price={price} no action")

        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
