from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


CRIME_ALIASES = {
    "theft": "Theft",
    "steal": "Theft",
    "stolen": "Theft",
    "robbery": "Robbery",
    "rob": "Robbery",
    "assault": "Assault",
    "attack": "Assault",
    "cybercrime": "Cybercrime",
    "cyber": "Cybercrime",
    "phishing": "Cybercrime",
    "fraud": "Fraud",
    "scam": "Fraud",
}

ASK_VARIATIONS = {
    "crime_type": [
        "Could you tell me what type of crime occurred (theft, robbery, assault, cybercrime, fraud)?",
        "What kind of incident are you reporting?",
        "Please specify the crime type so I can guide you correctly."
    ],
    "location": [
        "Could you share the exact location (state and region/city)?",
        "Where exactly did this happen?",
        "Please provide the location details (state and area)."
    ],
    "time": [
        "When did this happen?",
        "Can you mention the time of the incident?",
        "What time did this occur?"
    ],
    "people": [
        "Was it done by an individual or a group?",
        "Do you think one person was involved, or multiple people?",
        "Please tell me if this involved an individual or a group."
    ],
}

CONFIRM_VARIATIONS = [
    "I have enough details now. Do you want me to prepare this for report submission?",
    "Thanks — I captured the incident details. Shall I proceed to submit-ready format?",
    "Great, I have the key details. Do you want to submit this report now?"
]

URGENT_VARIATIONS = [
    "⚠️ This seems urgent. If you are in immediate danger, call 100 and use the PANIC button.",
    "⚠️ I detect urgency. Please prioritize safety first: call 100, then submit details here.",
    "⚠️ This sounds serious. Contact emergency services (100) immediately if risk is active."
]


@dataclass
class ConversationState:
    crime_type: Optional[str] = None
    location: Optional[str] = None
    time: Optional[str] = None
    people: Optional[str] = None
    last_prompted_field: Optional[str] = None
    turns: int = 0
    history: list[str] = field(default_factory=list)


class ChatRuntime:
    def __init__(self) -> None:
        self._sessions: dict[str, ConversationState] = {}

    def _session(self, key: str) -> ConversationState:
        if key not in self._sessions:
            self._sessions[key] = ConversationState()
        return self._sessions[key]

    def _extract(self, msg: str, st: ConversationState) -> Dict[str, Any]:
        m = msg.lower()

        # crime type
        if st.crime_type is None:
            for k, v in CRIME_ALIASES.items():
                if re.search(rf"\b{re.escape(k)}\b", m):
                    st.crime_type = v
                    break

        # people
        if st.people is None:
            if any(x in m for x in ("group", "gang", "multiple", "many people", "3 men", "two men")):
                st.people = "Group"
            elif any(x in m for x in ("individual", "single person", "one person", "alone")):
                st.people = "Individual"

        # time (simple)
        if st.time is None:
            if any(x in m for x in ("night", "midnight")):
                st.time = "Night"
            elif any(x in m for x in ("morning", "am")):
                st.time = "Morning"
            elif any(x in m for x in ("evening", "afternoon", "pm")):
                st.time = "Evening"
            else:
                tm = re.search(r"\b(\d{1,2}(:\d{2})?\s?(am|pm)?)\b", m)
                if tm:
                    st.time = tm.group(1).upper().replace(" ", "")

        # location
        if st.location is None:
            # capture phrases like "in Mumbai", "at Andheri", "near station"
            loc = re.search(r"\b(?:in|at|near)\s+([a-z][a-z\s]{1,30})", m)
            if loc:
                st.location = loc.group(1).strip().title()

        urgent = any(x in m for x in ("urgent", "help", "danger", "panic", "attack now", "bleeding", "weapon"))
        return {"urgent": urgent}

    def _next_missing(self, st: ConversationState) -> Optional[str]:
        for k in ("crime_type", "location", "time", "people"):
            if getattr(st, k) is None:
                return k
        return None

    def handle(self, message: str, session_key: str, user_name: str | None = None) -> Dict[str, Any]:
        st = self._session(session_key)
        st.turns += 1
        st.history.append(message)
        extracted = self._extract(message, st)

        if extracted.get("urgent"):
            reply = random.choice(URGENT_VARIATIONS)
        else:
            missing = self._next_missing(st)
            if missing is None:
                summary = (
                    f"Crime: {st.crime_type}, Location: {st.location}, Time: {st.time}, "
                    f"Involved: {st.people}."
                )
                reply = f"{summary} {random.choice(CONFIRM_VARIATIONS)}"
                st.last_prompted_field = None
            else:
                # avoid prompting the same field with same sentence repeatedly
                options = ASK_VARIATIONS[missing]
                if st.last_prompted_field == missing and len(options) > 1:
                    reply = random.choice(options[1:] + options[:1])
                else:
                    reply = random.choice(options)
                st.last_prompted_field = missing

        if user_name and st.turns <= 2 and "I " not in reply:
            reply = f"{user_name}, {reply[0].lower() + reply[1:]}"

        return {
            "reply": reply,
            "context": {
                "crime_type": st.crime_type,
                "location": st.location,
                "time": st.time,
                "people": st.people,
            },
            "missing_fields": [k for k in ("crime_type", "location", "time", "people") if getattr(st, k) is None],
            "urgent": bool(extracted.get("urgent")),
            "ready_to_submit": self._next_missing(st) is None,
        }


chat_runtime = ChatRuntime()

