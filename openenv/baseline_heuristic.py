"""
baseline_heuristic.py
─────────────────────
Deterministic rule-based baseline agent for CrimeTriageOpenEnv.

• Requires NO API key whatsoever.
• Fully reproducible — seed=42 fixed at module level.
• Demonstrates correct usage of reset() / step() / state().
• Prints per-step reward and a final normalized score ∈ [0.0, 1.0].

Heuristic strategy per task
────────────────────────────
  Task 1 (easy)   — predict the most frequent crime type in crime_stats.
  Task 2 (medium) — assign zone based on crime severity + time-of-day bump.
  Task 3 (hard)   — combine crime + zone heuristics; escalate if High zone
                    or if time_of_day is PM / Night.

Run:
    cd openenv
    pip install pydantic>=2.10
    python baseline_heuristic.py
"""

from __future__ import annotations

import random
from typing import Any, Dict

from openenv.environment import CrimeOpenEnv

# ── Fixed seed for reproducibility ───────────────────────────────────────────
random.seed(42)

# Crime → base severity score (used to derive zone)
CRIME_SEVERITY: Dict[str, int] = {
    "Assault":    3,
    "Robbery":    3,
    "Theft":      2,
    "Fraud":      1,
    "Cybercrime": 1,
}

# Property-crime category for EasyGrader partial-credit awareness
PROPERTY_CRIMES = {"Theft", "Robbery", "Fraud"}
VIOLENT_CRIMES  = {"Robbery", "Assault"}
CYBER_CRIMES    = {"Cybercrime", "Fraud"}


# ── Heuristic policy ──────────────────────────────────────────────────────────

def _dominant_crime(crime_stats: Dict[str, int]) -> str:
    """Return the most frequent crime type seen in current stats."""
    if not crime_stats:
        return "Theft"
    return max(crime_stats, key=crime_stats.get)  # type: ignore[arg-type]


def _derive_zone(crime: str, time_of_day: str) -> str:
    """Map crime severity + time-of-day to a risk zone."""
    severity = CRIME_SEVERITY.get(crime, 1)
    if time_of_day == "Night":
        severity += 1   # Night-time bumps severity by 1
    if severity >= 3:
        return "High"
    if severity == 2:
        return "Medium"
    return "Low"


def heuristic_action(observation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure deterministic policy — zero randomness.

    Works across all three task difficulties because:
      • crime classification feeds into zone derivation (transitivity).
      • escalation is derived from zone + time, matching HardGrader's logic.
    """
    crime_stats  = observation.get("crime_stats", {})
    time_of_day  = observation.get("time_of_day", "AM")

    predicted_crime = _dominant_crime(crime_stats)
    zone            = _derive_zone(predicted_crime, time_of_day)
    escalate        = zone == "High" or time_of_day in ("PM", "Night")

    return {
        "classify_crime": predicted_crime,
        "assign_zone":    zone,
        "escalate_case":  escalate,
        "ignore_case":    False,   # never ignore — always penalized
    }


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_heuristic_baseline(verbose: bool = True) -> float:
    """
    Run one full episode with the heuristic agent.

    Returns:
        mean_reward (float): mean normalized reward ∈ [0.0, 1.0]
    """
    env = CrimeOpenEnv()
    observation = env.reset()

    total_reward = 0.0
    step_count   = 0
    done         = False

    if verbose:
        print("=" * 68)
        print("  CrimeTriageOpenEnv — Deterministic Heuristic Baseline (seed=42)")
        print("=" * 68)
        header = f"{'Step':>4}  {'Task':<36}  {'Reward':>7}  {'Done'}"
        print(header)
        print("-" * 68)

    while not done:
        action = heuristic_action(observation.model_dump())
        observation, reward, done, info = env.step(action)
        total_reward += reward
        step_count   += 1

        if verbose:
            task_name = info.get("task", "")
            print(
                f"{step_count:>4}  {task_name:<36}  {reward:>7.4f}  {done}"
            )

    final_state = env.state()
    mean_reward = final_state.get("mean_reward", 0.0)

    if verbose:
        print("=" * 68)
        print(f"  Total Reward     : {total_reward:.4f}")
        print(f"  Mean Reward      : {mean_reward:.4f}  (normalized 0.0 – 1.0)")
        print(f"  Steps Taken      : {step_count}")
        print(f"  Per-step rewards : {[round(r, 3) for r in final_state['episode_rewards']]}")
        print("=" * 68)

    return mean_reward


if __name__ == "__main__":
    score = run_heuristic_baseline(verbose=True)
    print(f"\nReproducible baseline score: {score:.4f}")
