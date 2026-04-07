from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Dict, List, Literal


TimeOfDay = Literal["AM", "PM", "Night"]


class CrimeReport(BaseModel):
    region: str
    crime_type: str
    zone: str
    time_of_day: TimeOfDay
    needs_escalation: bool = False


class Observation(BaseModel):
    current_reports: List[CrimeReport] = Field(default_factory=list)
    selected_region: str
    crime_stats: Dict[str, int] = Field(default_factory=dict)
    time_of_day: TimeOfDay


class Action(BaseModel):
    classify_crime: Literal["Theft", "Robbery", "Assault", "Cybercrime", "Fraud"]
    assign_zone: Literal["Low", "Medium", "High"]
    escalate_case: bool
    ignore_case: bool


class Reward(BaseModel):
    """
    Reward components for one environment step.

    All components are bounded so that `normalized` ∈ [0.0, 1.0]:
      • accuracy_score : correctness signal      ∈ [0.0, 1.0]
      • progress_score : partial-progress bonus  ∈ [0.0, 1.0]
      • penalty        : negative signal         ∈ [-1.0, 0.0]

    `normalized` = clamp(accuracy + progress + penalty, 0.0, 1.0)
    """

    accuracy_score: float = Field(default=0.0, ge=0.0, le=1.0)
    progress_score: float = Field(default=0.0, ge=0.0, le=1.0)
    penalty: float = Field(default=0.0, ge=-1.0, le=0.0)

    @property
    def normalized(self) -> float:
        """Final scalar reward always in [0.0, 1.0]. Used by step()."""
        raw = self.accuracy_score + self.progress_score + self.penalty
        return float(max(0.0, min(1.0, raw)))
