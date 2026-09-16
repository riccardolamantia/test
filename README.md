# Trading bot

Bot di trading automatico basato su [ccxt](https://github.com/ccxt/ccxt), con strategia
a incrocio di medie mobili (SMA crossover), backtest su dati storici e modalità live
con esecuzione ordini sull'exchange configurato (default: Binance). Traccia e opera
in parallelo su più simboli contemporaneamente (default: BTC, ETH, SOL, BNB, XRP),
dividendo il capitale tra loro.

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

Modifica `.env` con i parametri desiderati (simboli, timeframe, medie mobili, importo
per ordine). Le chiavi API (`API_KEY`/`API_SECRET`) sono necessarie solo in modalità
live (`DRY_RUN=false`) o per operazioni autenticate.

`SYMBOLS` accetta una lista separata da virgole (es. `BTC/USDT,ETH/USDT,SOL/USDT`).
`TRADE_AMOUNT_QUOTE` è l'importo per operazione **per ogni singolo simbolo**: con 5
simboli e `TRADE_AMOUNT_QUOTE=20`, l'esposizione massima totale (se tutti i simboli
sono in posizione contemporaneamente) è 5 x 20 = 100.

## Backtest

Simula la strategia sui dati storici recenti per ogni simbolo configurato, con il
capitale diviso equamente tra loro, e stampa il rendimento per simbolo e a livello
di portafoglio, confrontato con il semplice "compra e tieni":

```bash
python -m src.backtest
```

## Esecuzione live (o dry-run)

```bash
python -m src.bot
```

Il bot controlla il segnale di ogni simbolo, in sequenza, ogni `POLL_INTERVAL_SECONDS`
secondi, e apre/chiude una posizione long quando la media mobile veloce incrocia
quella lenta (o scatta lo stop-loss/take-profit).

## Struttura

- `src/config.py` — parametri caricati da `.env`
- `src/exchange.py` — wrapper ccxt per dati di mercato e invio ordini
- `src/strategy.py` — logica di segnale (SMA crossover)
- `src/risk.py` — stop-loss / take-profit
- `src/backtest.py` — backtest su dati storici
- `src/bot.py` — loop live

## Guida passo-passo per farlo girare davvero (partendo da zero)

Questo bot è un esperimento/progetto didattico, non uno strumento per generare reddito
in modo affidabile. Segui questi passi solo con capitale che puoi permetterti di perdere.

### 1. Crea un account exchange

- Vai su [binance.com](https://www.binance.com) e registrati (serve documento d'identità
  per la verifica KYC, obbligatoria per legge).
- Deposita l'importo che vuoi rischiare (es. 100€) convertendolo nella crypto/stablecoin
  che userai come "quote currency" (es. USDT).

### 2. Genera le API key

- Nel tuo account Binance vai su *Gestione API* e crea una nuova API key.
- **Per iniziare, crea una key SENZA permesso di prelievo (withdrawal)** — solo
  lettura dati e trading spot. Così anche se qualcosa va storto, nessuno può
  spostare i tuoi fondi fuori dall'exchange.
- Copia `API_KEY` e `API_SECRET` nel file `.env` (mai condividerle, mai committarle su git —
  `.env` è già escluso da `.gitignore`).

### 3. Trova un posto dove farlo girare H24

Questa sessione di Claude è temporanea e non può tenere il bot acceso per settimane.
Ti serve un computer sempre acceso:

- **Opzione semplice**: un tuo PC/laptop sempre acceso e connesso (va bene per iniziare).
- **Opzione consigliata**: un piccolo server cloud (VPS) tipo Hetzner, DigitalOcean o
  Contabo, circa 4-5€/mese, sempre online, non dipende dal tuo PC.

Su quella macchina: installa Python, clona/copia questo progetto, esegui i comandi
della sezione **Setup** qui sopra.

### 4. Testa PRIMA in dry-run

Lascia `DRY_RUN=true` (default) per giorni/settimane e osserva i log: il bot ti dirà
cosa avrebbe comprato/venduto, senza rischiare nulla. Lancialo con:

```bash
python -m src.bot
```

Meglio ancora: usa un **account testnet** dell'exchange (dati reali, soldi finti) se
disponibile, per validare che gli ordini si piazzino correttamente prima di passare
al conto vero.

### 5. Solo dopo, valuta di passare al vero

Imposta `DRY_RUN=false` nel `.env` solo quando:
- hai fatto girare il bot in dry-run per un periodo ragionevole ed è coerente con
  quanto visto nel backtest,
- hai capito e accetti che puoi perdere l'intero capitale,
- l'importo per operazione (`TRADE_AMOUNT_QUOTE`) e i limiti di rischio
  (`STOP_LOSS_PCT`/`TAKE_PROFIT_PCT`) sono quelli che vuoi davvero.

## Limiti di questo progetto

- La strategia (incrocio di due medie mobili) è volutamente semplice: è un punto di
  partenza per imparare, non una strategia validata professionalmente.
- Il backtest include le commissioni ma non lo slippage (la differenza tra il prezzo
  atteso e quello realmente ottenuto): nella realtà i rendimenti saranno più bassi.
- Nessuna garanzia di profitto: i mercati finanziari sono imprevedibili, specialmente
  su capitali piccoli dove le commissioni pesano di più.
- Testato finora solo su pochi mesi di storico: un risultato positivo nel backtest
  non garantisce risultati futuri simili.

## Prossimi passi possibili

- Strategie aggiuntive (RSI, MACD, breakout) e selezione a runtime
- Slippage realistico nel backtest
- Limite al numero massimo di posizioni aperte contemporaneamente
- Persistenza storico operazioni e reportistica
- Notifiche (Telegram/email) sui segnali eseguiti
