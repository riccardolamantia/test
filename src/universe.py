import ccxt

from src import config

# Pegged or derivative assets: they either barely move or just track another coin in the
# universe, so they would burn slots without ever being a meaningful momentum candidate.
EXCLUDED_BASES = {
    "USDC", "FDUSD", "TUSD", "USDP", "USDE", "USD1", "USDS", "XUSD", "BFUSD", "RLUSD",
    "FRAX", "EUR", "EURI", "DAI", "PAXG", "XAUT",
    "WBTC", "WBETH", "BNSOL", "BETH",
}


def top_symbols_by_volume(exchange: ccxt.Exchange, limit: int) -> list[str]:
    """Returns the most liquid active spot symbols quoted in config.QUOTE_CURRENCY."""
    markets = exchange.load_markets()
    candidates = {
        symbol
        for symbol, market in markets.items()
        if market.get("spot")
        and market.get("active")
        and market.get("quote") == config.QUOTE_CURRENCY
        and market.get("base") not in EXCLUDED_BASES
        and not any(tag in market.get("base", "") for tag in ("UP", "DOWN", "BULL", "BEAR"))
    }

    # Requesting hundreds of symbols by name overflows the request URI, so pull every
    # ticker in one call and filter locally.
    tickers = exchange.fetch_tickers()
    by_volume = sorted(
        (t for s, t in tickers.items() if s in candidates and t.get("quoteVolume")),
        key=lambda t: t["quoteVolume"],
        reverse=True,
    )
    return [t["symbol"] for t in by_volume[:limit]]
