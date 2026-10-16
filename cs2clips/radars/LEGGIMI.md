Metti qui i radar delle mappe, un PNG per mappa, chiamato come la mappa nella demo:
`de_mirage.png`, `de_dust2.png`, `de_inferno.png`, `de_nuke.png`, `de_ancient.png`,
`de_anubis.png`, `de_overpass.png`, `de_train.png`, `de_vertigo.png`.

Devono essere l'immagine radar intera e quadrata (quella del gioco è 1024x1024; va bene
anche ridimensionata, purché non ritagliata), perché le coordinate in `maps.py` sono
calibrate sull'immagine completa. Se un radar manca, la mappa viene ricostruita dai
movimenti dei giocatori nella demo.
