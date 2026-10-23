"""Grounding check: every number the AI writes must come from our stats.

Example:
    facts = {"xg": 0.47, "distance_m": 6.4}
    check("A 47% chance from 6.4 m, wasted!", facts)   -> ok (47% matches 0.47, 6.4 matches 6.4)
    check("A 60% chance from 6.4 m, wasted!", facts)   -> NOT ok, bad numbers: ["60%"]

Rules:
  - A number matches if it equals a fact at the precision written (6 matches 6.4; 104 matches 104.2).
  - Percentages also match facts written as 0-1 values (47% matches 0.47).
  - Small numbers 0-3 are always allowed ("two goals", "1st half", "3 points").
"""

from __future__ import annotations

import re
from typing import Any

# Finds numbers like 6, 6.4, 104.2, 47%, 1,234 (Arabic digits, also inside Thai text).
NUMBER = re.compile(r"(?<![\d.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(\s?%)?")
ALWAYS_OK = {0, 1, 2, 3}


def collect_numbers(data: Any, found: set[float] | None = None) -> set[float]:
    """Collect every number inside a dict/list/string (the 'allowed' numbers)."""
    found = set() if found is None else found
    if isinstance(data, bool):
        return found
    if isinstance(data, (int, float)):
        found.add(abs(float(data)))
        if 0 < abs(data) <= 1:
            found.add(round(abs(data) * 100, 4))  # 0.47 also allows 47 (%)
    elif isinstance(data, str):
        for match in NUMBER.finditer(data):
            found.add(float(match.group(1).replace(",", "") + ("." + match.group(2) if match.group(2) else "")))
    elif isinstance(data, dict):
        for value in data.values():
            collect_numbers(value, found)
    elif isinstance(data, (list, tuple)):
        for value in data:
            collect_numbers(value, found)
    return found


def check(text: str, facts: Any) -> dict:
    """Return {"ok": True/False, "bad_numbers": [...], "checked": how many numbers were checked}."""
    allowed = collect_numbers(facts)
    bad, checked = [], 0
    for match in NUMBER.finditer(text):
        whole, decimals = match.group(1).replace(",", ""), match.group(2)
        value = float(whole + ("." + decimals if decimals else ""))
        if value in ALWAYS_OK:
            continue
        checked += 1
        places = len(decimals) if decimals else 0
        tolerance = 0.5 * 10 ** -places + 1e-9  # "6" may stand for 6.4, "6.4" must be 6.35-6.45
        if not any(abs(a - value) <= tolerance for a in allowed):
            bad.append(match.group(0).strip())
    return {"ok": not bad, "bad_numbers": bad, "checked": checked}


if __name__ == "__main__":
    facts = {"xg": 0.47, "distance_m": 6.4, "shot_speed_kmh": 104.2}
    for sentence in ["A 47% chance from 6.4 m at 104 km/h, wasted!",
                     "A 60% chance from 6 m, wasted!",
                     "โอกาส 47% จากระยะ 6.4 เมตร"]:
        print(f"{sentence!r:55} -> {check(sentence, facts)}")
