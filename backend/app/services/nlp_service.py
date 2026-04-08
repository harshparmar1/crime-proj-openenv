"""Structured extraction from free-form voice / text (keyword + dictionary)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from ..core.state_regions import STATE_REGIONS

CRIME_SYNONYMS = {
    "theft": "Theft",
    "steal": "Theft",
    "stolen": "Theft",
    "robbery": "Robbery",
    "rob": "Robbery",
    "assault": "Assault",
    "attack": "Assault",
    "fight": "Assault",
    "cyber": "Cybercrime",
    "cybercrime": "Cybercrime",
    "phishing": "Cybercrime",
    "fraud": "Fraud",
    "scam": "Fraud",
}


def extract_from_text(text: str, default_state: Optional[str] = None) -> Dict[str, Any]:
    t = (text or "").lower()
    out: Dict[str, Any] = {
        "crime_type": None,
        "region": None,
        "state": default_state,
        "actor_type": None,
        "weapon": None,
        "vehicle": None,
        "raw": text or "",
    }

    for key, label in CRIME_SYNONYMS.items():
        if re.search(rf"\b{re.escape(key)}\b", t):
            out["crime_type"] = label
            break

    if "group" in t or "gang" in t or "multiple people" in t:
        out["actor_type"] = "Group"
    elif "individual" in t or "alone" in t or "one person" in t:
        out["actor_type"] = "Individual"

    if "weapon" in t or "knife" in t or "gun" in t or "pistol" in t:
        out["weapon"] = "Yes"
    if any(v in t for v in ("car", "bike", "truck", "vehicle", "suv", "motorcycle", "scooter")):
        out["vehicle"] = "Yes"

    # Longest region name match wins (avoid short substring false positives)
    best: Optional[tuple[int, str, str]] = None
    for state, regions in STATE_REGIONS.items():
        for region in regions:
            if region.lower() in t:
                score = len(region)
                if best is None or score > best[0]:
                    best = (score, state, region)
    if best:
        _, st, reg = best
        out["state"] = st
        out["region"] = reg

    # State-only mentions (coarse)
    if out["region"] is None:
        for state in sorted(STATE_REGIONS.keys(), key=len, reverse=True):
            if state.lower() in t:
                out["state"] = state
                out["region"] = STATE_REGIONS[state][0]
                break

    return out


def time_of_day_hint(text: str) -> str:
    t = (text or "").lower()
    if any(x in t for x in ("night", "midnight", "late night")):
        return "Night"
    if any(x in t for x in ("morning", "am")):
        return "AM"
    if any(x in t for x in ("evening", "afternoon", "pm")):
        return "PM"
    return "AM"
