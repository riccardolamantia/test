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
secondi, e apre una posizione long quando la media mobile veloce incrocia quella lenta
**e** il prezzo è sopra la media di tendenza (`TREND_FILTER_MA`, default 200): in un
mercato in discesa prolungata resta in liquidità invece di comprare ogni rimbalzo.
Chiude la posizione all'incrocio opposto o quando scatta lo stop-loss/take-profit.

Il backtest stampa anche una tabella di consistenza: la finestra storica viene divisa
in `BACKTEST_SEGMENTS` periodi uguali e per ognuno confronta bot e buy&hold. Una
strategia affidabile deve reggere nella maggior parte dei periodi, non solo nel totale.

## Rotazione momentum su tutto il mercato

Approccio alternativo al bot a medie mobili: invece di seguire una lista fissa di monete,
scansiona le coppie più liquide dell'exchange, le classifica per forza del trend recente
e tiene solo le migliori, ribilanciando periodicamente.

```bash
python -m src.rotation
```

La selezione a ogni ribilanciamento usa **solo** le candele fino a quel momento, e il
rendimento è misurato su ciò che accade dopo: il test non può sbirciare nel futuro.

Parametri principali (`.env`): `UNIVERSE_SIZE` (quante monete scansionare),
`MOMENTUM_LOOKBACK` (su quante candele misurare la forza), `HOLD_PERIODS` (ogni quanto
ribilanciare), `TOP_K` (quante monete tenere).

**Bias di sopravvivenza**: l'universo è scelto tra le monete più scambiate *oggi*, quindi
quelle crollate o delistate in passato non compaiono. Il risultato del test è perciò
più ottimista di quanto sarebbe stato nella realtà.

## Struttura

- `src/config.py` — parametri caricati da `.env`
- `src/exchange.py` — wrapper ccxt per dati di mercato e invio ordini
- `src/strategy.py` — logica di segnale (SMA crossover)
- `src/risk.py` — stop-loss / take-profit
- `src/backtest.py` — backtest su dati storici
- `src/universe.py` — scansione delle coppie più liquide dell'exchange
- `src/rotation.py` — backtest della rotazione momentum su tutto il mercato
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

## Azioni ed ETF

La stessa strategia, applicata a indici azionari ed ETF tramite Yahoo Finance, su
decenni di storico invece dei pochi anni di dati crypto utilizzabili:

```bash
python -m src.stocks
```

I prezzi sono corretti per dividendi e frazionamenti, quindi il confronto con il
buy&hold è sul rendimento totale. Ticker e profondità storica si impostano con
`STOCK_TICKERS` e `STOCK_YEARS` nel `.env`.

Due differenze importanti rispetto al crypto, a sfavore del bot:

- **Le borse chiudono.** Su una brutta notizia notturna il prezzo riapre già sotto e lo
  stop-loss viene scavalcato, non ti protegge. Il crypto è aperto 24/7.
- **Le commissioni sono spesso fisse** (1-3€ a operazione dai broker italiani): su una
  posizione da 200€ significa l'1%, dieci volte lo 0,1% simulato qui.

## Risultati dei test (misurati, non stimati)

Tutti i numeri sotto includono le commissioni (0,1% per operazione) e provengono da dati
storici reali di Binance. Il confronto è sempre contro l'alternativa più semplice
possibile: comprare e non fare nulla.

| Strategia | Periodo | Risultato | Non fare nulla |
|---|---|---|---|
| SMA crossover, solo BTC | 4 mesi | +4,70% | -6,96% |
| SMA crossover, 5 monete | 4 mesi | +8,32% | -1,48% |
| SMA crossover + filtro trend, 5 monete | 1 anno | **-13,28%** | -39,72% |
| Rotazione momentum, 30 monete | 2 anni | **-66,05%** | +15,92% |
| SMA + filtro trend, S&P 500 | 20 anni | +138,86% (4,45%/anno) | +475,34% (9,15%/anno) |
| SMA + filtro trend, SPY | 20 anni | +166,04% (5,02%/anno) | +725,88% (11,14%/anno) |
| SMA + filtro trend, Nasdaq (QQQ) | 20 anni | +269,02% (6,75%/anno) | +1965,79% (16,35%/anno) |
| SMA + filtro trend, MSCI World | 17 anni | +98,15% (4,11%/anno) | +633,00% (12,45%/anno) |

Tre lezioni che i numeri mostrano chiaramente:

1. **Le finestre brevi ingannano.** Le prime due righe sembravano promettenti. La stessa
   strategia, testata su un anno, ha perso. Un backtest su pochi mesi non dice nulla.
2. **Provare tante strategie finché una "funziona" fabbrica illusioni.** Su abbastanza
   tentativi, il caso produce sempre un vincitore apparente. È il motivo per cui questo
   progetto si è fermato dopo tre strategie invece di cercarne una quarta.
3. **Sulle azioni il bot guadagna, ma perde comunque contro il non fare nulla.** Sui
   vent'anni rende il 4-7% annuo contro il 9-16% del buy&hold. L'unico periodo in cui
   ha vinto è la crisi 2008: è di fatto un'assicurazione contro i crolli, pagata con
   6-8 punti percentuali all'anno di rendimento mancato.

Nessuna delle strategie costruite qui ha battuto il non fare nulla su un orizzonte
onesto. Chi riprende questo progetto dovrebbe partire da qui, non dall'entusiasmo del
primo backtest positivo.

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
