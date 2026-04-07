"""
openenv/environment.py
──────────────────────
CrimeTriageOpenEnv — a real-world crime-incident triage environment.

Implements the full OpenEnv spec:
  • reset()  → Observation
  • step()   → (Observation, float ∈ [0,1], bool, dict)
  • state()  → dict  (episode statistics + active observation)
  • set_dataset() → inject custom training data

Three rotating tasks (easy → medium → hard) are evaluated using
named TaskGrader objects from `graders.py`.  Every step reward is
normalized to [0.0, 1.0] before being returned.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .graders import EasyGrader, HardGrader, MediumGrader, TaskGrader
from .models import Action, Observation, Reward


@dataclass
class TaskSpec:
    name: str
    difficulty: str
    grader: TaskGrader


class CrimeOpenEnv:
    """
    Real-world crime-incident triage environment.

    The agent observes incoming crime report(s) for a region and must make
    three simultaneous decisions:
      1. Classify the crime type
      2. Assign a risk zone (Low / Medium / High)
      3. Decide whether to escalate to senior officers

    Tasks rotate in sequence: Easy → Medium → Hard → Easy → …
    All returned rewards are in [0.0, 1.0].
    """

    def __init__(
        self,
        max_steps: int = 30,
        dataset: Optional[List[Dict]] = None,
    ) -> None:
        self.max_steps = max_steps

        # ── Named task graders ────────────────────────────────────────
        self.tasks: List[TaskSpec] = [
            TaskSpec(
                name="Task 1 – Crime Classification",
                difficulty="easy",
                grader=EasyGrader(),
            ),
            TaskSpec(
                name="Task 2 – Zone Risk Assignment",
                difficulty="medium",
                grader=MediumGrader(),
            ),
            TaskSpec(
                name="Task 3 – Full Triage Decision",
                difficulty="hard",
                grader=HardGrader(),
            ),
        ]

        self._provided_dataset: Optional[List[Dict]] = dataset
        self.dataset: List[Dict] = dataset if dataset is not None else self._seed_data()

        self.current_index: int = 0
        self.steps: int = 0
        self._loop_window: List[Tuple[str, str, bool, bool]] = []
        self._episode_rewards: List[float] = []

    # ── Default seed data ─────────────────────────────────────────────

    @staticmethod
    def _seed_data() -> List[Dict]:
        return [
            {
                "region": "Mumbai",
                "crime_type": "Theft",
                "zone": "Medium",
                "time_of_day": "AM",
                "needs_escalation": False,
            },
            {
                "region": "Pune",
                "crime_type": "Theft",
                "zone": "Medium",
                "time_of_day": "PM",
                "needs_escalation": False,
            },
            {
                "region": "Nagpur",
                "crime_type": "Robbery",
                "zone": "High",
                "time_of_day": "Night",
                "needs_escalation": True,
            },
            {
                "region": "Bangalore",
                "crime_type": "Cybercrime",
                "zone": "Medium",
                "time_of_day": "AM",
                "needs_escalation": False,
            },
            {
                "region": "Mysore",
                "crime_type": "Fraud",
                "zone": "Low",
                "time_of_day": "AM",
                "needs_escalation": False,
            },
            {
                "region": "Delhi",
                "crime_type": "Assault",
                "zone": "High",
                "time_of_day": "PM",
                "needs_escalation": True,
            },
            {
                "region": "Hyderabad",
                "crime_type": "Cybercrime",
                "zone": "Medium",
                "time_of_day": "AM",
                "needs_escalation": False,
            },
            {
                "region": "Chennai",
                "crime_type": "Robbery",
                "zone": "High",
                "time_of_day": "PM",
                "needs_escalation": True,
            },
            {
                "region": "Kolkata",
                "crime_type": "Theft",
                "zone": "Medium",
                "time_of_day": "Night",
                "needs_escalation": False,
            },
            {
                "region": "Ahmedabad",
                "crime_type": "Fraud",
                "zone": "Low",
                "time_of_day": "PM",
                "needs_escalation": False,
            },
        ]

    # ── Internal helpers ──────────────────────────────────────────────

    def _build_observation(self) -> Observation:
        sample = self.dataset[self.current_index]
        crime_stats: Dict[str, int] = {}
        for row in self.dataset:
            ct = row.get("crime_type", "Theft")
            crime_stats[ct] = crime_stats.get(ct, 0) + 1
        return Observation(
            current_reports=[sample],
            selected_region=sample.get("region", "Unknown"),
            crime_stats=crime_stats,
            time_of_day=sample.get("time_of_day", "AM"),
        )

    # ── Public API ────────────────────────────────────────────────────

    def reset(self) -> Observation:
        """Reset the environment to the first sample and clear all episode stats."""
        self.dataset = (
            self._provided_dataset
            if self._provided_dataset is not None
            else self._seed_data()
        )
        self.current_index = 0
        self.steps = 0
        self._loop_window.clear()
        self._episode_rewards.clear()
        return self._build_observation()

    def set_dataset(self, dataset: List[Dict]) -> None:
        """Inject a custom dataset and reset the episode."""
        self._provided_dataset = dataset
        self.dataset = dataset
        self.current_index = 0
        self.steps = 0
        self._loop_window.clear()
        self._episode_rewards.clear()

    def step(self, action_dict: Dict):
        """
        Apply one action and return (observation, reward, done, info).

        reward: float ∈ [0.0, 1.0]  (normalized, always)
        done  : True when all samples processed OR max_steps reached
        info  : task name, difficulty, reward breakdown, step index
        """
        self.steps += 1

        # ── Validate action ───────────────────────────────────────────
        try:
            action = Action(**action_dict)
        except Exception as exc:
            observation = (
                self._build_observation()
                if self.current_index < len(self.dataset)
                else Observation(
                    current_reports=[],
                    selected_region="N/A",
                    crime_stats={},
                    time_of_day="AM",
                )
            )
            return observation, 0.0, False, {"error": f"invalid action: {exc}"}

        sample = self.dataset[self.current_index]
        task = self.tasks[self.current_index % len(self.tasks)]

        # ── Grade the action ──────────────────────────────────────────
        reward_obj: Reward = task.grader.grade(action, sample)
        normalized_reward = reward_obj.normalized  # guaranteed ∈ [0.0, 1.0]

        # ── Anti-repetition signal (subtract 0.1 if looping) ─────────
        signature = (
            action.classify_crime,
            action.assign_zone,
            action.escalate_case,
            action.ignore_case,
        )
        self._loop_window.append(signature)
        if len(self._loop_window) > 4:
            self._loop_window.pop(0)
        if len(self._loop_window) == 4 and len(set(self._loop_window)) == 1:
            normalized_reward = max(0.0, normalized_reward - 0.10)

        self._episode_rewards.append(normalized_reward)

        # ── Advance index ─────────────────────────────────────────────
        self.current_index += 1
        done = (
            self.current_index >= len(self.dataset)
            or self.steps >= self.max_steps
        )

        if done:
            next_obs = Observation(
                current_reports=[],
                selected_region="N/A",
                crime_stats={},
                time_of_day="AM",
            )
        else:
            next_obs = self._build_observation()

        info = {
            "task": task.name,
            "difficulty": task.difficulty,
            "reward_breakdown": reward_obj.model_dump(),
            "normalized_reward": normalized_reward,
            "step": self.steps,
        }
        return next_obs, normalized_reward, done, info

    def state(self) -> Dict:
        """
        Return current episode statistics.

        Keys:
          current_index    : int   — samples processed so far
          steps            : int   — total step() calls
          remaining        : int   — samples left in dataset
          episode_rewards  : list  — per-step normalized rewards ∈ [0,1]
          mean_reward      : float — rolling mean of episode_rewards
          active_observation: dict | None
        """
        rewards = self._episode_rewards
        return {
            "current_index": self.current_index,
            "steps": self.steps,
            "remaining": max(len(self.dataset) - self.current_index, 0),
            "episode_rewards": list(rewards),
            "mean_reward": float(sum(rewards) / len(rewards)) if rewards else 0.0,
            "active_observation": (
                self._build_observation().model_dump()
                if self.current_index < len(self.dataset)
                else None
            ),
        }
