# cs2clips

Gli dai una demo di CS2 e lui fa tutto da solo: trova i momenti migliori della partita
e ne fa delle clip video in 2D, con la mappa vista dall'alto e un pannello con squadre,
vita, armi, timer e kill feed. Parte solo quando lo lanci tu: niente servizi in
background, niente che tocchi il gioco.

```bash
pip install -r cs2clips/requirements.txt
python -m cs2clips percorso/della/partita.dem
```

Opzioni utili:

```bash
python -m cs2clips partita.dem --player "tuonick"   # solo i tuoi momenti (anche nick parziale o SteamID64)
python -m cs2clips partita.dem --top 5              # al massimo 5 clip (default 10)
python -m cs2clips partita.dem --out clip/          # cartella di uscita
python -m cs2clips partita.dem --no-montage         # senza il video unico
```

Accanto alla demo viene creata la cartella `<nome demo>_clips/` con:

- una clip MP4 per ogni momento, numerate dal più bello;
- `montage.mp4`, tutte le clip in ordine di round;
- `index.html`, da aprire nel browser per guardarle tutte;
- `highlights.json`, round e tick di ogni momento, per ritrovarli nella demo in gioco.

## Cosa cerca

| Momento | Come lo riconosce |
|---|---|
| 2K, 3K, 4K, ACE | kill dello stesso giocatore a meno di 12 secondi l'una dall'altra (da 4 in su vale tutto il round); bonus se sono rapide |
| Clutch 1vN | il giocatore resta l'ultimo vivo contro N nemici e la sua squadra vince il round |
| Noscope, wallbang, attraverso il fumo, da accecato, collateral, coltello, Zeus | dai dati della kill nella demo |
| Flick | la visuale ruota di oltre 45° nei 150 ms prima della kill |
| Ninja defuse, defuse all'ultimo secondo | defuse con T ancora vivi, o con meno di 1,5 secondi sul timer |

Ogni momento prende un punteggio; nella clip il video rallenta sulle kill del
protagonista e accelera 4x nei tempi morti, così un clutch lungo resta guardabile.

## Mappe

Se in `cs2clips/radars/` c'è il radar della mappa (vedi `radars/LEGGIMI.md`), viene usato
come sfondo. Altrimenti la pianta viene ricostruita dai punti in cui i giocatori hanno
camminato durante la partita: si riconosce, ma è meno dettagliata. Sulle mappe a più
piani (Nuke, Vertigo) i piani si sovrappongono.

## Limiti

- Il rendering avviene sul processore: circa 3 secondi di calcolo per ogni secondo di video.
- Le traiettorie dei colpi sono indicative: la demo dice dove guardava chi ha sparato,
  non dove è finito il proiettile.
