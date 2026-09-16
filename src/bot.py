"""Live trading loop across every symbol in config.SYMBOLS.
Defaults to DRY_RUN (no real orders) until explicitly disabled in .env.

Usage: python -m src.bot
"""
import time

from src import config
from src.exchange import build_exchange, fetch_ohlcv, place_order
from src.risk import check_exit
from src.strategy import latest_signal, required_candles


def run():
    exchange = build_exchange()
    positions = {symbol: None for symbol in config.SYMBOLS}  # symbol -> entry_price or None

    print(f"Starting bot on {', '.join(config.SYMBOLS)} ({config.TIMEFRAME}) | DRY_RUN={config.DRY_RUN}")

    while True:
        for symbol in config.SYMBOLS:
            df = fetch_ohlcv(exchange, symbol, limit=required_candles())
            signal = latest_signal(df)
            price = df.iloc[-1]["close"]
            timestamp = df.iloc[-1]["timestamp"]
            entry_price = positions[symbol]

            if entry_price is not None:
                should_exit, reason = check_exit(entry_price, price)
                if should_exit:
                    place_order(exchange, symbol, "sell", price)
                    positions[symbol] = None
                    print(f"[{timestamp}] {symbol} exit position: {reason} @ {price}")
                elif signal == "SELL":
                    place_order(exchange, symbol, "sell", price)
                    positions[symbol] = None
                    print(f"[{timestamp}] {symbol} exit position: SIGNAL @ {price}")
                else:
                    print(f"[{timestamp}] {symbol} holding (entry={entry_price}) price={price}")
            elif signal == "BUY":
                place_order(exchange, symbol, "buy", price)
                positions[symbol] = price
                print(f"[{timestamp}] {symbol} entered position @ {price}")
            else:
                print(f"[{timestamp}] {symbol} signal={signal} price={price} no action")

        time.sleep(config.POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
