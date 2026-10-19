"""Stage 2 - Interpret: turn raw match events into stats and key moments.

Reads a match file made by generate_match.py and uses DuckDB (SQL on files)
to compute:
  - team stats       (possession, pass accuracy, shots, xG, pressure...)
  - player stats     (who passed, shot, pressed the most)
  - timeline         (each 15 minutes: who had the ball, who created chances)
  - key moments      (goals, big misses, great saves, momentum swings...)

Every number the AI uses later comes from here, so the AI never has to guess.

Run:
    python src/interpret.py --match data/match_007.jsonl
    python src/interpret.py --match data/match_007.jsonl --minute 60   (stats "live" at 60')

Output:
    data/match_007_stats.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import duckdb


def load_events(con: duckdb.DuckDBPyConnection, match_file: Path, up_to_minute: int) -> None:
    """Load the event file into a table called `events`, keeping only events up to the given minute."""
    con.execute(
        f"""
        CREATE OR REPLACE TABLE events AS
        SELECT *, minute * 60 + second AS t
        FROM read_json('{match_file.as_posix()}', format = 'newline_delimited', sample_size = -1)
        WHERE minute < {up_to_minute} OR type IN ('match_start')
        """
    )


def rows(con: duckdb.DuckDBPyConnection, sql: str) -> list[dict]:
    """Run SQL and return a list of dicts (one per row)."""
    cursor = con.execute(sql)
    columns = [c[0] for c in cursor.description]
    return [dict(zip(columns, r)) for r in cursor.fetchall()]


# --- Team stats ----------------------------------------------------------------------

TEAM_STATS_SQL = """
WITH passes AS (
    SELECT team_side, COUNT(*) AS passes,
           SUM(outcome = 'complete') AS passes_complete,
           ROUND(AVG(difficulty), 1) AS avg_pass_difficulty,
           SUM(outcome = 'complete' AND difficulty >= 7) AS hard_passes_complete
    FROM events WHERE type = 'pass' GROUP BY team_side
),
shots AS (
    SELECT team_side, COUNT(*) AS shots,
           SUM(outcome IN ('goal', 'saved')) AS shots_on_target,
           ROUND(SUM(xg), 2) AS xg,
           MAX(shot_speed_kmh) AS fastest_shot_kmh
    FROM events WHERE type = 'shot' GROUP BY team_side
),
defending AS (
    SELECT team_side, ANY_VALUE(team) AS team,
           SUM(type = 'pressure') AS pressures,
           SUM(type = 'tackle' AND outcome = 'won') AS tackles_won,
           SUM(type = 'interception') AS interceptions,
           SUM(type = 'foul') AS fouls,
           SUM(type = 'card') AS yellow_cards,
           SUM(type = 'goal') AS goals
    FROM events WHERE team_side IS NOT NULL GROUP BY team_side
)
SELECT d.team_side, d.team,
       d.goals,
       ROUND(100.0 * p.passes / SUM(p.passes) OVER (), 1) AS possession_pct,
       p.passes, p.passes_complete,
       ROUND(100.0 * p.passes_complete / p.passes, 1) AS pass_accuracy_pct,
       p.avg_pass_difficulty, p.hard_passes_complete,
       COALESCE(s.shots, 0) AS shots, COALESCE(s.shots_on_target, 0) AS shots_on_target,
       COALESCE(s.xg, 0) AS xg, s.fastest_shot_kmh,
       d.pressures, d.tackles_won, d.interceptions, d.fouls, d.yellow_cards
FROM defending d
JOIN passes p USING (team_side)
LEFT JOIN shots s USING (team_side)
ORDER BY d.team_side DESC  -- home first
"""

# Possession is measured the common simple way: each team's share of all passes.


# --- Player stats ----------------------------------------------------------------------

PLAYER_STATS_SQL = """
SELECT team_side, team, player, ANY_VALUE(position) AS position,
       SUM(type = 'pass') AS passes,
       ROUND(100.0 * SUM(type = 'pass' AND outcome = 'complete') / NULLIF(SUM(type = 'pass'), 0), 1)
           AS pass_accuracy_pct,
       SUM(type = 'shot') AS shots,
       ROUND(SUM(CASE WHEN type = 'shot' THEN xg ELSE 0 END), 2) AS xg,
       SUM(type = 'goal') AS goals,
       SUM(type = 'pressure') AS pressures,
       SUM(type = 'tackle' AND outcome = 'won') + SUM(type = 'interception') AS ball_wins,
       SUM(type = 'save') AS saves
FROM events
WHERE player IS NOT NULL
GROUP BY team_side, team, player
ORDER BY goals DESC, xg DESC, passes DESC
"""


# --- Timeline (15-minute blocks) -------------------------------------------------------

TIMELINE_SQL = """
SELECT LEAST(minute // 15, 5) * 15 AS from_minute,
       LEAST(minute // 15, 5) * 15 + 15 AS to_minute,
       ROUND(100.0 * SUM(type = 'pass' AND team_side = 'home') / NULLIF(SUM(type = 'pass'), 0), 1)
           AS home_possession_pct,
       ROUND(SUM(CASE WHEN type = 'shot' AND team_side = 'home' THEN xg ELSE 0 END), 2) AS home_xg,
       ROUND(SUM(CASE WHEN type = 'shot' AND team_side = 'away' THEN xg ELSE 0 END), 2) AS away_xg,
       SUM(type = 'pressure' AND team_side = 'home') AS home_pressures,
       SUM(type = 'pressure' AND team_side = 'away') AS away_pressures,
       SUM(type = 'goal' AND team_side = 'home') AS home_goals,
       SUM(type = 'goal' AND team_side = 'away') AS away_goals
FROM events
WHERE type <> 'match_start'
GROUP BY ALL
ORDER BY from_minute
"""


# --- Key moments -----------------------------------------------------------------------

def find_key_moments(con: duckdb.DuckDBPyConnection, teams: dict[str, str]) -> list[dict]:
    """Find the moments worth talking about. Each one carries the exact numbers behind it."""
    moments: list[dict] = []

    def add(minute, second, kind, side, player, importance, headline, facts):
        moments.append({
            "minute": minute, "second": second, "type": kind,
            "team": teams.get(side), "team_side": side, "player": player,
            "importance": importance, "headline": headline, "facts": facts,
        })

    # 1. Goals, with the shot that scored them.
    for r in rows(con, """
        SELECT g.minute, g.second, g.team_side, g.player, g.score_home, g.score_away,
               s.xg, s.shot_speed_kmh, s.distance_m
        FROM events g
        JOIN events s ON s.type = 'shot' AND s.outcome = 'goal' AND s.id < g.id AND s.id >= g.id - 2
        WHERE g.type = 'goal'
    """):
        add(r["minute"], r["second"], "goal", r["team_side"], r["player"], 5,
            f"GOAL! {r['player']} scores. {r['score_home']}-{r['score_away']}",
            {"xg": r["xg"], "shot_speed_kmh": r["shot_speed_kmh"], "distance_m": r["distance_m"],
             "score_home": r["score_home"], "score_away": r["score_away"]})

    # 2. Big chances missed (xG 0.25 or more but no goal).
    for r in rows(con, """
        SELECT minute, second, team_side, player, xg, distance_m, outcome
        FROM events WHERE type = 'shot' AND outcome <> 'goal' AND xg >= 0.25
    """):
        add(r["minute"], r["second"], "big_chance_missed", r["team_side"], r["player"], 3,
            f"Big chance! {r['player']} misses from {r['distance_m']} m",
            {"xg": r["xg"], "distance_m": r["distance_m"], "outcome": r["outcome"]})

    # 3. Great saves (keeper stops a shot with xG 0.2 or more).
    for r in rows(con, """
        SELECT sv.minute, sv.second, sv.team_side, sv.player AS keeper, s.player AS shooter, s.xg, s.shot_speed_kmh
        FROM events sv
        JOIN events s ON s.type = 'shot' AND s.id = sv.id - 1
        WHERE sv.type = 'save' AND s.xg >= 0.15
    """):
        add(r["minute"], r["second"], "great_save", r["team_side"], r["keeper"], 3,
            f"Great save by {r['keeper']} to deny {r['shooter']}",
            {"xg_saved": r["xg"], "shot_speed_kmh": r["shot_speed_kmh"], "shooter": r["shooter"]})

    # 4. Yellow cards.
    for r in rows(con, "SELECT minute, second, team_side, player FROM events WHERE type = 'card'"):
        add(r["minute"], r["second"], "yellow_card", r["team_side"], r["player"], 2,
            f"Yellow card for {r['player']}", {})

    # 5. Pressing spells: 10 or more pressures by one team inside 5 minutes.
    for r in rows(con, """
        SELECT minute // 5 * 5 AS from_minute, team_side, COUNT(*) AS pressures
        FROM events WHERE type = 'pressure'
        GROUP BY ALL HAVING COUNT(*) >= 10
        ORDER BY pressures DESC LIMIT 3
    """):
        add(r["from_minute"], 0, "pressing_spell", r["team_side"], None, 2,
            f"{teams[r['team_side']]} press hard: {r['pressures']} pressures in 5 minutes",
            {"pressures": r["pressures"], "from_minute": r["from_minute"], "to_minute": r["from_minute"] + 5})

    # 6. Momentum swings: a team's possession jumps 10+ points from one 15-minute block to the next.
    timeline = rows(con, TIMELINE_SQL)
    for before, after in zip(timeline, timeline[1:]):
        if before["home_possession_pct"] is None or after["home_possession_pct"] is None:
            continue
        change = round(after["home_possession_pct"] - before["home_possession_pct"], 1)
        if abs(change) >= 10:
            side = "home" if change > 0 else "away"
            new_share = after["home_possession_pct"] if side == "home" else round(100 - after["home_possession_pct"], 1)
            add(after["from_minute"], 0, "momentum_swing", side, None, 3,
                f"Momentum shift: {teams[side]} take control",
                {"possession_pct_now": new_share, "change_points": abs(change),
                 "from_minute": after["from_minute"], "to_minute": after["to_minute"]})

    # 7. Fastest shot of the match.
    for r in rows(con, """
        SELECT minute, second, team_side, player, shot_speed_kmh, outcome
        FROM events WHERE type = 'shot' ORDER BY shot_speed_kmh DESC LIMIT 1
    """):
        add(r["minute"], r["second"], "fastest_shot", r["team_side"], r["player"], 1,
            f"Rocket! {r['player']} hits the fastest shot: {r['shot_speed_kmh']} km/h",
            {"shot_speed_kmh": r["shot_speed_kmh"], "outcome": r["outcome"]})

    for m in moments:
        m["facts"] = {k: v for k, v in m["facts"].items() if v is not None}
    return sorted(moments, key=lambda m: (m["minute"], m["second"]))


# --- Put it all together ---------------------------------------------------------------

def interpret(match_file: Path, up_to_minute: int = 999) -> dict:
    con = duckdb.connect()
    load_events(con, match_file, up_to_minute)

    meta = rows(con, "SELECT match_id, home_team, away_team, venue, competition FROM events WHERE type = 'match_start'")[0]
    teams = {"home": meta["home_team"], "away": meta["away_team"]}
    team_stats = rows(con, TEAM_STATS_SQL)
    last = rows(con, "SELECT MAX(minute) AS minute FROM events WHERE type <> 'match_start'")[0]["minute"]
    score = {s["team_side"]: s["goals"] for s in team_stats}

    return {
        "match": {**meta, "minute": last, "score_home": score.get("home", 0), "score_away": score.get("away", 0),
                  "finished": up_to_minute >= 90 and last >= 90},
        "team_stats": team_stats,
        "player_stats": rows(con, PLAYER_STATS_SQL),
        "timeline": rows(con, TIMELINE_SQL),
        "key_moments": find_key_moments(con, teams),
    }


def print_summary(result: dict) -> None:
    m = result["match"]
    print(f"\n{m['home_team']} {m['score_home']} - {m['score_away']} {m['away_team']}  (minute {m['minute']})\n")
    home, away = result["team_stats"]
    for label, key in [("Possession %", "possession_pct"), ("Passes", "passes"), ("Pass accuracy %", "pass_accuracy_pct"),
                       ("Shots", "shots"), ("On target", "shots_on_target"), ("xG", "xg"),
                       ("Pressures", "pressures"), ("Tackles won", "tackles_won"),
                       ("Fastest shot km/h", "fastest_shot_kmh")]:
        print(f"  {label:<22}{home[key]!s:>8}  {away[key]!s:>8}")
    print("\nKey moments:")
    for k in result["key_moments"]:
        print(f"  {k['minute']:>2}'  {'*' * k['importance']:<5} {k['headline']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Turn match events into stats and key moments.")
    parser.add_argument("--match", default="data/match_007.jsonl", help="Match file from generate_match.py")
    parser.add_argument("--minute", type=int, default=999, help="Only use events before this minute (live mode).")
    args = parser.parse_args()

    match_file = Path(args.match)
    result = interpret(match_file, args.minute)
    out_file = match_file.with_name(match_file.stem + "_stats.json")
    out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print_summary(result)
    print(f"\nSaved {out_file}")


if __name__ == "__main__":
    main()
