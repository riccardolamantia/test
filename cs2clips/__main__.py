"""cs2clips: dai una demo CS2, ottieni le clip 2D dei momenti migliori.

    python -m cs2clips partita.dem
    python -m cs2clips partita.dem --player "tuonick" --top 5
"""

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

from . import maps
from .demo import TICKRATE, Demo
from .highlights import find_highlights, matches_player
from .render import MAP, SS, ClipData, Renderer, ffmpeg_exe


def main():
    args = _parse_args()
    started = time.time()
    demo_path = Path(args.demo)
    if not demo_path.exists():
        raise SystemExit(f"Demo non trovata: {demo_path}")
    out_dir = Path(args.out) if args.out else demo_path.with_suffix("").parent / f"{demo_path.stem}_clips"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Leggo {demo_path.name}...")
    demo = Demo(demo_path)
    print(f"  {demo.map_name}, {len(demo.rounds)} round, {len(demo.kills)} kill")

    highlights = find_highlights(demo)
    if args.player:
        mine = [h for h in highlights if matches_player(h, args.player)]
        if not mine:
            names = ", ".join(sorted(set(map(str, demo.players().values()))))
            raise SystemExit(f"Nessun highlight per '{args.player}'. Giocatori nella demo: {names}")
        highlights = mine
    highlights = [h for h in highlights if h.score >= args.min_score][: args.top]
    if not highlights:
        raise SystemExit("Nessun momento abbastanza interessante in questa demo.")

    print(f"\nTrovati {len(highlights)} momenti:")
    for i, h in enumerate(highlights, 1):
        print(f"  {i:2}. [{h.score:5.0f}]  R{h.round:<3} {str(h.player_name)[:20]:20}  {h.title}")

    print("\nPreparo la mappa...")
    view, background = maps.build(demo.map_name, demo.position_samples(), MAP * SS, args.radar)

    wanted = set()
    for h in highlights:
        wanted.update(range(h.start_tick, h.end_tick + 1))
    ticks = demo.ticks(wanted)
    renderer = Renderer(demo, view, background)

    clips = []
    for i, h in enumerate(highlights, 1):
        name = f"{i:02d}_R{h.round}_{_slug(h.title)}_{_slug(h.player_name)}.mp4"
        print(f"  Render {i}/{len(highlights)}: {name}")
        renderer.render(ClipData(demo, h, ticks), out_dir / name)
        clips.append((h, name))

    if args.montage and len(clips) > 1:
        print("  Monto il video unico...")
        _montage(out_dir, [name for _, name in sorted(clips, key=lambda c: c[0].start_tick)])

    _write_index(out_dir, demo, clips)
    print(f"\nFatto in {time.time() - started:.0f}s → {out_dir.resolve()}")
    print(f"Apri {(out_dir / 'index.html').resolve()} per vederle tutte.")


def _parse_args():
    p = argparse.ArgumentParser(prog="cs2clips", description="Clip 2D dei momenti migliori di una demo CS2.")
    p.add_argument("demo", help="file .dem")
    p.add_argument("--player", help="nick (anche parziale) o SteamID64: solo i suoi momenti")
    p.add_argument("--top", type=int, default=10, help="quante clip al massimo (default 10)")
    p.add_argument("--min-score", type=float, default=15, help="punteggio minimo di un momento (default 15)")
    p.add_argument("--out", help="cartella di uscita (default: <demo>_clips accanto alla demo)")
    p.add_argument("--radar", help="PNG del radar della mappa (default: cs2clips/radars/<mappa>.png)")
    p.add_argument("--no-montage", dest="montage", action="store_false", help="non creare il video unico")
    return p.parse_args()


def _slug(text):
    return re.sub(r"[^\w]+", "-", str(text), flags=re.UNICODE).strip("-")[:30] or "x"


def _montage(out_dir, names):
    listing = out_dir / "_montage.txt"
    listing.write_text("".join(f"file '{n}'\n" for n in names), encoding="utf-8")
    subprocess.run([ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", listing.name, "-c", "copy", "montage.mp4"], cwd=out_dir, check=True)
    listing.unlink()


def _write_index(out_dir, demo, clips):
    data = [{
        "file": name, "player": str(h.player_name), "steamid": h.player_id, "round": h.round,
        "labels": h.labels, "score": round(h.score, 1),
        "start_tick": h.start_tick, "end_tick": h.end_tick,
        "seconds_in_round": round((h.start_tick - demo.rounds[h.round - 1].start_tick) / TICKRATE, 1),
    } for h, name in clips]
    (out_dir / "highlights.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    cards = "\n".join(
        f'<figure><video src="{c["file"]}" controls preload="metadata"></video>'
        f'<figcaption><b>{" · ".join(c["labels"])}</b> — {c["player"]}, round {c["round"]}'
        f'<span>{c["score"]:.0f} pt</span></figcaption></figure>'
        for c in data
    )
    montage = '<h2>Montage</h2><video src="montage.mp4" controls class="wide"></video>' \
        if (out_dir / "montage.mp4").exists() else ""
    (out_dir / "index.html").write_text(f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Highlights {demo.map_name}</title>
<style>
body{{margin:0;padding:24px;background:#16191e;color:#e8ebf0;font:15px system-ui,sans-serif}}
h1{{margin:0 0 4px}} p{{color:#8c94a0;margin:0 0 24px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:20px}}
figure{{margin:0;background:#1f232a;border-radius:10px;overflow:hidden}}
video{{width:100%;display:block;background:#000}} .wide{{max-width:960px;border-radius:10px}}
figcaption{{padding:10px 14px;display:flex;justify-content:space-between;gap:12px}}
figcaption span{{color:#ffd65c}}
</style></head><body>
<h1>Highlights · {demo.map_name}</h1><p>{demo.path.name} · {len(demo.rounds)} round</p>
{montage}<h2>Clip</h2><div class="grid">{cards}</div></body></html>
""", encoding="utf-8")


if __name__ == "__main__":
    main()
