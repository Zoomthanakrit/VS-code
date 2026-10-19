# Match Story

AI match intelligence for synthetic football matches, in English and Thai.
Built for the Microsoft + Premier League "Inside the Game" Developer Hackathon (October 2026).

All teams, players, and events are synthetic (made up). No real match data or footage is used.

## Pipeline

| Stage | Status | What it does |
|---|---|---|
| 1. Ingest | done | `src/generate_match.py` creates a synthetic match as a stream of events |
| 2. Interpret | done | `src/interpret.py` turns events into team stats, player stats, a timeline, and key moments (DuckDB SQL) |
| 3. Explain | done | `src/explain.py` asks an Azure AI Foundry model why each key moment matters (fan or analyst, English or Thai). `src/grounding.py` rejects any number the AI did not get from the stats |
| 4. Render | planned | On-screen timeline and insight cards |
| 5. Personalize | planned | Fan or analyst mode, favorite team or player, English or Thai |

## Quick start

```
pip install -r requirements.txt
python src/generate_match.py --seed 7
python src/interpret.py --match data/match_007.jsonl
python src/interpret.py --match data/match_007.jsonl --minute 60   # live view at 60'
python src/explain.py --match data/match_007.jsonl --mode fan --lang en
python src/explain.py --match data/match_007.jsonl --mode analyst --lang th
```

`explain.py` needs a `.env` file (never committed) with `AZURE_AI_ENDPOINT`, `AZURE_AI_KEY`, `AZURE_AI_DEPLOYMENT`.

## How the AI stays honest

1. SQL computes every number (`interpret.py`).
2. The AI only gets those numbers, as FACTS.
3. `grounding.py` checks every number the AI writes. Example: FACTS say xG 0.47; "47% chance" passes, "60% chance" is rejected.
4. One retry, then the plain headline is shown instead. The screen never shows an invented stat.

Creates `data/match_007.jsonl`, one event per line, for example:

```json
{"id": 4, "minute": 0, "second": 2, "type": "pass", "team": "Chao Phraya Rovers", "player": "Arthit Kaewmanee",
 "x": 59.9, "y": 30.1, "end_x": 68.0, "end_y": 31.4, "length_m": 8.2, "difficulty": 2.4, "outcome": "complete"}
```

Event types: `match_start`, `kickoff`, `pass`, `pressure`, `tackle`, `interception`, `possession_change`,
`shot`, `save`, `goal`, `foul`, `card`, `half_end`, `match_end`.

Pitch is 105 m x 68 m. Coordinates are from the view of the team on the ball (they attack towards x = 105).
