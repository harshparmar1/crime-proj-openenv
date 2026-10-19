"""
openenv/graders.py
──────────────────
Named TaskGrader classes for the CrimeTriageOpenEnv.
All scores are normalized to [0.0, 1.0] and include partial-progress signals.

Grader hierarchy
────────────────
  TaskGrader (abstract)
    ├── EasyGrader   – Task 1: Crime Classification
    ├── MediumGrader – Task 2: Zone Risk Assignment
    └── HardGrader   – Task 3: Full Triage Decision
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict

from .models import Action, Reward

# Zone order for proximity scoring
ZONE_ORDER: Dict[str, int] = {"Low": 0, "Medium": 1, "High": 2}

# Crime category groups for partial-credit matching
PROPERTY_CRIMES = {"Theft", "Robbery", "Fraud"}
VIOLENT_CRIMES  = {"Robbery", "Assault"}
CYBER_CRIMES    = {"Cybercrime", "Fraud"}


class TaskGrader(ABC):
    """Abstract base for all task graders. Every subclass must produce a
    Reward whose components (accuracy_score, progress_score, penalty) are
    already bounded so that `reward.normalized` ∈ [0.0, 1.0]."""

    difficulty: str = "base"

    @abstractmethod
    def grade(self, action: Action, sample: Dict) -> Reward:
        """Grade one agent action against the ground-truth sample dict."""
        ...

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp(value: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, value))


# ══════════════════════════════════════════════════════════════════════
# Task 1 — Crime Classification (Easy)
# ══════════════════════════════════════════════════════════════════════

class EasyGrader(TaskGrader):
    """
    Task 1 — Crime Classification  (difficulty: easy)
    ──────────────────────────────────────────────────
    Goal: Identify the correct crime type from the observation stats.

    Scoring rubric (all values ∈ [0.0, 1.0] before combining):
      • Exact match         → accuracy=1.0, progress=0.0
      • Same category match → accuracy=0.4, progress=0.0  (partial credit)
      • Wrong category      → accuracy=0.0, penalty=-0.2
      • ignore_case=True    → additional penalty=-0.3

    Max achievable normalized reward = 1.0
    """

    difficulty = "easy"

    def grade(self, action: Action, sample: Dict) -> Reward:
        accuracy = 0.0
        progress = 0.0
        penalty  = 0.0

        if action.ignore_case:
            penalty -= 0.3

        true_crime = sample.get("crime_type", "Theft")
        pred_crime = action.classify_crime

        if pred_crime == true_crime:
            accuracy = 1.0
            progress = 0.0  # no progress bonus needed — already perfect
        else:
            # Partial credit: same broad category
            def _category(c: str) -> str:
                if c in PROPERTY_CRIMES: return "property"
                if c in VIOLENT_CRIMES:  return "violent"
                if c in CYBER_CRIMES:    return "cyber"
                return "other"

            if _category(pred_crime) == _category(true_crime):
                accuracy = 0.4  # right ballpark
            else:
                penalty -= 0.2  # wrong category

        return Reward(
            accuracy_score=self._clamp(accuracy, 0.0, 1.0),
            progress_score=self._clamp(progress, 0.0, 0.0),
            penalty=self._clamp(penalty, -1.0, 0.0),
        )


# ══════════════════════════════════════════════════════════════════════
# Task 2 — Zone Risk Assignment (Medium)
# ══════════════════════════════════════════════════════════════════════

class MediumGrader(TaskGrader):
    """
    Task 2 — Zone Risk Assignment  (difficulty: medium)
    ────────────────────────────────────────────────────
    Goal: Assign the correct risk zone (Low / Medium / High).

    Scoring rubric:
      • Exact zone match       → accuracy=0.6, progress=0.4
      • Adjacent zone (±1)     → accuracy=0.3, progress=0.2  (partial credit)
      • Completely wrong (±2)  → accuracy=0.0, penalty=-0.3
      • ignore_case=True       → penalty=-0.3

    Max achievable normalized reward = 1.0
    """

    difficulty = "medium"

    def grade(self, action: Action, sample: Dict) -> Reward:
        accuracy = 0.0
        progress = 0.0
        penalty  = 0.0

        if action.ignore_case:
            penalty -= 0.3

        true_zone = sample.get("zone", "Low")
        pred_zone = action.assign_zone

        true_idx = ZONE_ORDER.get(true_zone, 0)
        pred_idx = ZONE_ORDER.get(pred_zone, 0)
        diff = abs(true_idx - pred_idx)

        if diff == 0:               # exact
            accuracy = 0.6
            progress = 0.4
        elif diff == 1:             # adjacent — partial
            accuracy = 0.3
            progress = 0.2
        else:                       # completely wrong
            penalty -= 0.3

        return Reward(
            accuracy_score=self._clamp(accuracy, 0.0, 0.6),
            progress_score=self._clamp(progress, 0.0, 0.4),
            penalty=self._clamp(penalty, -1.0, 0.0),
        )


# ══════════════════════════════════════════════════════════════════════
# Task 3 — Full Triage Decision (Hard)
# ══════════════════════════════════════════════════════════════════════

class HardGrader(TaskGrader):
    """
    Task 3 — Full Triage Decision  (difficulty: hard)
    ──────────────────────────────────────────────────
    Goal: Simultaneously classify crime + assign zone + decide escalation.

    Scoring rubric (max accuracy=0.70, max progress=0.30):
      • Crime exact match       → +0.35 accuracy
      • Crime category match    → +0.15 accuracy  (partial)
      • Crime wrong category    → penalty -0.10
      • Zone exact match        → +0.35 accuracy
      • Zone adjacent (±1)      → +0.15 accuracy  (partial)
      • Zone fully wrong (±2)   → penalty -0.10
      • Escalation correct      → +0.30 progress
      • Escalation wrong        → penalty -0.10
      • ignore_case=True        → penalty -0.40 (dominant; skips rest)

    Max achievable normalized reward = 1.0
    """

    difficulty = "hard"

    def grade(self, action: Action, sample: Dict) -> Reward:
        if action.ignore_case:
            return Reward(
                accuracy_score=0.0,
                progress_score=0.0,
                penalty=-0.40,
            )

        accuracy = 0.0
        progress = 0.0
        penalty  = 0.0

        # ── Crime classification (35% of total) ────────────────────────
        true_crime = sample.get("crime_type", "Theft")
        pred_crime = action.classify_crime

        def _category(c: str) -> str:
            if c in PROPERTY_CRIMES: return "property"
            if c in VIOLENT_CRIMES:  return "violent"
            if c in CYBER_CRIMES:    return "cyber"
            return "other"

        if pred_crime == true_crime:
            accuracy += 0.35
        elif _category(pred_crime) == _category(true_crime):
            accuracy += 0.15
        else:
            penalty -= 0.10

        # ── Zone assignment (35% of total) ────────────────────────────
        true_zone = sample.get("zone", "Low")
        pred_zone = action.assign_zone
        true_idx  = ZONE_ORDER.get(true_zone, 0)
        pred_idx  = ZONE_ORDER.get(pred_zone, 0)
        diff = abs(true_idx - pred_idx)

        if diff == 0:
            accuracy += 0.35
        elif diff == 1:
            accuracy += 0.15
        else:
            penalty -= 0.10

        # ── Escalation decision (30% of total) ────────────────────────
        needs_escalation = sample.get("needs_escalation", False)
        if action.escalate_case == needs_escalation:
            progress += 0.30
        else:
            penalty -= 0.10

        return Reward(
            accuracy_score=self._clamp(accuracy, 0.0, 0.70),
            progress_score=self._clamp(progress, 0.0, 0.30),
            penalty=self._clamp(penalty, -1.0, 0.0),
        )
