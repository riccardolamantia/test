"""Rendering 2D di un highlight in MP4: mappa dall'alto a sinistra, pannello info a destra."""

import math
import shutil
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .demo import CT, T, TICKRATE

WIDTH, HEIGHT = 1280, 720
MAP = 720  # lato della mappa nel video
SS = 2  # la mappa si disegna al doppio e poi si riduce: bordi puliti senza antialiasing
FPS = 32  # a velocità normale ogni frame avanza di 2 tick

TEAM_COLOR = {T: (232, 163, 61), CT: (88, 150, 235)}
TEAM_NAME = {T: "T", CT: "CT"}
PANEL_BG = (24, 27, 33)
TEXT = (235, 238, 243)
MUTED = (140, 148, 160)
ACCENT = (255, 214, 92)
RED = (235, 75, 75)

ROUND_TIME = 115
BOMB_TIME = 40
SMOKE_RADIUS = 144
FIRE_RADIUS = 120
TRACER = 260
GRENADE_COLOR = {
    "CSmokeGrenadeProjectile": (215, 220, 228),
    "CFlashbangProjectile": (255, 255, 255),
    "CHEGrenadeProjectile": (240, 90, 70),
    "CMolotovProjectile": (255, 140, 40),
}
NOT_GUNS = ("knife", "bayonet", "c4", "grenade", "flashbang", "molotov", "incgrenade", "decoy", "smoke", "hegrenade")


@lru_cache(maxsize=None)
def font(size, bold=False):
    candidates = (
        ["DejaVuSans-Bold.ttf", "segoeuib.ttf", "arialbd.ttf", "Arial Bold.ttf"] if bold
        else ["DejaVuSans.ttf", "segoeui.ttf", "arial.ttf", "Arial.ttf"]
    )
    dirs = ["", "/usr/share/fonts/truetype/dejavu/", "C:/Windows/Fonts/", "/Library/Fonts/",
            "/System/Library/Fonts/Supplemental/"]
    for name in candidates:
        for d in dirs:
            try:
                return ImageFont.truetype(d + name, size)
            except OSError:
                continue
    return ImageFont.load_default(size)


def ffmpeg_exe():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise SystemExit("ffmpeg non trovato: installa ffmpeg oppure `pip install imageio-ffmpeg`.")


def _short(name, n=16):
    name = str(name)
    return name if len(name) <= n else name[: n - 1] + "…"


class ClipData:
    """Tutto ciò che serve per disegnare un highlight, già filtrato sulla sua finestra."""

    def __init__(self, demo, highlight, ticks):
        self.h = highlight
        self.round = demo.rounds[highlight.round - 1]
        t0, t1 = highlight.start_tick, highlight.end_tick
        r = self.round

        self.players = {}
        for tick, group in ticks[(ticks["tick"] >= t0) & (ticks["tick"] <= t1)].groupby("tick"):
            self.players[int(tick)] = list(group.itertuples(index=False))

        in_round = lambda df: df[(df["tick"] >= r.start_tick) & (df["tick"] <= t1)] if not df.empty else df
        in_clip = lambda df, before=0: df[(df["tick"] >= t0 - before) & (df["tick"] <= t1)] if not df.empty else df

        self.kills = in_round(demo.kills)
        self.shots = in_clip(demo.event("weapon_fire"), 8)
        self.shots = self.shots[~self.shots["weapon"].astype(str).str.contains("|".join(NOT_GUNS))]
        self.blinds = in_clip(demo.event("player_blind"), 6 * TICKRATE)
        self.grenades = in_clip(demo.grenades(), 32)
        self.flashes = in_clip(demo.event("flashbang_detonate"), 16)
        self.explosions = in_clip(demo.event("hegrenade_detonate"), 16)
        self.smokes = self._areas(demo, "smokegrenade_detonate", "smokegrenade_expired", 18)
        self.fires = self._areas(demo, "inferno_startburn", "inferno_expire", 7)

        plant = in_round(demo.event("bomb_planted"))
        self.plant = plant.iloc[0] if not plant.empty else None
        self.defuse = next(iter(in_round(demo.event("bomb_defused"))["tick"]), None) if self.plant is not None else None

        self.focus = str(highlight.player_id)
        self.key_ticks = highlight.key_ticks
        interesting = list(self.kills["tick"]) + list(highlight.key_ticks)
        mine = self.shots[self.shots["user_steamid"].astype(str) == self.focus]["tick"]
        self.interesting = np.array(sorted(interesting + list(mine)), dtype=float)

    def _areas(self, demo, start_event, end_event, default_seconds):
        """Fumi e molotov: (x, y, tick inizio, tick fine) attivi durante la clip."""
        starts, ends = demo.event(start_event), demo.event(end_event)
        areas = []
        for _, s in starts.iterrows():
            if "x" not in s:
                continue
            end = ends[(ends["tick"] > s["tick"])]
            if "entityid" in ends.columns:
                end = end[end["entityid"] == s["entityid"]]
            end_tick = int(end["tick"].iloc[0]) if not end.empty else int(s["tick"]) + default_seconds * TICKRATE
            if end_tick >= self.h.start_tick and s["tick"] <= self.h.end_tick:
                areas.append((s["x"], s["y"], int(s["tick"]), end_tick))
        return areas

    def schedule(self):
        """Tick da disegnare, uno per frame: rallenta sulle kill chiave, accelera nei tempi morti."""
        frames = []
        t = self.h.start_tick
        while t <= self.h.end_tick:
            near_key = any(abs(t - k) <= 20 for k in self.key_ticks)
            if near_key:
                step, mode = 1, "SLOW-MO"
            elif self._quiet(t):
                step, mode = 8, "4x"
            else:
                step, mode = 2, ""
            frames.append((t, mode))
            t += step
        return frames

    def _quiet(self, tick):
        if not len(self.interesting):
            return True
        nearest = np.min(np.abs(self.interesting - tick))
        return nearest > 2.5 * TICKRATE


class Renderer:
    def __init__(self, demo, view, background):
        self.demo = demo
        self.view = view
        self.background = background  # RGB, lato MAP * SS
        self.map_name = demo.map_name

    # La vista è al lato MAP * SS; qui si lavora in pixel del video e si moltiplica per SS al disegno.
    def p(self, x, y):
        px, py = self.view.px(x, y)
        return px / SS, py / SS

    def u(self, length):
        return self.view.units(length) / SS

    def render(self, data, out_path):
        cmd = [
            ffmpeg_exe(), "-y", "-loglevel", "error",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS), "-i", "-",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", str(out_path),
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        frame = None
        for tick, mode in data.schedule():
            frame = self.frame(data, tick, mode)
            proc.stdin.write(frame.tobytes())
        for _ in range(FPS // 2):  # mezzo secondo fermo sull'ultimo frame
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        if proc.wait() != 0:
            raise RuntimeError(f"ffmpeg ha fallito su {out_path}")

    def frame(self, data, tick, mode):
        canvas = Image.new("RGB", (WIDTH, HEIGHT), PANEL_BG)
        canvas.paste(self.map_layer(data, tick), (0, 0))
        self.panel(canvas, data, tick, mode)
        return canvas

    # --- mappa -------------------------------------------------------------------------

    def map_layer(self, data, tick):
        img = self.background.copy()
        players = self._players_at(data, tick)
        self._areas(img, data, tick)
        d = ImageDraw.Draw(img)
        self._deaths(d, data, tick)
        self._bomb(d, data, tick)
        self._grenades(d, data, tick)
        self._tracers(d, data, tick, players)
        self._kill_lines(d, data, tick)
        self._players(d, data, tick, players)
        return img.resize((MAP, MAP), Image.LANCZOS)

    def _players_at(self, data, tick):
        for t in range(tick, tick - 8, -1):
            if t in data.players:
                return data.players[t]
        return []

    def _areas(self, img, data, tick):
        active = [(a, (205, 210, 218, 150), SMOKE_RADIUS) for a in data.smokes if a[2] <= tick <= a[3]]
        active += [(a, (255, 105, 35, 110), FIRE_RADIUS) for a in data.fires if a[2] <= tick <= a[3]]
        bursts = []
        for df, color in ((data.flashes, (255, 255, 255)), (data.explosions, (255, 120, 60))):
            for row in df.itertuples():
                age = tick - row.tick
                if 0 <= age <= 14:
                    bursts.append((row.x, row.y, age / 14, color))
        if not active and not bursts:
            return
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        for (x, y, *_), color, radius in active:
            cx, cy = self.p(x, y)
            r = self.u(radius) * SS
            d.ellipse((cx * SS - r, cy * SS - r, cx * SS + r, cy * SS + r), fill=color)
        for x, y, progress, color in bursts:
            cx, cy = self.p(x, y)
            r = self.u(80 + 260 * progress) * SS
            alpha = int(220 * (1 - progress))
            d.ellipse((cx * SS - r, cy * SS - r, cx * SS + r, cy * SS + r), outline=color + (alpha,), width=3 * SS)
        img.paste(Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB"))

    def _deaths(self, d, data, tick):
        for k in data.kills[data.kills["tick"] <= tick].itertuples():
            if math.isnan(k.user_X):
                continue
            x, y = self.p(k.user_X, k.user_Y)
            color = tuple(int(c * 0.55) for c in TEAM_COLOR.get(k.user_team_num, MUTED))
            s = 6 * SS
            x, y = x * SS, y * SS
            d.line((x - s, y - s, x + s, y + s), fill=color, width=3 * SS)
            d.line((x - s, y + s, x + s, y - s), fill=color, width=3 * SS)

    def _bomb(self, d, data, tick):
        if data.plant is None or data.plant["tick"] > tick:
            return
        x, y = self.p(data.plant["user_X"], data.plant["user_Y"])
        defused = data.defuse is not None and data.defuse <= tick
        if not defused and (tick // 16) % 2:
            return
        s = 7 * SS
        color = (90, 220, 120) if defused else RED
        d.rectangle((x * SS - s, y * SS - s, x * SS + s, y * SS + s), fill=color, outline=(0, 0, 0), width=SS)

    def _grenades(self, d, data, tick):
        g = data.grenades
        if g.empty:
            return
        recent = g[(g["tick"] <= tick) & (g["tick"] >= tick - 24)]
        for _, path in recent.groupby("grenade_entity_id"):
            if path["tick"].max() < tick - 1:
                continue  # già esplosa
            color = GRENADE_COLOR.get(str(path["grenade_type"].iloc[0]), (220, 220, 220))
            pts = [(px * SS, py * SS) for px, py in (self.p(x, y) for x, y in zip(path["x"], path["y"]))]
            if len(pts) > 1:
                d.line(pts, fill=color, width=SS)
            x, y = pts[-1]
            r = 3 * SS
            d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def _tracers(self, d, data, tick, players):
        if data.shots.empty:
            return
        by_id = {str(p.steamid): p for p in players}
        for s in data.shots[(data.shots["tick"] <= tick) & (data.shots["tick"] > tick - 4)].itertuples():
            p = by_id.get(str(s.user_steamid))
            if p is None or not p.is_alive:
                continue
            x, y = self.p(p.X, p.Y)
            yaw = math.radians(p.yaw)
            length = self.u(TRACER)
            x2, y2 = x + math.cos(yaw) * length, y - math.sin(yaw) * length
            d.line((x * SS, y * SS, x2 * SS, y2 * SS), fill=(255, 236, 150), width=SS)

    def _kill_lines(self, d, data, tick):
        for k in data.kills[(data.kills["tick"] <= tick) & (data.kills["tick"] > tick - 48)].itertuples():
            if math.isnan(k.attacker_X) or math.isnan(k.user_X):
                continue
            a, v = self.p(k.attacker_X, k.attacker_Y), self.p(k.user_X, k.user_Y)
            color = ACCENT if str(k.attacker_steamid) == data.focus else (255, 255, 255)
            d.line((a[0] * SS, a[1] * SS, v[0] * SS, v[1] * SS), fill=color, width=2 * SS)

    def _players(self, d, data, tick, players):
        blinded = set()
        for b in data.blinds.itertuples():
            if b.tick <= tick <= b.tick + b.blind_duration * TICKRATE:
                blinded.add(str(b.user_steamid))
        label_font = font(11 * SS, bold=True)
        # Il protagonista per ultimo, sopra a tutti.
        for p in sorted(players, key=lambda p: str(p.steamid) == data.focus):
            if not p.is_alive or p.team_num not in TEAM_COLOR or math.isnan(p.X):
                continue
            focus = str(p.steamid) == data.focus
            x, y = self.p(p.X, p.Y)
            x, y = x * SS, y * SS
            r = (11 if focus else 8) * SS
            yaw = math.radians(p.yaw)
            tip = (x + math.cos(yaw) * (r + 9 * SS), y - math.sin(yaw) * (r + 9 * SS))
            color = TEAM_COLOR[p.team_num]
            d.line((x, y) + tip, fill=(255, 255, 255) if focus else color, width=3 * SS)
            fill = (255, 255, 255) if str(p.steamid) in blinded else color
            d.ellipse((x - r, y - r, x + r, y + r), fill=fill,
                      outline=(255, 255, 255) if focus else (12, 14, 18), width=(3 if focus else 2) * SS)
            label = _short(p.name, 14)
            d.text((x, y + r + 3 * SS), label, font=label_font, anchor="mt",
                   fill=ACCENT if focus else TEXT, stroke_width=3, stroke_fill=(10, 12, 16))

    # --- pannello ----------------------------------------------------------------------

    def panel(self, canvas, data, tick, mode):
        d = ImageDraw.Draw(canvas)
        x0, pad = MAP, 28
        x = x0 + pad
        h, r = data.h, data.round

        # Etichette dell'highlight.
        cx, y = x, 26
        for label in h.labels:
            w = d.textlength(label, font=font(16, True)) + 20
            if cx + w > WIDTH - pad:
                cx, y = x, y + 34
            d.rounded_rectangle((cx, y, cx + w, y + 28), radius=6, fill=ACCENT)
            d.text((cx + 10, y + 14), label, font=font(16, True), fill=(20, 20, 20), anchor="lm")
            cx += w + 8
        y += 46
        d.text((x, y), _short(h.player_name, 24), font=font(30, True), fill=TEXT)
        y += 40
        d.text((x, y), f"Round {r.number}  ·  {self.map_name}", font=font(17), fill=MUTED)

        # Orologio del round o timer della bomba.
        y += 42
        planted = data.plant is not None and data.plant["tick"] <= tick
        if tick > r.end_tick:
            clock, color = "FINE ROUND", MUTED
        elif planted and not (data.defuse is not None and data.defuse <= tick):
            left = max(0, BOMB_TIME - (tick - data.plant["tick"]) / TICKRATE)
            clock, color = f"BOMBA  {left:4.1f}", RED
        elif planted:
            clock, color = "DISINNESCATA", (90, 220, 120)
        else:
            left = max(0, ROUND_TIME - (tick - r.start_tick) / TICKRATE)
            clock, color = f"{int(left) // 60}:{int(left) % 60:02d}", TEXT
        d.text((x, y), clock, font=font(34, True), fill=color)
        if mode:
            d.text((WIDTH - pad, y + 18), mode, font=font(18, True),
                   fill=ACCENT if mode == "SLOW-MO" else MUTED, anchor="rm")

        # Squadre: quella del protagonista per prima.
        y += 62
        players = self._players_at(data, tick)
        focus_team = next((p.team_num for p in players if str(p.steamid) == data.focus), T)
        for team in (focus_team, CT if focus_team == T else T):
            members = [p for p in players if p.team_num == team]
            alive = sum(bool(p.is_alive) for p in members)
            d.text((x, y), f"{TEAM_NAME[team]}  {alive} vivi", font=font(15, True), fill=TEAM_COLOR[team])
            y += 24
            for p in sorted(members, key=lambda p: (not p.is_alive, str(p.name))):
                self._player_row(d, x, y, p, str(p.steamid) == data.focus)
                y += 22
            y += 10

        # Kill feed.
        y = max(y, 548)
        feed = data.kills[data.kills["tick"] <= tick].tail(5)
        for k in feed.itertuples():
            self._feed_row(d, x, y, k, data.focus)
            y += 24
        d.text((WIDTH - 14, HEIGHT - 12), "cs2clips", font=font(13), fill=(70, 76, 88), anchor="rb")

    def _player_row(self, d, x, y, p, focus):
        alive = bool(p.is_alive)
        name_color = ACCENT if focus else (TEXT if alive else (90, 96, 108))
        d.text((x, y), _short(p.name, 18), font=font(15, focus), fill=name_color)
        bar_x, bar_w = x + 200, 110
        d.rectangle((bar_x, y + 5, bar_x + bar_w, y + 13), fill=(45, 50, 58))
        if alive:
            hp = max(0, min(100, int(p.health or 0)))
            d.rectangle((bar_x, y + 5, bar_x + bar_w * hp / 100, y + 13), fill=TEAM_COLOR[p.team_num])
            weapon = "" if p.active_weapon_name is None or p.active_weapon_name != p.active_weapon_name \
                else str(p.active_weapon_name)
            d.text((bar_x + bar_w + 12, y), _short(weapon, 13), font=font(13), fill=MUTED)

    def _feed_row(self, d, x, y, k, focus):
        mine = str(k.attacker_steamid) == focus
        if mine:
            d.rounded_rectangle((x - 6, y - 2, WIDTH - 22, y + 20), radius=4, fill=(52, 46, 28))
        cx = x
        parts = []
        if isinstance(k.attacker_name, str):
            parts.append((_short(k.attacker_name, 14), TEAM_COLOR.get(k.attacker_team_num, TEXT), True))
        weapon = str(k.weapon).upper() + (" ⊕" if k.headshot else "")
        parts.append((f"  {weapon}  ", MUTED, False))
        parts.append((_short(k.user_name, 14), TEAM_COLOR.get(k.user_team_num, TEXT), True))
        for text, color, bold in parts:
            d.text((cx, y), text, font=font(14, bold), fill=color)
            cx += d.textlength(text, font=font(14, bold))
