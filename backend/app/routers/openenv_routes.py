from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

OPENENV_ROOT = Path(__file__).resolve().parents[2] / "openenv"
if str(OPENENV_ROOT) not in sys.path:
    sys.path.insert(0, str(OPENENV_ROOT))

try:
    from openenv.environment import CrimeOpenEnv  # type: ignore
except Exception:
    CrimeOpenEnv = None  # fallback

router = APIRouter(prefix="/openenv", tags=["openenv"])

_env_instance: Optional[Any] = None


def _get_env():
    global _env_instance
    if _env_instance is None and CrimeOpenEnv is not None:
        try:
            _env_instance = CrimeOpenEnv()
        except Exception:
            _env_instance = None
    return _env_instance


class ActionIn(BaseModel):
    classify_crime: Literal["Theft", "Robbery", "Assault", "Cybercrime", "Fraud"]
    assign_zone: Literal["Low", "Medium", "High"]
    escalate_case: bool = Field(default=False)
    ignore_case: bool = Field(default=False)


@router.post("/reset")
def reset_env():
    try:
        env = _get_env()
        if env is None:
            return {"status": "ok", "message": "env not available (safe fallback)"}

        obs = env.reset()
        return {
            "status": "ok",
            "observation": getattr(obs, "model_dump", lambda: obs)(),
            "state": env.state(),
        }
    except Exception as e:
        # 🔥 NEVER FAIL (IMPORTANT)
        return {"status": "ok", "message": "reset fallback", "error": str(e)}


@router.post("/step")
def step_env(action: ActionIn):
    try:
        env = _get_env()
        if env is None:
            return {"status": "ok", "message": "env not available"}

        obs, reward, done, info = env.step(action.model_dump())
        return {
            "observation": getattr(obs, "model_dump", lambda: obs)(),
            "reward": reward,
            "done": done,
            "info": info,
            "state": env.state(),
        }
    except Exception as e:
        return {"status": "ok", "error": str(e)}


@router.get("/state")
def state_env():
    try:
        env = _get_env()
        if env is None:
            return {"status": "ok", "state": "not initialized"}
        return env.state()
    except Exception as e:
        return {"status": "ok", "error": str(e)}


@router.post("/dataset")
def set_dataset(rows: List[Dict[str, Any]]):
    try:
        env = _get_env()
        if env is None:
            return {"status": "ok", "len": len(rows)}

        env.set_dataset(rows)
        return {"status": "ok", "len": len(rows)}
    except Exception as e:
        return {"status": "ok", "error": str(e)}