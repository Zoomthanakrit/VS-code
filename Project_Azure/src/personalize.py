"""Stage 5 - Personalize: the same match, told differently for each viewer.

A viewer profile changes:
  - WHICH moments are shown   (all goals + the best other moments for this viewer)
  - HOW they are explained    (fan = simple, analyst = stats, focus metric, language)
  - EXTRA content             (player focus card that follows one player all match)

Every text still goes through the grounding check from explain.py.
AI answers are saved in data/cache/, so the same moment + profile is never paid for twice.

Run:
    python src/personalize.py --mode fan --lang en --team "Chao Phraya Rovers"
    python src/personalize.py --mode analyst --lang th --player "Ali Demir" --focus shooting
    python src/personalize.py --mode fan --lang en --minute 60          (live: only what happened before 60')

Output:
    data/match_007_overlay_<profile>.json   (timed, machine-readable overlays for the screen)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from explain import LANGUAGES, grounded_answer, make_client, moment_facts, recap_facts  # noqa: E402
from interpret import interpret  # noqa: E402

STYLE = {
    "fan": ("a casual fan. Be short, lively and easy to understand. No jargon, no 'xG'. "
            "Use at most ONE number. 1-2 sentences."),
    "analyst": ("a data-hungry analyst. Be precise and tactical. Use 3-5 numbers from FACTS "
                "(xG, possession, pressures, pass accuracy) to explain the pattern. 2-3 sentences."),
}

FOCUS = {
    "shooting": "The viewer cares most about shooting: shot quality (xG), distance and shot speed.",
    "passing": "The viewer cares most about passing: pass accuracy and how hard the passes were.",
    "pressing": "The viewer cares most about pressing: pressures, ball wins and who forced mistakes.",
    "possession": "The viewer cares most about control: possession and who dictated the rhythm.",
}

# How long each overlay stays on screen (seconds of match time).
ON_SCREEN = {"goal": 20, "big_chance_missed": 12, "great_save": 12, "momentum_swing": 15,
             "pressing_spell": 15, "yellow_card": 8, "fastest_shot": 10, "player_focus": 12}

# Max non-goal moments of one type, so the story has variety.
MAX_PER_TYPE = 2

CACHE_DIR = Path("data/cache")

# Safety cap for a public website: max new AI cards per app start (cached cards are free and unlimited).
# Set AI_BUDGET in the environment; default = no limit when you run it on your own laptop.
AI_CALLS_LEFT = int(os.environ.get("AI_BUDGET", "1000000"))


@dataclass
class Profile:
    mode: str = "fan"              # fan | analyst
    language: str = "en"           # en | th
    favorite_team: str | None = None
    favorite_player: str | None = None
    focus: str | None = None       # shooting | passing | pressing | possession

    def slug(self) -> str:
        parts = [self.mode, self.language, self.favorite_team, self.favorite_player, self.focus]
        return "_".join(str(p).replace(" ", "-").lower() for p in parts if p)


# --- Matching what the viewer typed to real names ------------------------------------------

def match_team(text: str | None, match: dict) -> str | None:
    """'rovers', 'home', 'CPR' or the full name -> 'Chao Phraya Rovers'."""
    if not text:
        return None
    t = text.strip().lower()
    home, away = match["home_team"], match["away_team"]
    if t in ("home", home.lower()) or t in home.lower() or t == "".join(w[0] for w in home.split()).lower():
        return home
    if t in ("away", away.lower()) or t in away.lower() or t == "".join(w[0] for w in away.split()).lower():
        return away
    sys.exit(f"Team '{text}' not found. Choose '{home}' or '{away}'.")


def match_player(text: str | None, players: list[dict]) -> str | None:
    """'demir' or 'Ali Demir' -> 'Ali Demir'."""
    if not text:
        return None
    hits = [p["player"] for p in players if text.strip().lower() in p["player"].lower()]
    if not hits:
        sys.exit(f"Player '{text}' not found. Try one of: {', '.join(p['player'] for p in players[:8])} ...")
    return hits[0]


# --- 1. WHICH moments --------------------------------------------------------------------

def choose_moments(moments: list[dict], profile: Profile, extra: int) -> list[dict]:
    """Every goal, plus the best `extra` other moments for this viewer (max 2 of each type)."""
    def score(m: dict) -> float:
        s = m["importance"]
        if profile.favorite_team and m["team"] == profile.favorite_team:
            s += 1.5
        if profile.favorite_player and m["player"] == profile.favorite_player:
            s += 3
        if profile.focus == "shooting" and m["type"] in ("big_chance_missed", "great_save", "fastest_shot"):
            s += 1
        if profile.focus in ("pressing", "possession") and m["type"] in ("pressing_spell", "momentum_swing"):
            s += 1.5
        return s

    picked = [m for m in moments if m["type"] == "goal"]
    per_type: dict[str, int] = {}
    others = [m for m in moments if m["type"] != "goal"]
    for m in sorted(others, key=lambda m: (-score(m), m["minute"])):
        if len(picked) - sum(p["type"] == "goal" for p in picked) >= extra:
            break
        if per_type.get(m["type"], 0) < MAX_PER_TYPE:
            picked.append(m)
            per_type[m["type"]] = per_type.get(m["type"], 0) + 1
    picked = [{**m, "for_you": score(m) > m["importance"]} for m in picked]
    return sorted(picked, key=lambda m: (m["minute"], m["second"]))


# --- 2. HOW they are explained -----------------------------------------------------------

def task_text(profile: Profile, what: str) -> str:
    parts = [f"{what} Write in {LANGUAGES[profile.language]} for {STYLE[profile.mode]}"]
    if profile.favorite_team:
        parts.append(f"The viewer supports {profile.favorite_team}. Speak to them as a supporter "
                     "(warm when their team does well, honest when it doesn't), but keep every fact neutral.")
    if profile.favorite_player:
        parts.append(f"The viewer's favorite player is {profile.favorite_player}. Mention them if they are involved.")
    if profile.focus:
        parts.append(FOCUS[profile.focus])
    return " ".join(parts)


def cached_answer(client, deployment, key: dict, task: str, facts: dict, fallback: str) -> dict:
    """Same moment + same profile = reuse the saved answer (faster, and no extra cost)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha1(json.dumps({**key, "task": task, "facts": facts}, sort_keys=True, default=str)
                        .encode()).hexdigest()[:16]
    path = CACHE_DIR / f"{name}.json"
    if path.exists():
        return {**json.loads(path.read_text(encoding="utf-8")), "cached": True}
    global AI_CALLS_LEFT
    if client is None or AI_CALLS_LEFT <= 0:  # no AI (no .env) or budget used up: plain, fact-based headline
        return {"headline": fallback, "commentary": "", "grounded": True, "cached": False, "offline": True}
    AI_CALLS_LEFT -= 1
    answer = grounded_answer(client, deployment, task, facts, fallback)
    if answer["grounded"]:  # only keep good answers
        path.write_text(json.dumps(answer, ensure_ascii=False), encoding="utf-8")
    return {**answer, "cached": False}


# --- 3. EXTRA: player focus card ---------------------------------------------------------

def player_card(match_file: Path, player: str, up_to_minute: int) -> list[dict]:
    """The favorite player's stats at the end of each 15 minutes (no AI, pure numbers)."""
    card = []
    for minute in range(15, min(up_to_minute, 90) + 1, 15):
        stats = interpret(match_file, up_to_minute=minute)
        p = next((p for p in stats["player_stats"] if p["player"] == player), None)
        if p:
            card.append({"minute": minute, **{k: p[k] for k in ("passes", "pass_accuracy_pct", "shots", "xg",
                                                                 "goals", "pressures", "ball_wins")}})
    return card


# --- Build the overlay -------------------------------------------------------------------

def build_overlay(match_file: Path, profile: Profile, extra: int = 6, up_to_minute: int = 999,
                  client=None, deployment: str = "") -> dict:
    so_far = interpret(match_file, up_to_minute)
    moments = choose_moments(so_far["key_moments"], profile, extra)
    match_key = {"match": match_file.name, "profile": asdict(profile)}

    overlays = []
    for m in moments:
        facts = moment_facts(match_file, m)
        task = task_text(profile, "Explain why this moment matters for the match.")
        answer = cached_answer(client, deployment, {**match_key, "moment": [m["minute"], m["second"], m["type"]]},
                               task, facts, fallback=m["headline"])
        t = m["minute"] * 60 + m["second"]
        overlays.append({
            "t": t, "show_at": f"{m['minute']:02d}:{m['second']:02d}",
            "duration_s": ON_SCREEN.get(m["type"], 10), "kind": m["type"],
            "team": m["team"], "player": m["player"], "for_you": m["for_you"],
            "headline": answer["headline"], "text": answer["commentary"],
            "grounded": answer["grounded"], "cached": answer["cached"],
        })
        print(f"  {m['minute']:>2}' {'★' if m['for_you'] else ' '} [{'OK' if answer['grounded'] else 'FALLBACK'}"
              f"{', cached' if answer['cached'] else ''}] {answer['headline']}\n       {answer['commentary']}")

    result = {"profile": asdict(profile), "match": so_far["match"], "overlays": overlays}

    if profile.favorite_player:
        result["player_card"] = player_card(match_file, profile.favorite_player, so_far["match"]["minute"] + 1)

    if so_far["match"]["finished"]:
        task = task_text(profile, "Write a 3-4 sentence match recap: how the match was won, "
                                  "control, pressure and turning points.")
        final = f"Full time: {so_far['match']['score_home']}-{so_far['match']['score_away']}"
        recap = cached_answer(client, deployment, {**match_key, "recap": True}, task, recap_facts(so_far), final)
        result["recap"] = {"headline": recap["headline"], "text": recap["commentary"], "grounded": recap["grounded"]}
        print(f"\n  RECAP [{'OK' if recap['grounded'] else 'FALLBACK'}] {recap['headline']}\n       {recap['commentary']}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Personalized, timed match overlays.")
    parser.add_argument("--match", default="data/match_007.jsonl")
    parser.add_argument("--mode", choices=STYLE, default="fan")
    parser.add_argument("--lang", choices=LANGUAGES, default="en")
    parser.add_argument("--team", help="Favorite team, e.g. 'Chao Phraya Rovers', 'home', 'rovers'")
    parser.add_argument("--player", help="Favorite player, e.g. 'Ali Demir' or 'demir'")
    parser.add_argument("--focus", choices=FOCUS, help="The one thing you care about most")
    parser.add_argument("--extra", type=int, default=6, help="How many non-goal moments to add (all goals are shown)")
    parser.add_argument("--minute", type=int, default=999, help="Live mode: only events before this minute")
    args = parser.parse_args()

    match_file = Path(args.match)
    full = interpret(match_file)
    profile = Profile(mode=args.mode, language=args.lang,
                      favorite_team=match_team(args.team, full["match"]),
                      favorite_player=match_player(args.player, full["player_stats"]),
                      focus=args.focus)
    print(f"Profile: {asdict(profile)}\n")

    client, deployment = make_client()
    result = build_overlay(match_file, profile, args.extra, args.minute, client, deployment)

    out_file = match_file.with_name(f"{match_file.stem}_overlay_{profile.slug()}.json")
    out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nSaved {out_file}")
    if "player_card" in result:
        print(f"Player card for {profile.favorite_player}:")
        for row in result["player_card"]:
            print(f"  {row['minute']:>2}'  passes {row['passes']:>3}  shots {row['shots']}  xG {row['xg']}"
                  f"  goals {row['goals']}  pressures {row['pressures']}")


if __name__ == "__main__":
    main()
