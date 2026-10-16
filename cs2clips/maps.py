"""Sfondo della mappa e conversione da coordinate di gioco a pixel.

Se c'è un'immagine radar della mappa (cartella `radars/`, file `<mappa>.png`) viene
usata quella, con le coordinate ufficiali dei file overview di CS2. Altrimenti la
pianta viene ricostruita dalle posizioni dei giocatori nella demo stessa: i punti
in cui qualcuno ha camminato disegnano corridoi e siti.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter

RADAR_DIR = Path(__file__).parent / "radars"

# pos_x, pos_y, scale dei file overview: radar 1024x1024, unità di gioco per pixel.
RADAR_COORDS = {
    "de_ancient": (-2953, 2164, 5.0),
    "de_anubis": (-2796, 3328, 5.22),
    "de_dust2": (-2476, 3239, 4.4),
    "de_inferno": (-2087, 3870, 4.9),
    "de_mirage": (-3230, 1713, 5.0),
    "de_nuke": (-3453, 2887, 7.0),
    "de_overpass": (-4831, 1781, 5.2),
    "de_train": (-2308, 2078, 4.082077),
    "de_vertigo": (-3168, 1762, 4.0),
}

FLOOR = (52, 58, 68)
EDGE = (96, 106, 122)
VOID = (18, 20, 25)


class MapView:
    """Trasforma (x, y) di gioco in pixel su un'immagine quadrata di lato `size`."""

    def __init__(self, origin_x, origin_y, units_per_px, size):
        self.origin_x, self.origin_y = origin_x, origin_y
        self.units_per_px = units_per_px
        self.size = size

    def px(self, x, y):
        return ((x - self.origin_x) / self.units_per_px, (self.origin_y - y) / self.units_per_px)

    def units(self, length):
        return length / self.units_per_px


def build(map_name, samples, size, radar=None):
    """Restituisce (vista, immagine di sfondo RGB)."""
    radar = Path(radar) if radar else RADAR_DIR / f"{map_name}.png"
    if radar.exists() and map_name in RADAR_COORDS:
        pos_x, pos_y, scale = RADAR_COORDS[map_name]
        view = MapView(pos_x, pos_y, scale * 1024 / size, size)
        image = Image.open(radar).convert("RGBA").resize((size, size), Image.LANCZOS)
        background = Image.new("RGBA", (size, size), VOID + (255,))
        return view, Image.alpha_composite(background, image).convert("RGB")
    return _from_samples(samples, size)


def _from_samples(samples, size):
    lo, hi = samples.min(axis=0), samples.max(axis=0)
    extent = (hi - lo).max() * 1.08
    center = (lo + hi) / 2
    view = MapView(center[0] - extent / 2, center[1] + extent / 2, extent / size, size)

    # Ogni posizione occupa circa la larghezza di un giocatore (32 unità).
    grid = np.zeros((size, size), dtype=np.uint8)
    xs, ys = view.px(samples[:, 0], samples[:, 1])
    inside = (xs >= 0) & (xs < size) & (ys >= 0) & (ys < size)
    grid[ys[inside].astype(int), xs[inside].astype(int)] = 255
    mask = Image.fromarray(grid)
    reach = max(3, int(view.units(32)) | 1)
    close = max(3, int(view.units(80)) | 1)  # chiude i buchi lasciati dove nessuno è passato
    mask = mask.filter(ImageFilter.MaxFilter(reach))
    mask = mask.filter(ImageFilter.MaxFilter(close)).filter(ImageFilter.MinFilter(close))
    mask = mask.filter(ImageFilter.GaussianBlur(reach / 2))
    mask = mask.point(lambda v: 255 if v > 90 else 0)

    edge = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(5)), mask)
    image = Image.new("RGB", (size, size), VOID)
    image.paste(FLOOR, mask=mask)
    image.paste(EDGE, mask=edge)
    return view, image
