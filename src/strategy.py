import pandas as pd

from src import config


def add_signals(df: pd.DataFrame) -> pd.DataFrame:
    """SMA crossover: BUY when the fast MA crosses above the slow MA, SELL on the opposite cross."""
    df = df.copy()
    df["fast_ma"] = df["close"].rolling(config.FAST_MA).mean()
    df["slow_ma"] = df["close"].rolling(config.SLOW_MA).mean()

    above = df["fast_ma"] > df["slow_ma"]
    crossed_up = above & ~above.shift(1).fillna(False)
    crossed_down = ~above & above.shift(1).fillna(False)

    df["signal"] = "HOLD"
    df.loc[crossed_up, "signal"] = "BUY"
    df.loc[crossed_down, "signal"] = "SELL"
    return df


def latest_signal(df: pd.DataFrame) -> str:
    df = add_signals(df)
    return df.iloc[-1]["signal"]
