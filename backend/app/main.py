from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Load .env without overriding existing environment variables
_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=_backend_root / ".env", override=False)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import CORS_ORIGINS, CORS_ORIGIN_REGEX
from .db import Base, engine
from .routers import (
    ai_routes,
    analytics_routes,
    auth_routes,
    chat_routes,
    notifications_routes,
    openenv_routes,
    panic_routes,
    predict_routes,
    realtime_routes,
    reports_routes,
    dispatch_routes,
    case_intelligence_routes,
    suspect_routes,
)
from .services.migrate import run_schema_migrations

# Upload directory
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_schema_migrations(engine)
    yield


app = FastAPI(
    title="CRIMEWATCH AI",
    version="3.0.0",
    lifespan=lifespan,
)

_allow_all = "*" in CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else CORS_ORIGINS,
    allow_origin_regex=None if _allow_all else CORS_ORIGIN_REGEX,
    allow_credentials=False if _allow_all else True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_routes.router)
app.include_router(analytics_routes.router)
app.include_router(reports_routes.router)
app.include_router(ai_routes.router)
app.include_router(ai_routes.legacy)
app.include_router(realtime_routes.router)
app.include_router(panic_routes.router)
app.include_router(predict_routes.router)
app.include_router(chat_routes.router)
app.include_router(notifications_routes.router)
app.include_router(openenv_routes.router)
app.include_router(dispatch_routes.router)
app.include_router(case_intelligence_routes.router)
app.include_router(suspect_routes.router)


@app.get("/")
def home():
    return {"status": "ok"}


@app.get("/health") 
def health():
    return {"status": "ok", "service": "crime-intelligence-api"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=7860)