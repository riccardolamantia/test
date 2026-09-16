import os

from dotenv import load_dotenv

load_dotenv()


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


EXCHANGE = os.getenv("EXCHANGE", "binance")
API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")

SYMBOLS = [s.strip() for s in os.getenv("SYMBOLS", "BTC/USDT,ETH/USDT,SOL/USDT,BNB/USDT,XRP/USDT").split(",") if s.strip()]
TIMEFRAME = os.getenv("TIMEFRAME", "1h")

FAST_MA = int(os.getenv("FAST_MA", "20"))
SLOW_MA = int(os.getenv("SLOW_MA", "50"))

# Regime filter: only open new positions while price is above this long moving average
TREND_FILTER_MA = int(os.getenv("TREND_FILTER_MA", "200"))

# Number of equal segments the backtest window is split into for the consistency report
BACKTEST_SEGMENTS = int(os.getenv("BACKTEST_SEGMENTS", "4"))

# Momentum rotation (src/rotation.py): scan the most liquid pairs, hold the strongest few
QUOTE_CURRENCY = os.getenv("QUOTE_CURRENCY", "USDT")
UNIVERSE_SIZE = int(os.getenv("UNIVERSE_SIZE", "40"))
ROTATION_TIMEFRAME = os.getenv("ROTATION_TIMEFRAME", "1d")
ROTATION_CANDLES = int(os.getenv("ROTATION_CANDLES", "700"))
MOMENTUM_LOOKBACK = int(os.getenv("MOMENTUM_LOOKBACK", "30"))
HOLD_PERIODS = int(os.getenv("HOLD_PERIODS", "7"))
TOP_K = int(os.getenv("TOP_K", "5"))

# Stocks and ETFs (src/stocks.py), via Yahoo Finance
STOCK_TICKERS = [t.strip() for t in os.getenv("STOCK_TICKERS", "^GSPC,SPY,QQQ,EUNL.DE").split(",") if t.strip()]
STOCK_YEARS = int(os.getenv("STOCK_YEARS", "20"))

TRADE_AMOUNT_QUOTE = float(os.getenv("TRADE_AMOUNT_QUOTE", "50"))

# Risk management: exit a position early if price moves this much against/in favor of entry
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "5"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "10"))

# Exchange taker fee applied on both buy and sell in the backtest (Binance spot default: 0.1%)
FEE_PCT = float(os.getenv("FEE_PCT", "0.1"))

# Number of historical candles to pull for `python -m src.backtest` (8000 hourly candles ~= 1 year)
BACKTEST_CANDLES = int(os.getenv("BACKTEST_CANDLES", "8000"))

DRY_RUN = _bool(os.getenv("DRY_RUN", "true"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
