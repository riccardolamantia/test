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
