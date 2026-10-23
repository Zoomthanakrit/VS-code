"""Synthetic physical (tracking) data: distance run, sprints and top speed for every player.

Real broadcasts get this from player-tracking cameras. We don't have cameras, so we
create realistic synthetic numbers, based on what each player did in the match events:
  - every player runs a base distance per minute, depending on position
    (goalkeeper ~52 m, defender ~95 m, midfielder ~106 m, forward ~98 m)
  - every action (pass, shot, tackle, pressure...) adds extra running
  - pressing and attacking actions can be sprints (24-35 km/h)

Same match file = same numbers every time (fixed random seed).

Run:
    python src/physical.py --match data/match_007.jsonl
Output:
    data/match_007_tracking.jsonl   (one row per player per minute)

Example row:
    {"minute": 51, "player": "Ali Demir", "team_side": "away", "position": "FW",
     "distance_m": 148, "sprints": 2, "top_speed_kmh": 33.4}
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

BASE_M_PER_MIN = {"GK": 52, "DF": 95, "MF": 106, "FW": 98}
EXTRA_M_PER_ACTION = 12
SPRINT_SPEED = {"GK": (20.0, 25.0), "DF": (24.5, 32.5), "MF": (25.0, 33.0), "FW": (26.0, 35.0)}
RANDOM_SPRINT_CHANCE = {"GK": 0.0, "DF": 0.10, "MF": 0.14, "FW": 0.16}
ACTIONS = {"pass", "shot", "tackle", "interception", "pressure", "foul"}


def tracking_file(match_file: Path) -> Path:
    return match_file.with_name(f"{match_file.stem}_tracking.jsonl")


def generate(match_file: Path) -> list[dict]:
    events = [json.loads(line) for line in match_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    start = events[0]
    rng = random.Random(f"tracking-{start['match_id']}")
    last_minute = max(e["minute"] for e in events)

    players = [(side, p["name"], p["position"]) for side in ("home", "away") for p in start["lineups"][side]]
    actions: dict[tuple[str, int], list[dict]] = {}
    for e in events:
        if e["type"] in ACTIONS and e.get("player"):
            actions.setdefault((e["player"], e["minute"]), []).append(e)

    rows = []
    for minute in range(last_minute + 1):
        for side, name, pos in players:
            mine = actions.get((name, minute), [])
            distance = BASE_M_PER_MIN[pos] * rng.uniform(0.85, 1.15) + EXTRA_M_PER_ACTION * len(mine)
            sprints = 0
            for e in mine:
                attacking = e["type"] == "shot" or (e["type"] == "pass" and e.get("end_x", 0) > 75)
                if (e["type"] == "pressure" and rng.random() < 0.55) or (attacking and rng.random() < 0.35):
                    sprints += 1
            if rng.random() < RANDOM_SPRINT_CHANCE[pos]:
                sprints += 1
            low, high = SPRINT_SPEED[pos]
            top = rng.uniform(low, high) if sprints else rng.uniform(14.0, 22.0)
            rows.append({"minute": minute, "player": name, "team_side": side, "position": pos,
                         "distance_m": round(distance + sprints * 25), "sprints": sprints,
                         "top_speed_kmh": round(top, 1)})
    return rows


def load(match_file: Path) -> list[dict]:
    """Read the tracking file; create it first if it doesn't exist yet."""
    path = tracking_file(match_file)
    if not path.exists():
        rows = generate(match_file)
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Create synthetic player tracking data.")
    parser.add_argument("--match", default="data/match_007.jsonl")
    args = parser.parse_args()
    match_file = Path(args.match)
    path = tracking_file(match_file)
    path.unlink(missing_ok=True)
    rows = load(match_file)
    totals: dict[str, dict] = {}
    for r in rows:
        t = totals.setdefault(r["player"], {"pos": r["position"], "km": 0, "sprints": 0, "top": 0})
        t["km"] += r["distance_m"] / 1000
        t["sprints"] += r["sprints"]
        t["top"] = max(t["top"], r["top_speed_kmh"])
    print(f"Saved {path} ({len(rows)} rows)\n")
    for name, t in sorted(totals.items(), key=lambda x: -x[1]["km"])[:8]:
        print(f"  {name:<20} {t['pos']}  {t['km']:5.1f} km  {t['sprints']:>3} sprints  top {t['top']} km/h")


if __name__ == "__main__":
    main()
