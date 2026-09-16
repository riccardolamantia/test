import ccxt
import pandas as pd

from src import config


def build_exchange() -> ccxt.Exchange:
    exchange_class = getattr(ccxt, config.EXCHANGE)
    return exchange_class(
        {
            "apiKey": config.API_KEY,
            "secret": config.API_SECRET,
            "enableRateLimit": True,
        }
    )


def fetch_ohlcv(exchange: ccxt.Exchange, symbol: str, limit: int = 200) -> pd.DataFrame:
    raw = exchange.fetch_ohlcv(symbol, timeframe=config.TIMEFRAME, limit=limit)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def fetch_ohlcv_history(
    exchange: ccxt.Exchange, symbol: str, total_candles: int, timeframe: str | None = None
) -> pd.DataFrame:
    """Paginates fetch_ohlcv backwards in time to gather more candles than a single call allows."""
    timeframe = timeframe or config.TIMEFRAME
    timeframe_ms = exchange.parse_timeframe(timeframe) * 1000
    since = exchange.milliseconds() - total_candles * timeframe_ms

    all_rows = []
    while len(all_rows) < total_candles:
        batch = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1000)
        if not batch:
            break
        all_rows.extend(batch)
        since = batch[-1][0] + timeframe_ms

    df = pd.DataFrame(all_rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates(subset="timestamp").tail(total_candles).reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def place_order(exchange: ccxt.Exchange, symbol: str, side: str, price: float):
    """Places a market order sized in quote currency. No-ops when DRY_RUN is on."""
    amount = config.TRADE_AMOUNT_QUOTE / price

    if config.DRY_RUN:
        print(f"[DRY_RUN] {side.upper()} {amount:.6f} {symbol} @ ~{price}")
        return {"dry_run": True, "symbol": symbol, "side": side, "amount": amount, "price": price}

    return exchange.create_order(symbol, "market", side, amount)
