from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Try loading backend/.env first, then root .env if available
_backend_env = Path(__file__).resolve().parent.parent.parent / ".env"
if _backend_env.exists():
    load_dotenv(dotenv_path=_backend_env, override=False)
else:
    _root_env = Path(__file__).resolve().parent.parent.parent.parent / ".env"
    if _root_env.exists():
        load_dotenv(dotenv_path=_root_env, override=False)


def env_str(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


# Security & JWT
JWT_SECRET = env_str("JWT_SECRET", "") or env_str("SECRET_KEY", "change-me-in-production-min-32-chars!!")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(env_str("JWT_EXPIRE_HOURS", "168"))

# OpenAI Configuration
OPENAI_API_KEY = env_str("OPENAI_API_KEY", "")
OPENAI_MODEL = env_str("OPENAI_MODEL", "gpt-4o-mini")

# Police Registration Policy
POLICE_REGISTER_SECRET = env_str("POLICE_REGISTER_SECRET", "")
ALLOW_OPEN_POLICE_REGISTER = env_bool("ALLOW_OPEN_POLICE_REGISTER", False)

# CORS Configuration
# Default development origins
_DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

_raw_origins = env_str("CORS_ORIGINS", "") or env_str("ALLOWED_ORIGINS", "")
_frontend_url = env_str("FRONTEND_URL", "")

_parsed_origins: list[str] = list(_DEFAULT_ORIGINS)

if _frontend_url:
    for u in _frontend_url.split(","):
        clean_u = u.strip().rstrip("/")
        if clean_u and clean_u not in _parsed_origins:
            _parsed_origins.append(clean_u)

if _raw_origins:
    if _raw_origins.strip() == "*":
        _parsed_origins = ["*"]
    else:
        for o in _raw_origins.split(","):
            clean_o = o.strip().rstrip("/")
            if clean_o and clean_o not in _parsed_origins:
                _parsed_origins.append(clean_o)

CORS_ORIGINS = _parsed_origins
CORS_ORIGIN_REGEX = env_str("CORS_ORIGIN_REGEX", r"^https://.*\.vercel\.app$")
