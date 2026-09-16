# Trading bot

Bot di trading automatico basato su [ccxt](https://github.com/ccxt/ccxt), con strategia
a incrocio di medie mobili (SMA crossover), backtest su dati storici e modalità live
con esecuzione ordini sull'exchange configurato (default: Binance).

## Avvertenza

Il trading automatico comporta rischio di perdita di capitale. Il bot parte in modalità
`DRY_RUN=true`: logga i segnali e le operazioni simulate senza inviare ordini reali.
Passa a `DRY_RUN=false` solo dopo aver validato la strategia con il backtest e, se
possibile, con un account demo/testnet dell'exchange.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Modifica `.env` con i parametri desiderati (simbolo, timeframe, medie mobili, importo
per ordine). Le chiavi API (`API_KEY`/`API_SECRET`) sono necessarie solo in modalità
live (`DRY_RUN=false`) o per operazioni autenticate.

## Backtest

Simula la strategia sui dati storici recenti e stampa il rendimento:

```bash
python -m src.backtest
```

## Esecuzione live (o dry-run)

```bash
python -m src.bot
```

Il bot controlla il segnale ogni `POLL_INTERVAL_SECONDS` secondi e apre/chiude una
posizione long quando la media mobile veloce incrocia quella lenta.

## Struttura

- `src/config.py` — parametri caricati da `.env`
- `src/exchange.py` — wrapper ccxt per dati di mercato e invio ordini
- `src/strategy.py` — logica di segnale (SMA crossover)
- `src/backtest.py` — backtest su dati storici
- `src/bot.py` — loop live

## Prossimi passi possibili

- Strategie aggiuntive (RSI, MACD, breakout) e selezione a runtime
- Stop-loss / take-profit e position sizing basato sul rischio
- Persistenza storico operazioni e reportistica
- Notifiche (Telegram/email) sui segnali eseguiti
