"""Stage 4 - Render: the web app that replays a match with live stats and AI overlays.

Run (from the Project_Azure folder):
    python src/app.py
Then open http://127.0.0.1:8000

API (the web page calls these):
    GET /api/match                      teams, lineups, venue
    GET /api/events                     every event (the page replays them on the pitch)
    GET /api/state?minute=60            score, team stats and timeline at that minute
    GET /api/overlays?minute=60&mode=fan&lang=th&team=...&player=...&focus=...
                                        personalized, fact-checked AI cards up to that minute
"""

from __future__ import annotations

import json
import os
import sys
import threading
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

sys.path.insert(0, str(Path(__file__).parent))
from explain import make_client  # noqa: E402
from interpret import interpret  # noqa: E402
from personalize import FOCUS, STYLE, Profile, build_overlay  # noqa: E402
from explain import LANGUAGES  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]
os.chdir(PROJECT_DIR)  # so data/ paths work wherever you start it from
MATCH_FILE = Path(os.environ.get("MATCH_FILE", "data/match_007.jsonl"))
STATIC_DIR = Path(__file__).parent / "static"

if not MATCH_FILE.exists():
    sys.exit(f"{MATCH_FILE} not found. Run: python src/generate_match.py --seed 7")

EVENTS = [json.loads(line) for line in MATCH_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
FULL = interpret(MATCH_FILE)

try:
    CLIENT, DEPLOYMENT = make_client()
    AI_STATUS = f"connected ({DEPLOYMENT})"
except SystemExit as reason:  # no .env: the app still works, cards show plain headlines
    CLIENT, DEPLOYMENT = None, ""
    AI_STATUS = "offline (no .env) - cards show fact-based headlines"
    print(f"AI not connected: {reason}")

AI_LOCK = threading.Lock()  # one AI build at a time, so we never pay twice for the same card

app = FastAPI(title="Match Story")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "ai": AI_STATUS, "match": MATCH_FILE.name}


@app.get("/api/match")
def match() -> dict:
    start = EVENTS[0]
    return {
        **FULL["match"],
        "lineups": start["lineups"],
        "ai": AI_STATUS,
        "options": {"mode": list(STYLE), "lang": list(LANGUAGES), "focus": list(FOCUS)},
    }


@app.get("/api/events")
def events() -> list[dict]:
    keep = ("id", "minute", "second", "type", "team_side", "player", "x", "y", "end_x", "end_y", "outcome")
    return [{k: e[k] for k in keep if k in e} for e in EVENTS if e["type"] != "match_start"]


@lru_cache(maxsize=128)
def state_at(minute: int) -> dict:
    s = interpret(MATCH_FILE, up_to_minute=minute)
    return {"match": s["match"], "team_stats": s["team_stats"], "timeline": s["timeline"]}


@app.get("/api/state")
def state(minute: int = 999) -> dict:
    return state_at(max(0, min(minute, 999)))


@app.get("/api/overlays")
def overlays(minute: int = 999, mode: str = "fan", lang: str = "en", team: str | None = None,
             player: str | None = None, focus: str | None = None) -> dict:
    if mode not in STYLE or lang not in LANGUAGES or (focus and focus not in FOCUS):
        raise HTTPException(400, "Unknown mode, language or focus")
    teams = (FULL["match"]["home_team"], FULL["match"]["away_team"])
    players = {p["player"] for p in FULL["player_stats"]}
    profile = Profile(mode=mode, language=lang,
                      favorite_team=team if team in teams else None,
                      favorite_player=player if player in players else None,
                      focus=focus or None)
    with AI_LOCK:
        return build_overlay(MATCH_FILE, profile, extra=6, up_to_minute=max(1, minute),
                             client=CLIENT, deployment=DEPLOYMENT)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"AI: {AI_STATUS}\nOpen http://127.0.0.1:{port}")
    uvicorn.run(app, host=host, port=port)
