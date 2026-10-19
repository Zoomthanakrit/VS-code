# Match Story

AI match intelligence for synthetic football matches, in English and Thai.
Built for the Microsoft + Premier League "Inside the Game" Developer Hackathon (October 2026).

All teams, players, and events are synthetic (made up). No real match data or footage is used.

## Pipeline

| Stage | Status | What it does |
|---|---|---|
| 1. Ingest | in progress | `src/generate_match.py` creates a synthetic match as a stream of events |
| 2. Interpret | planned | Turn events into stats (possession, pass accuracy, xG, pressure) |
| 3. Explain | planned | AI explains why key moments matter, with a grounding check on every number |
| 4. Render | planned | On-screen timeline and insight cards |
| 5. Personalize | planned | Fan or analyst mode, favorite team or player, English or Thai |

## Quick start

```
python src/generate_match.py --seed 7
```

Creates `data/match_007.jsonl`, one event per line, for example:

```json
{"id": 4, "minute": 0, "second": 2, "type": "pass", "team": "Chao Phraya Rovers", "player": "Arthit Kaewmanee",
 "x": 59.9, "y": 30.1, "end_x": 68.0, "end_y": 31.4, "length_m": 8.2, "difficulty": 2.4, "outcome": "complete"}
```

Event types: `match_start`, `kickoff`, `pass`, `pressure`, `tackle`, `interception`, `possession_change`,
`shot`, `save`, `goal`, `foul`, `card`, `half_end`, `match_end`.

Pitch is 105 m x 68 m. Coordinates are from the view of the team on the ball (they attack towards x = 105).
