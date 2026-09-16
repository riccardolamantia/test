import os

from dotenv import load_dotenv

load_dotenv()


def _bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


EXCHANGE = os.getenv("EXCHANGE", "binance")
API_KEY = os.getenv("API_KEY", "")
API_SECRET = os.getenv("API_SECRET", "")

SYMBOL = os.getenv("SYMBOL", "BTC/USDT")
TIMEFRAME = os.getenv("TIMEFRAME", "1h")

FAST_MA = int(os.getenv("FAST_MA", "20"))
SLOW_MA = int(os.getenv("SLOW_MA", "50"))

TRADE_AMOUNT_QUOTE = float(os.getenv("TRADE_AMOUNT_QUOTE", "50"))

# Risk management: exit a position early if price moves this much against/in favor of entry
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "5"))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "10"))

DRY_RUN = _bool(os.getenv("DRY_RUN", "true"))
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
