"""Runs the same crossover strategy on stock indices and ETFs, over decades of history
instead of the couple of years of usable crypto data.

Prices are dividend- and split-adjusted, so buy-and-hold is compared on total return.

Usage: python -m src.stocks
"""
import pandas as pd
import yfinance as yf

from src import config
from src.backtest import buy_and_hold_return_pct, run_backtest, split_segments
from src.strategy import add_signals


def fetch_yahoo(ticker: str, years: int) -> pd.DataFrame:
    raw = yf.download(ticker, period=f"{years}y", interval="1d", auto_adjust=True, progress=False)
    if raw.empty:
        return pd.DataFrame()

    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    df = raw.reset_index()
    df.columns = [str(c).lower() for c in df.columns]
    df = df.rename(columns={"date": "timestamp", "datetime": "timestamp", "index": "timestamp"})
    return df[["timestamp", "open", "high", "low", "close", "volume"]].dropna()


if __name__ == "__main__":
    print(f"Strategia: SMA {config.FAST_MA}/{config.SLOW_MA} + filtro MA{config.TREND_FILTER_MA}")
    print(f"Commissione simulata: {config.FEE_PCT}% per operazione\n")

    for ticker in config.STOCK_TICKERS:
        data = fetch_yahoo(ticker, config.STOCK_YEARS)
        if len(data) < config.TREND_FILTER_MA * 2:
            print(f"=== {ticker} === storico insufficiente, saltato\n")
            continue

        data = add_signals(data)
        result = run_backtest(data)
        hold_return = buy_and_hold_return_pct(data)
        years = (data.iloc[-1]["timestamp"] - data.iloc[0]["timestamp"]).days / 365.25

        print(f"=== {ticker} ===")
        print(f"Periodo: {data.iloc[0]['timestamp'].date()} -> {data.iloc[-1]['timestamp'].date()} ({years:.1f} anni)")
        print(f"Operazioni: {len(result['trades'])}")
        print(f"Return (bot):      {result['return_pct']:10.2f}%  -> {(1 + result['return_pct'] / 100) ** (1 / years) * 100 - 100:6.2f}% annuo")
        print(f"Return (buy&hold): {hold_return:10.2f}%  -> {(1 + hold_return / 100) ** (1 / years) * 100 - 100:6.2f}% annuo")

        wins = 0
        segments = split_segments(data, config.BACKTEST_SEGMENTS)
        for segment in segments:
            seg_bot = run_backtest(segment)["return_pct"]
            seg_hold = buy_and_hold_return_pct(segment)
            wins += seg_bot > seg_hold
            print(f"  {segment.iloc[0]['timestamp'].date()} -> {segment.iloc[-1]['timestamp'].date()} | bot {seg_bot:8.2f}% | buy&hold {seg_hold:8.2f}%")
        print(f"  Il bot batte il buy&hold in {wins}/{len(segments)} periodi\n")
