"""Pre-make the AI cards for the most common viewer settings.

Run this once before recording the demo or deploying. Afterwards these
settings load instantly and cost nothing, on your laptop and on Azure.

Run:
    python src/warm_cache.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from explain import make_client  # noqa: E402
from personalize import Profile, build_overlay  # noqa: E402

MATCH = Path("data/match_007.jsonl")

PROFILES = [
    Profile(mode="fan", language="en"),
    Profile(mode="fan", language="th"),
    Profile(mode="analyst", language="en"),
    Profile(mode="analyst", language="th"),
    Profile(mode="fan", language="th", favorite_team="Chao Phraya Rovers"),
    Profile(mode="fan", language="en", favorite_player="Ali Demir"),
    Profile(mode="analyst", language="en", favorite_player="Ali Demir", focus="shooting"),
]

if __name__ == "__main__":
    # Windows consoles (e.g. Thai cp874) can't print every character the AI writes in Thai
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    client, deployment = make_client()
    for i, profile in enumerate(PROFILES, 1):
        print(f"\n=== {i}/{len(PROFILES)}: {profile.slug()} ===")
        build_overlay(MATCH, profile, extra=6, up_to_minute=999, client=client, deployment=deployment)
    print("\nDone. Cards are saved in data/cache/")
