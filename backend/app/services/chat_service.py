"""Crime intelligence Q&A: citizen guidance + police intelligence.

When OPENAI_API_KEY is configured, responses come from OpenAI but remain grounded
to DB statistics provided in the prompt.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from ..core.config import OPENAI_API_KEY, OPENAI_MODEL
from ..db import Report


def _aggregate(db: Session, state: str | None) -> Dict[str, Any]:
    q = db.query(Report)
    if state:
        q = q.filter(Report.state == state)
    rows = q.all()
    by_crime = Counter(r.crime_type for r in rows)
    by_region = Counter(r.region for r in rows)
    return {
        "total_reports": len(rows),
        "top_crimes": by_crime.most_common(5),
        "top_regions": by_region.most_common(5),
    }


def _system_prompt(role: str) -> str:
    if role == "police" or role == "admin":
        return (
            "You are a crime intelligence assistant for Indian law enforcement. "
            "Answer using ONLY the provided statistics JSON as factual grounding. "
            "If data is insufficient, say what is missing. Keep answers concise."
        )
    # citizen default
    return (
        "You are a supportive safety and reporting assistant for citizens in India. "
        "Your goals: (1) guide the user calmly with practical next steps, (2) motivate them to report using the app, "
        "(3) help them phrase a clear incident description and choose fields, (4) use ONLY the provided statistics JSON "
        "for any claims about safest/high-risk regions. "
        "If the user may be in immediate danger, tell them to contact emergency services (100) first. "
        "Do not provide instructions for wrongdoing. Keep answers friendly, clear, and action-oriented."
    )


async def answer_query(
    db: Session,
    question: str,
    state_hint: str | None,
    *,
    role: str = "citizen",
    username: Optional[str] = None,
) -> Dict[str, Any]:
    stats_global = _aggregate(db, None)
    stats_state = _aggregate(db, state_hint) if state_hint else stats_global

    if OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            system = _system_prompt(role)
            user_content = {
                "question": question,
                "user": {"role": role, "username": username, "state_hint": state_hint},
                "stats_all_india": stats_global,
                "stats_filtered_state": stats_state,
                "state_hint": state_hint,
            }
            resp = await client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": str(user_content)},
                ],
                temperature=0.2,
            )
            text = (resp.choices[0].message.content or "").strip()
            return {"answer": text, "source": "openai", "stats_used": stats_state}
        except Exception:
            # Do not leak raw provider errors to end users (quota, rate limit, etc).
            # We silently fall back to local guidance/statistics mode.
            pass

    # Deterministic heuristic answers
    qlow = (question or "").lower()
    if "safest" in qlow or "safe" in qlow:
        regions = list(stats_state.get("top_regions") or [])
        if not regions:
            return {"answer": "No regional data yet for this scope.", "source": "db", "stats_used": stats_state}
        safest = min(regions, key=lambda x: x[1])
        return {
            "answer": f"Among recorded reports in scope, '{safest[0]}' has the fewest incidents ({safest[1]}). Lower counts may indicate safer activity only for this dataset window.",
            "source": "db",
            "stats_used": stats_state,
        }
    if "high risk" in qlow or "danger" in qlow:
        hot = stats_state.get("top_regions", [])[:3]
        if not hot:
            return {"answer": "No incidents recorded for this filter.", "source": "db", "stats_used": stats_state}
        parts = ", ".join(f"{name} ({cnt})" for name, cnt in hot)
        return {"answer": f"Regions with the most recorded reports: {parts}.", "source": "db", "stats_used": stats_state}

    tc = stats_state.get("top_crimes", [])
    summary = ", ".join(f"{n} ({c})" for n, c in tc[:5])
    if role not in ("police", "admin"):
        name = f" {username}" if username else ""
        if not question.strip():
            return {
                "answer": (
                    f"Hi{name}. I can guide you to file a strong report. Share what happened, where (state/region), and when, "
                    "then add any photo/video evidence and phone number for follow-up."
                ),
                "source": "db",
                "stats_used": stats_state,
            }

        if any(k in qlow for k in ("how to report", "report", "complaint", "file case", "submit")):
            return {
                "answer": (
                    "To report quickly: (1) choose state and region, (2) select crime type and actor type, "
                    "(3) write 2-3 clear lines: what happened, where, when, (4) upload photo/video evidence if available, "
                    "(5) submit proof and keep the report ID for tracking."
                ),
                "source": "db",
                "stats_used": stats_state,
            }

        if any(k in qlow for k in ("evidence", "photo", "video", "proof")):
            return {
                "answer": (
                    "Best evidence tips: capture clear face/vehicle details, exact location markers, and timestamps if possible. "
                    "Do not edit the media. Upload original photo/video and add a short factual description."
                ),
                "source": "db",
                "stats_used": stats_state,
            }

        if any(k in qlow for k in ("emergency", "urgent", "danger", "help now", "panic")):
            return {
                "answer": (
                    "If you are in immediate danger, call 100 right now. Then use the PANIC button in the app to send location "
                    "and optional snapshot. After you are safe, submit full report details for faster action."
                ),
                "source": "db",
                "stats_used": stats_state,
            }

        if any(k in qlow for k in ("what to write", "description", "write report")):
            return {
                "answer": (
                    "Use this format: 'At [time], at [exact place], [what happened], suspect details: [appearance/vehicle], "
                    "direction of movement: [if known]. Witnesses: [yes/no].' Keep it factual and concise."
                ),
                "source": "db",
                "stats_used": stats_state,
            }

        stats_line = (
            f"Based on current records in scope, common categories are: {summary}. "
            if summary
            else "I do not have enough local report data yet to summarize crime categories. "
        )
        return {
            "answer": (
                f"I can help{name}. Tell me: what happened, where (state/region), and when. "
                f"{stats_line}"
                f"If you’re in immediate danger, call 100 first. Otherwise, you can submit a report in the Proof Box and upload any evidence."
            ),
            "source": "db",
            "stats_used": stats_state,
        }
    return {
        "answer": f"Recorded crime mix (filtered): {summary}. Total reports: {stats_state.get('total_reports', 0)}.",
        "source": "db",
        "stats_used": stats_state,
    }
