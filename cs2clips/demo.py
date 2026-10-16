"""Lettura di una demo CS2: round, kill e dati per tick tramite demoparser2."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from demoparser2 import DemoParser

TICKRATE = 64
T, CT = 2, 3

# Proprietà per tick usate dal rendering.
TICK_PROPS = ["X", "Y", "yaw", "is_alive", "team_num", "health", "active_weapon_name"]


@dataclass
class Round:
    number: int
    start_tick: int  # fine del freeze time
    end_tick: int  # round_end
    next_start_tick: int  # inizio del round successivo (o fine demo)
    winner: int  # T o CT


class Demo:
    def __init__(self, path):
        self.path = Path(path)
        self.parser = DemoParser(str(self.path))
        self.map_name = self.parser.parse_header().get("map_name", "unknown")
        self.rounds = self._load_rounds()
        self.kills = self._load_kills()
        self._events = {}

    def _load_rounds(self):
        starts = sorted(self.parser.parse_event("round_freeze_end")["tick"].tolist())
        ends = self.parser.parse_event("round_end")
        rounds = []
        for i, start in enumerate(starts):
            following = ends[ends["tick"] > start]
            if following.empty:
                continue  # demo tagliata a metà round
            end = following.iloc[0]
            next_start = starts[i + 1] if i + 1 < len(starts) else int(end["tick"]) + 10 * TICKRATE
            rounds.append(Round(len(rounds) + 1, start, int(end["tick"]), next_start, int(end["winner"])))
        return rounds

    def _load_kills(self):
        kills = self.parser.parse_event("player_death", player=["X", "Y", "team_num"])
        kills = kills.sort_values("tick").reset_index(drop=True)
        kills["round"] = kills["tick"].map(self.round_of_tick)
        return kills[kills["round"].notna()].reset_index(drop=True)

    def round_of_tick(self, tick):
        for r in self.rounds:
            if r.start_tick <= tick < r.next_start_tick:
                return r.number
        return None

    def event(self, name, **kwargs):
        """Evento di gioco, in cache (lo stesso evento serve a più clip)."""
        if name not in self._events:
            try:
                df = self.parser.parse_event(name, **kwargs)
            except Exception:
                df = pd.DataFrame()
            self._events[name] = df if "tick" in df.columns else pd.DataFrame(columns=["tick"])
        return self._events[name]

    def ticks(self, ticks, props=TICK_PROPS):
        ticks = sorted(set(int(t) for t in ticks))
        if not ticks:
            return pd.DataFrame()
        return self.parser.parse_ticks(props, ticks=ticks)

    def grenades(self):
        if "_grenades" not in self._events:
            g = self.parser.parse_grenades()
            g = g[g["grenade_type"].astype(str).str.endswith("Projectile")]
            self._events["_grenades"] = g.dropna(subset=["x", "y"])
        return self._events["_grenades"]

    def position_samples(self, step=4):
        """Posizioni dei giocatori vivi lungo tutta la partita: servono a disegnare la mappa."""
        if not self.rounds:
            return np.empty((0, 2))
        ticks = range(self.rounds[0].start_tick, self.rounds[-1].end_tick, step)
        df = self.parser.parse_ticks(["X", "Y", "is_alive"], ticks=list(ticks))
        df = df[df["is_alive"] == True].dropna(subset=["X", "Y"])  # noqa: E712
        return df[["X", "Y"]].to_numpy()

    def players(self):
        names = pd.concat([self.kills["attacker_name"], self.kills["user_name"]]).dropna()
        ids = pd.concat([self.kills["attacker_steamid"], self.kills["user_steamid"]]).dropna()
        return dict(zip(ids.astype(str), names))
