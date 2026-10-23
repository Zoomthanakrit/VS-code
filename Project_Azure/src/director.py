"""The Director agent: decides WHEN each card goes on screen, like a TV director.

It follows 3 simple rules:
  1. Goals go on screen right away.
  2. Other cards wait for a calm moment (a foul, a card, a kick-off, a stopped shot,
     or the ball back in the middle third), at most 45 seconds.
  3. Only one pop-up every 30 seconds. If two cards clash, the more important one wins;
     the other still goes into the "Story so far" list, but doesn't pop up.

It also writes the "agent log": a simple diary of what each agent did, so viewers
(and judges) can see the AI team at work.

Example:
    card: big chance at 27:33 (importance 3)
    next events: 27:35 shot saved -> 27:41 possession change after the shot
    Director: "Waited 8 s for a calm moment (the shot was stopped)" -> show at 27:41
"""

from __future__ import annotations

MAX_WAIT_S = 45
GAP_S = 30

KIND_NAMES = {"goal": "goal", "big_chance_missed": "big chance", "great_save": "great save",
              "yellow_card": "yellow card", "pressing_spell": "pressing spell",
              "momentum_swing": "momentum shift", "fastest_shot": "fastest shot"}


def calm_reason(event: dict) -> str | None:
    """Is this event a calm moment to show a graphic? Returns why, or None."""
    kind = event["type"]
    if kind == "foul":
        return "a foul stopped play"
    if kind == "card":
        return "the referee showed a card"
    if kind == "kickoff":
        return "a kick-off"
    if kind == "half_end":
        return "half-time"
    if kind == "possession_change" and str(event.get("reason", "")).startswith("shot_"):
        return "the shot was stopped"
    if kind == "pass" and event.get("x") is not None and 35 <= event["x"] <= 70:
        return "the ball went back to the middle third"
    return None


def plan(overlays: list[dict], events: list[dict]) -> list[dict]:
    """Add show_t (when to pop up), popup (True/False) and director_note to each card."""
    timed = sorted(events, key=lambda e: e["t"])
    for o in overlays:
        if o["kind"] == "goal":
            o["show_t"], o["director_note"] = o["t"], "Goal: show it now"
            continue
        o["show_t"], o["director_note"] = o["t"] + MAX_WAIT_S, f"No calm moment, showed it after {MAX_WAIT_S} s"
        for e in timed:
            if e["t"] < o["t"]:
                continue
            if e["t"] > o["t"] + MAX_WAIT_S:
                break
            reason = calm_reason(e)
            if reason:
                waited = e["t"] - o["t"]
                o["show_t"] = e["t"]
                o["director_note"] = (f"Waited {waited} s for a calm moment ({reason})" if waited
                                      else f"Calm moment, show it now ({reason})")
                break

    last = None
    for o in sorted(overlays, key=lambda o: (o["show_t"], -o["importance"])):
        o["popup"] = True
        if last and o["show_t"] - last["show_t"] < GAP_S:
            if o["importance"] <= last["importance"]:
                o["popup"] = False
                o["director_note"] = (f"Skipped the pop-up: the {KIND_NAMES.get(last['kind'], last['kind'])} card "
                                      "is still on screen (kept in the story list)")
                continue
            o["director_note"] += f" (replaces the less important {KIND_NAMES.get(last['kind'], last['kind'])} card)"
        last = o
    return overlays


def agent_log(overlays: list[dict], profile: dict) -> list[dict]:
    """A diary of what each agent did for each card. Each line has a match time t."""
    lang = {"en": "English", "th": "Thai"}.get(profile.get("language"), profile.get("language"))
    log = []
    for o in overlays:
        kind = KIND_NAMES.get(o["kind"], o["kind"])
        who = o["player"] or o["team"] or ""
        why = " (picked for you)" if o.get("for_you") else ""
        log.append({"t": o["t"], "agent": "stats", "text": f"Found a {kind}: {who}. Importance {o['importance']}/5{why}"})
        if o.get("offline"):
            write = "AI not connected, using the plain fact headline"
        elif o.get("cached"):
            write = f"Wrote the {lang} {profile.get('mode')} card (reused from cache, instant)"
        else:
            write = f"Wrote the {lang} {profile.get('mode')} card in {o.get('ai_seconds')} s"
        log.append({"t": o["t"], "agent": "commentator", "text": write})
        if o["grounded"]:
            n = o["numbers_checked"]
            check = (f"Checked {n} number{'s' if n != 1 else ''} against the stats: all correct"
                     if o["numbers_checked"] else "No numbers to check: approved")
        else:
            check = "Blocked an invented number, showing the plain headline instead"
        log.append({"t": o["t"], "agent": "factchecker", "text": check, "ok": o["grounded"]})
        log.append({"t": o["show_t"], "agent": "director", "text": o["director_note"], "popup": o["popup"]})
    return sorted(log, key=lambda x: x["t"])
