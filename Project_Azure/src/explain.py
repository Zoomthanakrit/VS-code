"""Stage 3 - Explain: the AI commentator.

For each key moment, the AI explains WHY it matters, using only the numbers
from interpret.py. Then the grounding check makes sure no number was invented.
If a number is wrong, the AI gets one retry. If it fails again, we show the
plain headline instead. So the screen never shows a made-up stat.

Run:
    python src/explain.py --match data/match_007.jsonl                     (fan mode, English)
    python src/explain.py --match data/match_007.jsonl --mode analyst --lang th
    python src/explain.py --match data/match_007.jsonl --dry-run           (show the prompt, no AI call)

Needs a .env file next to README.md with:
    AZURE_AI_ENDPOINT=...   AZURE_AI_KEY=...   AZURE_AI_DEPLOYMENT=...

Output:
    data/match_007_story_fan_en.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from openai import AzureOpenAI, BadRequestError, NotFoundError, OpenAI

sys.path.insert(0, str(Path(__file__).parent))
from grounding import check  # noqa: E402
from interpret import interpret  # noqa: E402

PROJECT_DIR = Path(__file__).resolve().parents[1]

LANGUAGES = {"en": "English", "th": "Thai (natural, like a Thai TV football commentator)"}

MODES = {
    "fan": "a casual fan. Be short, lively and easy to understand. No jargon. 1-2 sentences.",
    "analyst": ("a data-hungry analyst. Be precise and tactical. Use the stats (xG, possession, pressures, "
                "pass accuracy) to explain the pattern behind the moment. 2-3 sentences."),
}

SYSTEM_PROMPT = """You are an AI football commentator for a live broadcast overlay.
You explain WHY a moment matters, not only WHAT happened.
Think about: control vs chaos, pressure changes, momentum, and game rhythm.

STRICT RULES:
1. Use ONLY the numbers in FACTS. Never invent, estimate or round to a new number.
2. You may round a fact (6.4 -> 6) or show a 0-1 value as a percent (0.47 -> 47%).
3. Never mention real clubs, real players or real competitions. Everything is fictional.
4. Reply with JSON only: {"headline": "...", "commentary": "..."}
   headline = max 8 words, commentary = the explanation.
"""


# --- Connect to Azure AI Foundry -------------------------------------------------------

def make_client() -> tuple[OpenAI, str]:
    """Read .env and connect. Works with the endpoint formats Foundry shows."""
    load_dotenv(PROJECT_DIR / ".env")
    try:
        endpoint = os.environ["AZURE_AI_ENDPOINT"]
        key = os.environ["AZURE_AI_KEY"]
        deployment = os.environ["AZURE_AI_DEPLOYMENT"]
    except KeyError as missing:
        sys.exit(f"Missing {missing} in .env (file should be at {PROJECT_DIR / '.env'})")
    url = urlparse(endpoint.strip())
    base = f"{url.scheme}://{url.netloc}"  # keep only https://name.openai.azure.com
    return OpenAI(base_url=f"{base}/openai/v1/", api_key=key), deployment


def ask_ai(client: OpenAI, deployment: str, messages: list[dict]) -> tuple[dict, int, str]:
    """Send messages, return (answer with 'headline' + 'commentary', tokens used, raw reply text)."""
    # reasoning_effort=low keeps "thinking" models fast and stops them using all tokens on thinking.
    options = {"response_format": {"type": "json_object"}, "max_completion_tokens": 4000,
               "reasoning_effort": "low"}
    for _ in range(4):
        try:
            reply = client.chat.completions.create(model=deployment, messages=messages, **options)
            break
        except BadRequestError as error:  # some models don't support an option: drop it and retry
            text = str(error)
            dropped = [o for o in list(options) if o in text]
            if not dropped:
                raise
            for option in dropped:
                options.pop(option)
        except NotFoundError:  # older endpoint style: fall back to the classic Azure client
            url = urlparse(str(client.base_url))
            client = AzureOpenAI(azure_endpoint=f"{url.scheme}://{url.netloc}", api_key=client.api_key,
                                 api_version="2024-10-21")
    raw = (reply.choices[0].message.content or "").strip()
    tokens = reply.usage.total_tokens if reply.usage else 0
    return normalize(raw), tokens, raw


def normalize(raw: str) -> dict:
    """Turn the AI reply into {"headline": ..., "commentary": ...}, even if it used other key names."""
    text = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        data = json.loads(text) if text else {}
    except json.JSONDecodeError:
        return {"headline": "", "commentary": text}  # plain text instead of JSON: use it as commentary
    if isinstance(data, dict) and len(data) == 1 and isinstance(next(iter(data.values())), dict):
        data = next(iter(data.values()))  # e.g. {"th": {"headline": ...}} -> {"headline": ...}
    if not isinstance(data, dict):
        return {"headline": "", "commentary": str(data)}
    lower = {str(k).lower(): v for k, v in data.items()}
    headline = next((lower[k] for k in ("headline", "title", "heading") if k in lower), "")
    commentary = next((lower[k] for k in ("commentary", "text", "explanation", "recap", "body") if k in lower), "")
    return {"headline": str(headline).strip(), "commentary": str(commentary).strip()}


# --- Build the facts for one moment ----------------------------------------------------

def team_snapshot(stats: dict) -> list[dict]:
    keep = ["team", "goals", "possession_pct", "pass_accuracy_pct", "shots", "shots_on_target", "xg", "pressures"]
    return [{k: t[k] for k in keep} for t in stats["team_stats"]]


def moment_facts(match_file: Path, moment: dict) -> dict:
    """Everything the AI may use for one moment: the moment itself + the match so far."""
    so_far = interpret(match_file, up_to_minute=moment["minute"] + 1)
    block = next((b for b in so_far["timeline"] if b["from_minute"] <= moment["minute"] < b["to_minute"]), None)
    player = next((p for p in so_far["player_stats"] if p["player"] == moment["player"]), None)
    return {
        "moment": {k: moment[k] for k in ("minute", "type", "team", "player", "headline", "facts")},
        "score_now": f"{so_far['match']['home_team']} {so_far['match']['score_home']}-"
                     f"{so_far['match']['score_away']} {so_far['match']['away_team']}",
        "team_stats_so_far": team_snapshot(so_far),
        "this_15_minutes": block,
        "player_stats_so_far": player,
    }


def recap_facts(full: dict) -> dict:
    return {
        "final_score": f"{full['match']['home_team']} {full['match']['score_home']}-"
                       f"{full['match']['score_away']} {full['match']['away_team']}",
        "team_stats": team_snapshot(full),
        "key_moments": [{"minute": m["minute"], "headline": m["headline"], "facts": m["facts"]}
                        for m in full["key_moments"] if m["importance"] >= 3],
        "top_players": full["player_stats"][:5],
    }


# --- Ask, check, retry -----------------------------------------------------------------

def grounded_answer(client, deployment, task: str, facts: dict, fallback: str) -> dict:
    """Ask the AI, check every number, retry once, else fall back to the plain headline."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"{task}\n\nFACTS:\n{json.dumps(facts, ensure_ascii=False, default=str)}"},
    ]
    tokens, result, raw = 0, {"bad_numbers": []}, ""
    for attempt in (1, 2):
        answer, used, raw = ask_ai(client, deployment, messages)
        tokens += used
        if not answer["headline"] and not answer["commentary"]:
            # Empty reply: ask again, more clearly.
            messages.append({"role": "user", "content": 'Your reply was empty. Reply with JSON only: '
                                                        '{"headline": "...", "commentary": "..."}'})
            continue
        result = check(f"{answer['headline']} {answer['commentary']}", facts)
        if result["ok"]:
            return {**answer, "grounded": True, "attempts": attempt, "tokens": tokens}
        messages += [
            {"role": "assistant", "content": json.dumps(answer, ensure_ascii=False)},
            {"role": "user", "content": f"These numbers are not in FACTS: {result['bad_numbers']}. "
                                        "Rewrite using only numbers from FACTS."},
        ]
    return {"headline": fallback, "commentary": "", "grounded": False, "attempts": 2,
            "rejected_numbers": result["bad_numbers"], "last_ai_reply": raw[:300], "tokens": tokens}


def main() -> None:
    parser = argparse.ArgumentParser(description="AI commentary for key moments, with a grounding check.")
    parser.add_argument("--match", default="data/match_007.jsonl")
    parser.add_argument("--mode", choices=MODES, default="fan")
    parser.add_argument("--lang", choices=LANGUAGES, default="en")
    parser.add_argument("--top", type=int, default=6, help="How many key moments to explain.")
    parser.add_argument("--dry-run", action="store_true", help="Print the first prompt only. No AI call.")
    args = parser.parse_args()

    match_file = Path(args.match)
    full = interpret(match_file)
    important = sorted(full["key_moments"], key=lambda m: (-m["importance"], m["minute"]))[: args.top]
    important.sort(key=lambda m: (m["minute"], m["second"]))
    task = (f"Write commentary for this moment in {LANGUAGES[args.lang]} for {MODES[args.mode]} "
            "Say why it matters for the match.")

    if args.dry_run:
        print(SYSTEM_PROMPT)
        print(task)
        print("FACTS:", json.dumps(moment_facts(match_file, important[0]), indent=2, ensure_ascii=False, default=str))
        return

    client, deployment = make_client()
    print(f"Using model deployment: {deployment}  |  mode: {args.mode}  |  language: {args.lang}\n")
    story, total_tokens = [], 0
    for moment in important:
        facts = moment_facts(match_file, moment)
        answer = grounded_answer(client, deployment, task, facts, fallback=moment["headline"])
        total_tokens += answer["tokens"]
        story.append({"minute": moment["minute"], "second": moment["second"], "type": moment["type"],
                      "team": moment["team"], "player": moment["player"], **answer})
        mark = "OK " if answer["grounded"] else "FALLBACK"
        print(f"{moment['minute']:>2}' [{mark}] {answer['headline']}\n     {answer['commentary']}")
        if not answer["grounded"]:
            print(f"     (why: numbers {answer['rejected_numbers']} | AI said: {answer['last_ai_reply']!r})")
        print()

    recap_task = (f"Write a 3-4 sentence match recap in {LANGUAGES[args.lang]} for {MODES[args.mode]} "
                  "Explain how the match was won: control, pressure and turning points.")
    final = f"Full time: {full['match']['score_home']}-{full['match']['score_away']}"
    recap = grounded_answer(client, deployment, recap_task, recap_facts(full), fallback=final)
    total_tokens += recap["tokens"]
    print(f"RECAP [{'OK' if recap['grounded'] else 'FALLBACK'}] {recap['headline']}\n  {recap['commentary']}\n")

    out_file = match_file.with_name(f"{match_file.stem}_story_{args.mode}_{args.lang}.json")
    out_file.write_text(json.dumps({"mode": args.mode, "language": args.lang, "moments": story, "recap": recap},
                                   indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {out_file}  (tokens used: {total_tokens})")


if __name__ == "__main__":
    main()
