"""Ricerca dei momenti migliori di una demo, con un punteggio per ordinarli."""

from dataclasses import dataclass, field

import numpy as np

from .demo import CT, T, TICKRATE

MULTIKILL_SCORE = {2: 12, 3: 35, 4: 65, 5: 100}
MULTIKILL_LABEL = {2: "2K", 3: "3K", 4: "4K", 5: "ACE"}
CLUTCH_SCORE = {1: 20, 2: 45, 3: 75, 4: 105, 5: 140}

# Due kill dello stesso giocatore distanti meno di così fanno parte della stessa azione.
CLUSTER_GAP = 12 * TICKRATE
# Una kill isolata diventa clip solo se ha qualcosa di speciale che vale almeno tanto.
SINGLE_KILL_MIN_BONUS = 10
# Rotazione della visuale (gradi) negli ultimi FLICK_TICKS prima della kill per chiamarlo flick.
FLICK_DEGREES = 45
FLICK_TICKS = 10
BOMB_TIMER = 40 * TICKRATE


@dataclass
class Highlight:
    player_id: str
    player_name: str
    round: int
    start_tick: int
    end_tick: int
    score: float
    labels: list = field(default_factory=list)
    key_ticks: list = field(default_factory=list)  # kill del protagonista, rallentate nel video

    @property
    def title(self):
        return " · ".join(self.labels)

    def merge(self, other):
        self.start_tick = min(self.start_tick, other.start_tick)
        self.end_tick = max(self.end_tick, other.end_tick)
        self.score += other.score
        self.labels += [label for label in other.labels if label not in self.labels]
        self.key_ticks = sorted(set(self.key_ticks + other.key_ticks))


def _seconds(s):
    return int(s * TICKRATE)


def _kill_tags(demo, kills):
    """Etichette e bonus per le kill fuori dal comune."""
    flicks = _flick_kills(demo, kills)
    tags = {}
    seen = set()
    for idx, k in kills.iterrows():
        found = []
        weapon = str(k["weapon"])
        if k["noscope"]:
            found.append(("NOSCOPE", 20))
        if k["penetrated"] and k["penetrated"] > 0:
            found.append(("WALLBANG", 10))
        if k["thrusmoke"]:
            found.append(("THRU SMOKE", 10))
        if k["attackerblind"]:
            found.append(("BLIND", 12))
        if weapon.startswith("knife") or weapon == "bayonet":
            found.append(("KNIFE", 25))
        if weapon == "taser":
            found.append(("ZEUS", 15))
        if idx in flicks:
            found.append(("FLICK", 15))
        key = (k["attacker_steamid"], k["tick"])
        if key in seen:
            found.append(("COLLATERAL", 20))
        seen.add(key)
        tags[idx] = found
    return tags


def _flick_kills(demo, kills):
    """Kill arrivate subito dopo una rotazione brusca della visuale."""
    if kills.empty:
        return set()
    wanted = set()
    for tick in kills["tick"]:
        wanted.update(range(int(tick) - FLICK_TICKS, int(tick) + 1))
    view = demo.ticks(wanted, props=["yaw", "pitch"])
    view = view.set_index(["steamid", "tick"]).sort_index()
    flicks = set()
    for idx, k in kills.iterrows():
        try:
            before = view.loc[(int(k["attacker_steamid"]), int(k["tick"]) - FLICK_TICKS)]
            at = view.loc[(int(k["attacker_steamid"]), int(k["tick"]))]
        except (KeyError, ValueError, TypeError):
            continue
        if _angle_between(before, at) >= FLICK_DEGREES:
            flicks.add(idx)
    return flicks


def _angle_between(a, b):
    def direction(v):
        yaw, pitch = np.radians(float(v["yaw"])), np.radians(float(v["pitch"]))
        return np.array([np.cos(pitch) * np.cos(yaw), np.cos(pitch) * np.sin(yaw), np.sin(pitch)])

    cos = float(np.clip(direction(a) @ direction(b), -1.0, 1.0))
    return np.degrees(np.arccos(cos))


def _valid_kills(demo):
    k = demo.kills
    real = k["attacker_steamid"].notna() & (k["attacker_steamid"] != k["user_steamid"])
    not_team = k["attacker_team_num"] != k["user_team_num"]
    return k[real & not_team]


def _multikills(demo, kills, tags):
    found = []
    for (player, rnd), group in kills.groupby(["attacker_steamid", "round"]):
        group = group.sort_values("tick")
        # Da 4 kill in su il round intero è una sola azione: i tempi morti li accelera il video.
        if len(group) >= 4:
            clusters = [group]
        else:
            clusters, current = [], [group.iloc[0]]
            for _, k in list(group.iterrows())[1:]:
                if k["tick"] - current[-1]["tick"] <= CLUSTER_GAP:
                    current.append(k)
                else:
                    clusters.append(current)
                    current = [k]
            clusters.append(current)
            clusters = [group.loc[[k.name for k in c]] for c in clusters]

        for cluster in clusters:
            n = min(len(cluster), 5)
            ticks = cluster["tick"].tolist()
            if n < 2:
                bonus = sum(b for _, b in tags[cluster.index[0]])
                if bonus < SINGLE_KILL_MIN_BONUS:
                    continue
                score, labels = 8, []
            else:
                span = (ticks[-1] - ticks[0]) / TICKRATE
                score = MULTIKILL_SCORE[n] + (15 if span <= 3 else 8 if span <= 6 else 0)
                labels = [MULTIKILL_LABEL[n]]
            for idx in cluster.index:
                for label, bonus in tags[idx]:
                    score += bonus
                    if label not in labels:
                        labels.append(label)
            found.append(Highlight(
                str(player), cluster.iloc[0]["attacker_name"], int(rnd),
                ticks[0] - _seconds(4), ticks[-1] + _seconds(2), score, labels, ticks,
            ))
    return found


def _round_rosters(demo):
    """Per ogni round, i giocatori vivi all'inizio con la loro squadra."""
    df = demo.ticks([r.start_tick for r in demo.rounds], props=["team_num", "is_alive"])
    rosters = {}
    for r in demo.rounds:
        at = df[(df["tick"] == r.start_tick) & (df["is_alive"] == True)]  # noqa: E712
        rosters[r.number] = {
            str(row.steamid): (int(row.team_num), row.name)
            for row in at.itertuples() if row.team_num in (T, CT)
        }
    return rosters


def _clutches(demo, all_kills, rosters):
    found = []
    for r in demo.rounds:
        roster = rosters.get(r.number, {})
        alive = {pid: team for pid, (team, _) in roster.items()}
        deaths = all_kills[(all_kills["round"] == r.number) & (all_kills["tick"] <= r.end_tick)]
        in_clutch = set()
        for _, death in deaths.sort_values("tick").iterrows():
            alive.pop(str(death["user_steamid"]), None)
            for team in (T, CT):
                mates = [p for p, t in alive.items() if t == team]
                enemies = [p for p, t in alive.items() if t != team]
                if len(mates) != 1 or not enemies or team in in_clutch:
                    continue
                in_clutch.add(team)
                if r.winner != team:
                    continue
                pid, n = mates[0], min(len(enemies), 5)
                own = deaths[(deaths["attacker_steamid"].astype(str) == pid) & (deaths["tick"] > death["tick"])]
                found.append(Highlight(
                    pid, roster[pid][1], r.number,
                    int(death["tick"]) - _seconds(3), r.end_tick + _seconds(1.5),
                    CLUTCH_SCORE[n], [f"CLUTCH 1v{n}"], own["tick"].astype(int).tolist(),
                ))
    return found


def _defuses(demo, rosters):
    found = []
    planted = demo.event("bomb_planted")
    defused = demo.event("bomb_defused")
    begins = demo.event("bomb_begindefuse")
    all_kills = demo.kills
    for _, d in defused.iterrows():
        tick = int(d["tick"])
        rnd = demo.round_of_tick(tick)
        r = demo.rounds[rnd - 1] if rnd else None
        if r is None:
            continue
        plant = planted[(planted["tick"] < tick) & (planted["tick"] >= r.start_tick)]
        labels, score = [], 0
        if not plant.empty and tick - int(plant["tick"].iloc[-1]) > BOMB_TIMER - _seconds(1.5):
            labels.append("LAST SECOND DEFUSE")
            score += 25
        t_alive = {pid for pid, (team, _) in rosters.get(rnd, {}).items() if team == T}
        dead = all_kills[(all_kills["round"] == rnd) & (all_kills["tick"] <= tick)]
        if t_alive - set(dead["user_steamid"].astype(str)):
            labels.append("NINJA DEFUSE")
            score += 30
        if not labels:
            continue
        mine = begins[(begins["user_steamid"] == d["user_steamid"]) & (begins["tick"] <= tick)]
        start = int(mine["tick"].iloc[-1]) if not mine.empty else tick - _seconds(10)
        found.append(Highlight(
            str(d["user_steamid"]), d["user_name"], rnd,
            start - _seconds(4), tick + _seconds(2), score, labels, [tick],
        ))
    return found


def _merge_overlapping(highlights):
    merged = []
    for h in sorted(highlights, key=lambda h: (h.player_id, h.round, h.start_tick)):
        last = merged[-1] if merged else None
        if last and last.player_id == h.player_id and last.round == h.round \
                and h.start_tick <= last.end_tick + _seconds(2):
            last.merge(h)
        else:
            merged.append(h)
    return merged


def find_highlights(demo):
    all_kills = demo.kills
    kills = _valid_kills(demo)
    tags = _kill_tags(demo, kills)
    rosters = _round_rosters(demo)
    found = _multikills(demo, kills, tags) + _clutches(demo, all_kills, rosters) + _defuses(demo, rosters)
    for h in found:
        r = demo.rounds[h.round - 1]
        h.start_tick = max(h.start_tick, r.start_tick)
        h.end_tick = min(h.end_tick, r.next_start_tick)
    return sorted(_merge_overlapping(found), key=lambda h: -h.score)


def matches_player(highlight, query):
    query = query.lower()
    return highlight.player_id == query or query in str(highlight.player_name).lower()
