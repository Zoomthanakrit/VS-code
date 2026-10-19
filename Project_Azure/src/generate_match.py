"""Generate one synthetic football match as a stream of events.

Everything here is made up: fictional teams, fictional players, random play.
Same seed = same match, so results are repeatable.

Run:
    python src/generate_match.py --seed 7

Output:
    data/match_<seed>.jsonl   (one JSON event per line, in time order)

Pitch: 105 m x 68 m. Coordinates are from the view of the team on the ball:
they always attack towards x = 105. The goal they attack is at (105, 34).
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0
GOAL = (105.0, 34.0)
HALF_SECONDS = 45 * 60

# --- Fictional teams --------------------------------------------------------------
# skill values are between 0 and 1. Higher = better.
TEAMS = {
    "home": {
        "name": "Chao Phraya Rovers",
        "short": "CPR",
        "pass_skill": 0.84,
        "attack_skill": 0.62,
        "defend_skill": 0.55,
        "players": [
            (1, "Somchai Keeper", "GK"), (2, "Anan Wongsa", "DF"), (4, "Krit Boonmee", "DF"),
            (5, "Tawan Srisuk", "DF"), (3, "Niran Chaiya", "DF"), (6, "Pongsak Meesuk", "MF"),
            (8, "Arthit Kaewmanee", "MF"), (10, "Chanin Rattana", "MF"), (7, "Kittipong Saelim", "FW"),
            (9, "Thanawat Promma", "FW"), (11, "Surasak Inthong", "FW"),
        ],
    },
    "away": {
        "name": "Harbour Lights FC",
        "short": "HLF",
        "pass_skill": 0.80,
        "attack_skill": 0.58,
        "defend_skill": 0.60,
        "players": [
            (1, "Tom Granger", "GK"), (2, "Leo Marsh", "DF"), (5, "Owen Pike", "DF"),
            (6, "Ravi Shah", "DF"), (3, "Dan Okoro", "DF"), (4, "Finn Hale", "MF"),
            (8, "Mateo Ruiz", "MF"), (10, "Sam Kerrigan", "MF"), (7, "Jay Holt", "FW"),
            (9, "Victor Lund", "FW"), (11, "Ali Demir", "FW"),
        ],
    },
}

# How often each position gets the ball (passing) and takes shots.
TOUCH_WEIGHT = {"GK": 1, "DF": 4, "MF": 6, "FW": 4}
SHOT_WEIGHT = {"GK": 0, "DF": 1, "MF": 3, "FW": 7}


class MatchGenerator:
    def __init__(self, seed: int):
        self.rng = random.Random(seed)
        self.match_id = f"M{seed:03d}"
        self.events: list[dict] = []
        self.clock = 0  # seconds since kickoff of the current half
        self.period = 1
        self.score = {"home": 0, "away": 0}

    # --- small helpers ------------------------------------------------------------
    def other(self, side: str) -> str:
        return "away" if side == "home" else "home"

    def pick_player(self, side: str, weights: dict[str, int]) -> tuple[int, str, str]:
        players = TEAMS[side]["players"]
        return self.rng.choices(players, weights=[weights[p[2]] for p in players])[0]

    def emit(self, event_type: str, side: str | None = None, player=None, **details) -> dict:
        total = self.clock + (0 if self.period == 1 else HALF_SECONDS)
        event = {
            "id": len(self.events) + 1,
            "match_id": self.match_id,
            "period": self.period,
            "minute": total // 60,
            "second": total % 60,
            "type": event_type,
        }
        if side:
            event["team"] = TEAMS[side]["name"]
            event["team_side"] = side
        if player:
            event["player_number"], event["player"], event["position"] = player
        event.update(details)
        self.events.append(event)
        return event

    def tick(self, low: int, high: int) -> None:
        self.clock += self.rng.randint(low, high)

    # --- football logic ------------------------------------------------------------
    def expected_goals(self, x: float, y: float) -> float:
        """Chance (0-1) that a shot from (x, y) is a goal. Closer and more central = higher."""
        distance = math.dist((x, y), GOAL)
        angle = abs(y - GOAL[1]) / max(distance, 1)
        score = 1.0 - 0.18 * distance - 1.2 * angle
        return round(1 / (1 + math.exp(-score)), 3)

    def play_possession(self, side: str, x: float, y: float) -> tuple[str, float, float]:
        """Play one spell on the ball. Returns who has the ball next and where."""
        team = TEAMS[side]
        opp = self.other(side)
        carrier = self.pick_player(side, TOUCH_WEIGHT)

        for _ in range(self.rng.randint(2, 15)):  # up to 15 passes in a spell
            if self.clock >= HALF_SECONDS + self.rng.randint(60, 240):
                return side, x, y  # half is over; stoppage time used up

            # Opponent may press the ball carrier.
            under_pressure = self.rng.random() < 0.35
            if under_pressure:
                presser = self.pick_player(opp, TOUCH_WEIGHT)
                self.emit("pressure", opp, presser, x=round(PITCH_LENGTH - x, 1), y=round(PITCH_WIDTH - y, 1),
                          on_player=carrier[1])
                # A strong press can win the ball with a tackle.
                if self.rng.random() < 0.25 * TEAMS[opp]["defend_skill"]:
                    won = self.rng.random() < 0.7
                    self.emit("tackle", opp, presser, x=round(PITCH_LENGTH - x, 1), y=round(PITCH_WIDTH - y, 1),
                              outcome="won" if won else "foul", on_player=carrier[1])
                    self.tick(2, 5)
                    if won:
                        self.emit("possession_change", opp, presser, reason="tackle")
                        return opp, PITCH_LENGTH - x, PITCH_WIDTH - y
                    self.emit("foul", opp, presser, on_player=carrier[1])
                    if self.rng.random() < 0.15:
                        self.emit("card", opp, presser, card="yellow")
                    self.tick(10, 30)
                    continue  # free kick: same team keeps the ball

            # Shoot if close enough to goal.
            if x > 84 and self.rng.random() < 0.10 * team["attack_skill"] + (0.12 if x > 94 else 0):
                return self.take_shot(side, x, y)

            # Otherwise pass forward (mostly) or sideways.
            length = min(max(self.rng.gauss(17, 9), 5), 55)
            angle = self.rng.gauss(0, 1.25)  # radians: 0 = straight at goal, about 3 = backwards
            end_x = min(max(x + length * math.cos(angle), 2), 103)
            end_y = min(max(y + length * math.sin(angle), 2), 66)
            length = math.dist((x, y), (end_x, end_y))

            difficulty = min(10.0, 1 + length / 6 + (2.5 if under_pressure else 0) + (1.5 if end_x > 88 else 0))
            success_chance = team["pass_skill"] - 0.035 * difficulty + 0.15
            complete = self.rng.random() < success_chance
            receiver = self.pick_player(side, TOUCH_WEIGHT) if complete else None
            self.emit(
                "pass", side, carrier,
                x=round(x, 1), y=round(y, 1), end_x=round(end_x, 1), end_y=round(end_y, 1),
                length_m=round(length, 1), difficulty=round(difficulty, 1),
                under_pressure=under_pressure, outcome="complete" if complete else "intercepted",
                recipient=receiver[1] if receiver else None,
            )
            self.tick(2, 7)

            if not complete:
                interceptor = self.pick_player(opp, TOUCH_WEIGHT)
                self.emit("interception", opp, interceptor, x=round(PITCH_LENGTH - end_x, 1),
                          y=round(PITCH_WIDTH - end_y, 1))
                self.emit("possession_change", opp, interceptor, reason="interception")
                return opp, PITCH_LENGTH - end_x, PITCH_WIDTH - end_y

            carrier, x, y = receiver, end_x, end_y

        # Spell ended without a shot: a loose touch gives the ball away.
        self.emit("possession_change", opp, None, reason="loose_ball")
        return opp, PITCH_LENGTH - x, PITCH_WIDTH - y

    def take_shot(self, side: str, x: float, y: float) -> tuple[str, float, float]:
        shooter = self.pick_player(side, SHOT_WEIGHT)
        xg = self.expected_goals(x, y)
        speed = round(self.rng.uniform(55, 120), 1)
        roll = self.rng.random()
        if roll < xg:
            outcome = "goal"
        elif roll < xg + 0.30:
            outcome = "saved"
        elif roll < xg + 0.55:
            outcome = "blocked"
        else:
            outcome = "off_target"

        self.emit("shot", side, shooter, x=round(x, 1), y=round(y, 1), xg=xg,
                  shot_speed_kmh=speed, distance_m=round(math.dist((x, y), GOAL), 1), outcome=outcome)
        self.tick(5, 15)
        opp = self.other(side)
        if outcome == "goal":
            self.score[side] += 1
            self.emit("goal", side, shooter, score_home=self.score["home"], score_away=self.score["away"])
            self.tick(40, 70)  # celebration
            self.emit("kickoff", opp)
            return opp, 52.5, 34.0
        if outcome == "saved":
            keeper = TEAMS[opp]["players"][0]
            self.emit("save", opp, keeper, shot_speed_kmh=speed)
        self.emit("possession_change", opp, None, reason=f"shot_{outcome}")
        return opp, 8.0, 34.0  # goal kick / keeper's ball

    def play(self) -> list[dict]:
        self.emit(
            "match_start",
            home_team=TEAMS["home"]["name"], away_team=TEAMS["away"]["name"],
            venue="Riverside Arena (fictional)", competition="Synthetic League",
            lineups={side: [{"number": n, "name": name, "position": pos} for n, name, pos in t["players"]]
                     for side, t in TEAMS.items()},
        )
        for period, first in ((1, "home"), (2, "away")):
            self.period, self.clock = period, 0
            self.emit("kickoff", first)
            side, x, y = first, 52.5, 34.0
            while self.clock < HALF_SECONDS:
                side, x, y = self.play_possession(side, x, y)
            self.emit("half_end", score_home=self.score["home"], score_away=self.score["away"])
        self.emit("match_end", score_home=self.score["home"], score_away=self.score["away"])
        return self.events


def summary(events: list[dict]) -> str:
    lines = []
    for side in ("home", "away"):
        passes = [e for e in events if e["type"] == "pass" and e.get("team_side") == side]
        done = sum(e["outcome"] == "complete" for e in passes)
        shots = [e for e in events if e["type"] == "shot" and e.get("team_side") == side]
        xg = sum(e["xg"] for e in shots)
        lines.append(f"  {TEAMS[side]['name']:<20} passes {len(passes):>3} ({done / max(len(passes), 1):.0%} complete)"
                     f" | shots {len(shots):>2} | xG {xg:.2f}")
    end = events[-1]
    lines.insert(0, f"  Final score: {TEAMS['home']['short']} {end['score_home']} - {end['score_away']} "
                    f"{TEAMS['away']['short']}  ({len(events)} events)")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a synthetic football match.")
    parser.add_argument("--seed", type=int, default=7, help="Same seed = same match.")
    parser.add_argument("--out", default="data", help="Folder for the output file.")
    args = parser.parse_args()

    events = MatchGenerator(args.seed).play()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"match_{args.seed:03d}.jsonl"
    with out_file.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")

    print(f"Saved {out_file}")
    print(summary(events))


if __name__ == "__main__":
    main()
