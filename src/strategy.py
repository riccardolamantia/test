import pandas as pd

from src import config


def add_signals(df: pd.DataFrame) -> pd.DataFrame:
    """SMA crossover with a regime filter: BUY only when the fast MA crosses above the slow MA
    AND price sits above the long trend MA; SELL on the opposite cross regardless of regime."""
    df = df.copy()
    df["fast_ma"] = df["close"].rolling(config.FAST_MA).mean()
    df["slow_ma"] = df["close"].rolling(config.SLOW_MA).mean()
    df["trend_ma"] = df["close"].rolling(config.TREND_FILTER_MA).mean()

    above = (df["fast_ma"] > df["slow_ma"]).astype(bool)
    prev_above = above.shift(1, fill_value=False).astype(bool)
    uptrend = (df["close"] > df["trend_ma"]).astype(bool)
    crossed_up = above & ~prev_above & uptrend
    crossed_down = ~above & prev_above

    df["signal"] = "HOLD"
    df.loc[crossed_up, "signal"] = "BUY"
    df.loc[crossed_down, "signal"] = "SELL"
    return df


def latest_signal(df: pd.DataFrame) -> str:
    df = add_signals(df)
    return df.iloc[-1]["signal"]


def required_candles() -> int:
    return max(config.SLOW_MA, config.TREND_FILTER_MA) + 10
