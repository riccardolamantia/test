import ccxt

from src import config


def top_symbols_by_volume(exchange: ccxt.Exchange, limit: int) -> list[str]:
    """Returns the most liquid active spot symbols quoted in config.QUOTE_CURRENCY."""
    markets = exchange.load_markets()
    candidates = [
        symbol
        for symbol, market in markets.items()
        if market.get("spot")
        and market.get("active")
        and market.get("quote") == config.QUOTE_CURRENCY
        and not any(tag in market.get("base", "") for tag in ("UP", "DOWN", "BULL", "BEAR"))
    ]

    tickers = exchange.fetch_tickers(candidates)
    by_volume = sorted(
        (t for t in tickers.values() if t.get("quoteVolume")),
        key=lambda t: t["quoteVolume"],
        reverse=True,
    )
    return [t["symbol"] for t in by_volume[:limit]]
