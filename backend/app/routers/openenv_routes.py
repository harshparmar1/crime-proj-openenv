from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

OPENENV_ROOT = Path(__file__).resolve().parents[2] / "openenv"
if str(OPENENV_ROOT) not in sys.path:
    sys.path.insert(0, str(OPENENV_ROOT))

from openenv.environment import CrimeOpenEnv  # type: ignore

router = APIRouter(prefix="/openenv", tags=["openenv"])

_env_instance: Optional[CrimeOpenEnv] = None


def _get_env() -> CrimeOpenEnv:
    global _env_instance
    if _env_instance is None:
        _env_instance = CrimeOpenEnv()
    return _env_instance


class ActionIn(BaseModel):
    classify_crime: Literal["Theft", "Robbery", "Assault", "Cybercrime", "Fraud"]
    assign_zone: Literal["Low", "Medium", "High"]
    escalate_case: bool = Field(default=False)
    ignore_case: bool = Field(default=False)


@router.post("/reset")
def reset_env():
    env = _get_env()
    obs = env.reset()
    return {"observation": obs.model_dump(), "state": env.state()}


@router.post("/step")
def step_env(action: ActionIn):
    env = _get_env()
    obs, reward, done, info = env.step(action.model_dump())
    return {
        "observation": obs.model_dump(),
        "reward": reward,
        "done": done,
        "info": info,
        "state": env.state(),
    }


@router.get("/state")
def state_env():
    env = _get_env()
    return env.state()


@router.post("/dataset")
def set_dataset(rows: List[Dict[str, Any]]):
    env = _get_env()
    env.set_dataset(rows)
    return {"status": "ok", "len": len(rows)}
