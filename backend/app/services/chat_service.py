"""Crime intelligence Q&A: OpenAI when configured, else DB-grounded answers."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

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


async def answer_query(db: Session, question: str, state_hint: str | None) -> Dict[str, Any]:
    stats_global = _aggregate(db, None)
    stats_state = _aggregate(db, state_hint) if state_hint else stats_global

    if OPENAI_API_KEY:
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            system = (
                "You are a crime intelligence assistant for Indian law enforcement. "
                "Answer using ONLY the provided statistics JSON as factual grounding. "
                "If data is insufficient, say what is missing. Keep answers concise."
            )
            user_content = {
                "question": question,
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
        except Exception as exc:
            return {
                "answer": f"OpenAI error ({exc!r}). Falling back to local statistics.",
                "source": "fallback_error",
                "stats_used": stats_state,
            }

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
    summary = ", ".join(f"{n} ({c})" for n, c in tc[:5]) or "n/a"
    return {
        "answer": f"Recorded crime mix (filtered): {summary}. Total reports: {stats_state.get('total_reports', 0)}.",
        "source": "db",
        "stats_used": stats_state,
    }
