"""The Q&A agent: "Ask the Match".

A viewer types a question, for example "Who is in control right now?".
The AI does NOT answer from memory. It has 5 tools (small SQL look-ups) and decides
which ones to use, reads the real numbers, then answers. The fact-checker then
checks every number in the answer against what the tools returned.

Example:
    Question (minute 60): "How is Ali Demir playing?"
    1. AI calls  player_stats(player="Ali Demir")      -> passes 36, shots 3, xG 0.83, goals 2
    2. AI answers "Ali Demir has 2 goals from 3 shots (xG 0.83)..."
    3. Fact-checker: 2, 3, 0.83 all came from the tool -> approved

The AI only sees what has happened up to the current minute, so it can't "see the future".
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import duckdb
from openai import AzureOpenAI, BadRequestError, NotFoundError

sys.path.insert(0, str(Path(__file__).parent))
from grounding import check  # noqa: E402
from interpret import TEAM_STATS_SQL, interpret, load_events, rows, zones  # noqa: E402

MAX_TOOL_ROUNDS = 4
MAX_QUESTION_CHARS = 200

# --- The 5 tools the AI can use -------------------------------------------------------------

TOOLS = [
    {"type": "function", "function": {
        "name": "match_overview",
        "description": "Score and team stats so far: possession, passes, pass accuracy, shots, shots on target, "
                       "xG (expected goals), pressures, tackles, fouls, cards.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "player_stats",
        "description": "Stats so far for one player (or part of a name): passes, pass accuracy, shots, xG, goals, "
                       "pressures, ball wins, saves.",
        "parameters": {"type": "object", "properties": {
            "player": {"type": "string", "description": "Player name or part of it, e.g. 'Demir'"}},
            "required": ["player"]}}},
    {"type": "function", "function": {
        "name": "key_moments",
        "description": "Key moments so far (goals, big chances missed, great saves, cards, pressing spells, "
                       "momentum swings), with the numbers behind each one.",
        "parameters": {"type": "object", "properties": {
            "team": {"type": "string", "description": "Optional: only this team"}}}}},
    {"type": "function", "function": {
        "name": "period_stats",
        "description": "Team stats for a time window, e.g. the last 10 minutes (from_minute=50, to_minute=60). "
                       "Use it for 'right now', 'recently' or 'second half' questions. Also returns where the "
                       "ball was (thirds of the pitch).",
        "parameters": {"type": "object", "properties": {
            "from_minute": {"type": "integer"}, "to_minute": {"type": "integer"}},
            "required": ["from_minute", "to_minute"]}}},
    {"type": "function", "function": {
        "name": "pulse_and_zones",
        "description": "Match Pulse for the last 5 minutes (control % per team, chaos 0-100) and where each team "
                       "plays (defensive / middle / attacking third).",
        "parameters": {"type": "object", "properties": {}}}},
]


def run_tool(name: str, args: dict, match_file: Path, minute: int) -> dict:
    """Run one tool and return its result (plain numbers from SQL)."""
    so_far = interpret(match_file, up_to_minute=minute)
    if name == "match_overview":
        return {"score": f"{so_far['match']['home_team']} {so_far['match']['score_home']}-"
                         f"{so_far['match']['score_away']} {so_far['match']['away_team']}",
                "minute": so_far["match"]["minute"], "team_stats": so_far["team_stats"]}
    if name == "player_stats":
        text = str(args.get("player", "")).strip().lower()
        found = [p for p in so_far["player_stats"] if text and text in p["player"].lower()]
        return {"players": found[:3]} if found else {"error": f"No player matching '{args.get('player')}'"}
    if name == "key_moments":
        team = str(args.get("team") or "").lower()
        moments = [{k: m[k] for k in ("minute", "type", "team", "player", "headline", "facts")}
                   for m in so_far["key_moments"] if not team or team in str(m["team"]).lower()]
        return {"key_moments": moments}
    if name == "period_stats":
        start = max(0, int(args.get("from_minute", 0)))
        end = min(minute, int(args.get("to_minute", minute)))
        con = duckdb.connect()
        load_events(con, match_file, end)
        con.execute(f"DELETE FROM events WHERE minute < {start} AND type <> 'match_start'")
        return {"from_minute": start, "to_minute": end, "team_stats": rows(con, TEAM_STATS_SQL),
                "territory": zones(con, end)["territory"]}
    if name == "pulse_and_zones":
        return {"pulse": so_far["pulse"], "zones": so_far["zones"]}
    return {"error": f"Unknown tool {name}"}


# --- Talking to the AI ----------------------------------------------------------------------

def chat(client, deployment: str, **kwargs):
    """One AI call. Drops options a model doesn't support and falls back to the classic Azure endpoint."""
    options = {"max_completion_tokens": 3000, "reasoning_effort": "low", **kwargs}
    for _ in range(4):
        try:
            return client.chat.completions.create(model=deployment, **options)
        except BadRequestError as error:
            dropped = [o for o in ("reasoning_effort", "max_completion_tokens") if o in str(error) and o in options]
            if not dropped:
                raise
            for o in dropped:
                options.pop(o)
        except NotFoundError:
            url = urlparse(str(client.base_url))
            client = AzureOpenAI(azure_endpoint=f"{url.scheme}://{url.netloc}", api_key=client.api_key,
                                 api_version="2024-10-21")
    raise RuntimeError("AI call failed")


SYSTEM = """You are "Ask the Match", a football analyst for a live broadcast app.
The match is fictional (synthetic data). Current match minute: {minute}.

RULES:
1. Always use the tools to get numbers. Never guess or use outside knowledge.
2. Use ONLY numbers that appear in tool results. You may round them (6.4 -> 6) or show 0-1 values as %.
3. Explain WHY, not only WHAT (control, pressure, chances, momentum).
4. Answer in {language} for {audience}. 2-4 short sentences.
5. If the question is not about this match, politely say you can only answer questions about this match.
"""

AUDIENCE = {"fan": "a casual fan (simple words, at most 2 numbers)",
            "analyst": "an analyst (precise, 3-5 numbers)"}
LANGUAGE = {"en": "English", "th": "Thai", "es": "Spanish (Latin American, like a TV football commentator)", "ar": "Arabic (Modern Standard Arabic; write numbers with digits 0-9)", "ja": "Japanese (natural TV commentary; write numbers with normal digits 0-9, not full-width)", "zh": "Simplified Chinese (write numbers with normal digits 0-9)"}


def ask(question: str, match_file: Path, minute: int, client, deployment: str,
        mode: str = "fan", lang: str = "en") -> dict:
    """Answer one viewer question. Returns the answer, the tools used, and the fact-check result."""
    question = question.strip()[:MAX_QUESTION_CHARS]
    started = time.time()
    if client is None:
        return {"answer": "The AI is not connected right now, so I can't answer questions.",
                "grounded": False, "tools": [], "numbers_checked": 0, "seconds": 0}

    messages = [
        {"role": "system", "content": SYSTEM.format(minute=minute, language=LANGUAGE.get(lang, "English"),
                                                    audience=AUDIENCE.get(mode, AUDIENCE["fan"]))},
        {"role": "user", "content": question},
    ]
    used, evidence = [], [question]  # numbers in the question itself are allowed too
    answer = ""
    for _ in range(MAX_TOOL_ROUNDS + 1):
        reply = chat(client, deployment, messages=messages, tools=TOOLS, tool_choice="auto")
        msg = reply.choices[0].message
        if not msg.tool_calls:
            answer = (msg.content or "").strip()
            break
        messages.append({"role": "assistant", "content": msg.content or "",
                         "tool_calls": [{"id": c.id, "type": "function",
                                         "function": {"name": c.function.name, "arguments": c.function.arguments}}
                                        for c in msg.tool_calls]})
        for call in msg.tool_calls:
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = run_tool(call.function.name, args, match_file, minute)
            used.append({"tool": call.function.name, "args": args})
            evidence.append(result)
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(result, ensure_ascii=False, default=str)})

    # Fact-checker: every number must come from the tools (one retry, then refuse).
    result = check(answer, evidence)
    if answer and not result["ok"]:
        messages += [{"role": "assistant", "content": answer},
                     {"role": "user", "content": f"These numbers are not in the tool results: "
                                                 f"{result['bad_numbers']}. Rewrite using only tool numbers."}]
        answer = (chat(client, deployment, messages=messages).choices[0].message.content or "").strip()
        result = check(answer, evidence)
    grounded = bool(answer) and result["ok"]
    if not grounded:
        answer = ("I couldn't fully verify the numbers for that answer, so I won't guess. "
                  "Try asking about the score, a player, or the last 10 minutes.")
    return {"answer": answer, "grounded": grounded, "tools": used,
            "numbers_checked": result["checked"], "seconds": round(time.time() - started, 1)}


if __name__ == "__main__":
    from explain import make_client

    client, deployment = make_client()
    q = " ".join(sys.argv[1:]) or "Who is in control right now?"
    out = ask(q, Path("data/match_007.jsonl"), 60, client, deployment)
    print(json.dumps(out, indent=2, ensure_ascii=False))
