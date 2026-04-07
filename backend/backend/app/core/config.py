from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
# override=True: values in backend/.env win over empty/mis-set Windows env vars
load_dotenv(dotenv_path=_env_path, override=True)


def env_str(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


JWT_SECRET = env_str("JWT_SECRET", "change-me-in-production-min-32-chars!!")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(env_str("JWT_EXPIRE_HOURS", "168"))

OPENAI_API_KEY = env_str("OPENAI_API_KEY", "")
OPENAI_MODEL = env_str("OPENAI_MODEL", "gpt-4o-mini")

POLICE_REGISTER_SECRET = env_str("POLICE_REGISTER_SECRET", "")
ALLOW_OPEN_POLICE_REGISTER = env_bool("ALLOW_OPEN_POLICE_REGISTER", False)

CORS_ORIGINS = [o.strip() for o in env_str("CORS_ORIGINS", "*").split(",") if o.strip()]
