"""Live trading loop. Defaults to DRY_RUN (no real orders) until explicitly disabled in .env.

Usage: python -m src.bot
"""
import time

from src import config
from src.exchange import build_exchange, fetch_ohlcv, place_order
from src.strategy import latest_signal


def run():
    exchange = build_exchange()
    position_open = False

    print(f"Starting bot on {config.SYMBOL} ({config.TIMEFRAME}) | DRY_RUN={config.DRY_RUN}")

    while True:
        df = fetch_ohlcv(exchange, limit=config.SLOW_MA + 10)
        signal = latest_signal(df)
        price = df.iloc[-1]["close"]

        if signal == "BUY" and not position_open:
            place_order(exchange, "buy", price)
            position_open = True
        elif signal == "SELL" and position_open:
            place_order(exchange, "sell", price)
            position_open = False
        else:
            print(f"[{df.iloc[-1]['timestamp']}] signal={signal} price={price} no action")

        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
