"""
baseline.py
───────────
LLM-powered baseline agent for CrimeTriageOpenEnv (requires OPENAI_API_KEY).

For a zero-key, fully deterministic baseline, use:
    python baseline_heuristic.py

Usage:
    export OPENAI_API_KEY=sk-...
    python baseline.py --mode live   [--episodes N] [--seed 42]
    python baseline.py --mode record [--episodes N] [--seed 42]
    python baseline.py --mode replay [--episodes N] [--seed 42]
"""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from typing import Any, Dict, Literal

from dotenv import load_dotenv
from openai import OpenAI

from openenv.environment import CrimeOpenEnv
from openenv.models import Action

load_dotenv()

DEFAULT_MODEL = "gpt-4o-mini-2024-07-18"
DEFAULT_CACHE = "baseline_action_cache.json"
Mode = Literal["live", "record", "replay"]

SYSTEM_PROMPT = """\
You are a dispatch-policy agent for a real-world crime reporting system.

Given an observation about active crime reports in a region, respond with
strict JSON containing exactly these four keys:

  classify_crime  : one of ["Theft", "Robbery", "Assault", "Cybercrime", "Fraud"]
  assign_zone     : one of ["Low", "Medium", "High"]
  escalate_case   : boolean
  ignore_case     : boolean  (always set to false — skipping a case earns 0 reward)

Think step-by-step:
1. Look at crime_stats to identify the dominant crime type.
2. Use time_of_day (AM | PM | Night) to gauge urgency.
3. Assign the risk zone accordingly.
4. Decide escalation: escalate when zone is High or time is PM/Night.
"""


def _observation_key(observation: Dict[str, Any]) -> str:
    """Stable cache key for an observation payload."""
    return json.dumps(observation, sort_keys=True, separators=(",", ":"))


def _load_cache(cache_file: Path) -> Dict[str, Dict[str, Any]]:
    if not cache_file.exists():
        return {}
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _save_cache(cache_file: Path, cache: Dict[str, Dict[str, Any]]) -> None:
    cache_file.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")


def infer_action(client: OpenAI, observation: Dict[str, Any], model: str, seed: int) -> Dict[str, Any]:
    """Call the LLM and parse its JSON response into an action dict."""
    chat = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Observation:\n{json.dumps(observation, indent=2)}\n\nReturn JSON only.",
            },
        ],
        temperature=0.1,
        seed=seed,
    )
    raw = chat.choices[0].message.content or "{}"
    parsed = json.loads(raw)
    return Action(**parsed).model_dump()


def _get_action(
    mode: Mode,
    observation: Dict[str, Any],
    cache: Dict[str, Dict[str, Any]],
    client: OpenAI | None,
    model: str,
    seed: int,
) -> Dict[str, Any]:
    """
    Get an action based on runtime mode.

    Modes:
      live   -> always call OpenAI API
      record -> call OpenAI if cache miss, then persist to cache
      replay -> never call OpenAI; require full cache coverage
    """
    key = _observation_key(observation)

    if mode in ("record", "replay") and key in cache:
        return Action(**cache[key]).model_dump()

    if mode == "replay":
        raise RuntimeError(
            "Replay cache miss. Run once with --mode record to create a deterministic cache."
        )

    if client is None:
        raise RuntimeError("OpenAI client is required for live/record mode.")

    action = infer_action(client, observation, model=model, seed=seed)
    if mode == "record":
        cache[key] = action
    return action


def run_llm_baseline(
    episodes: int = 1,
    seed: int = 42,
    verbose: bool = True,
    mode: Mode = "live",
    model: str = DEFAULT_MODEL,
    cache_path: str = DEFAULT_CACHE,
) -> float:
    """
    Run N episodes with the OpenAI baseline and return overall mean reward ∈ [0, 1].

    In replay mode, this function is fully deterministic for a fixed cache+dataset.
    """
    if mode in ("live", "record") and not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set.\n"
            "For deterministic no-key evaluation use: python baseline.py --mode replay"
        )

    random.seed(seed)
    client = (
        OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        if mode in ("live", "record")
        else None
    )

    cache_file = Path(cache_path)
    cache: Dict[str, Dict[str, Any]] = _load_cache(cache_file)

    all_means: list[float] = []
    per_task: Dict[str, list[float]] = {
        "easy": [],
        "medium": [],
        "hard": [],
    }

    for ep in range(1, episodes + 1):
        env = CrimeOpenEnv()
        observation = env.reset()

        total_reward = 0.0
        step_count   = 0
        done         = False

        if verbose:
            print(f"\n{'='*68}")
            print(f"  Episode {ep}/{episodes} — OpenAI Baseline (mode={mode}, model={model})")
            print(f"{'='*68}")

        while not done:
            action = _get_action(
                mode=mode,
                observation=observation.model_dump(),
                cache=cache,
                client=client,
                model=model,
                seed=seed,
            )
            observation, reward, done, info = env.step(action)
            total_reward += reward
            step_count   += 1
            difficulty = str(info.get("difficulty", "")).lower()
            if difficulty in per_task:
                per_task[difficulty].append(float(reward))

            if verbose:
                print(
                    f"  step={step_count:02d}  task={info.get('task',''):<36}"
                    f"  reward={reward:.4f}  done={done}"
                )

        final_state = env.state()
        mean_r = final_state.get("mean_reward", 0.0)
        all_means.append(mean_r)

        if verbose:
            print(f"\n  Episode {ep} summary")
            print(f"    Total reward : {total_reward:.4f}")
            print(f"    Mean reward  : {mean_r:.4f}  (normalized 0.0 – 1.0)")
            print(f"    Steps        : {step_count}")

    if mode == "record":
        _save_cache(cache_file, cache)

    overall_mean = sum(all_means) / len(all_means) if all_means else 0.0
    easy_mean = sum(per_task["easy"]) / len(per_task["easy"]) if per_task["easy"] else 0.0
    medium_mean = sum(per_task["medium"]) / len(per_task["medium"]) if per_task["medium"] else 0.0
    hard_mean = sum(per_task["hard"]) / len(per_task["hard"]) if per_task["hard"] else 0.0

    print(f"\n{'='*68}")
    print(f"  OpenAI Baseline — {episodes} episode(s), seed={seed}, mode={mode}")
    print(f"  Model: {model}")
    print(f"  Per-task mean reward: easy={easy_mean:.4f}  medium={medium_mean:.4f}  hard={hard_mean:.4f}")
    print(f"  Overall mean normalized reward: {overall_mean:.4f}")
    if mode in ("record", "replay"):
        print(f"  Cache file: {cache_file}")
    print(f"{'='*68}")

    return overall_mean


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LLM baseline for CrimeTriageOpenEnv")
    parser.add_argument(
        "--mode",
        choices=["live", "record", "replay"],
        default="live",
        help="live=OpenAI only, record=OpenAI+cache, replay=cache only",
    )
    parser.add_argument("--episodes", type=int, default=1, help="Number of episodes to run")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("OPENAI_MODEL", DEFAULT_MODEL),
        help="OpenAI model id (default: pinned stable model)",
    )
    parser.add_argument(
        "--cache-file",
        type=str,
        default=DEFAULT_CACHE,
        help="Path to JSON action cache used by record/replay modes",
    )
    args = parser.parse_args()

    score = run_llm_baseline(
        episodes=args.episodes,
        seed=args.seed,
        mode=args.mode,
        model=args.model,
        cache_path=args.cache_file,
    )
    print(f"\nFinal normalized score: {score:.4f}")
