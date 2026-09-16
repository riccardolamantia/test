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


def fetch_ohlcv(exchange: ccxt.Exchange, limit: int = 200) -> pd.DataFrame:
    raw = exchange.fetch_ohlcv(config.SYMBOL, timeframe=config.TIMEFRAME, limit=limit)
    df = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    return df


def place_order(exchange: ccxt.Exchange, side: str, price: float):
    """Places a market order sized in quote currency. No-ops when DRY_RUN is on."""
    amount = config.TRADE_AMOUNT_QUOTE / price

    if config.DRY_RUN:
        print(f"[DRY_RUN] {side.upper()} {amount:.6f} {config.SYMBOL} @ ~{price}")
        return {"dry_run": True, "side": side, "amount": amount, "price": price}

    return exchange.create_order(config.SYMBOL, "market", side, amount)
