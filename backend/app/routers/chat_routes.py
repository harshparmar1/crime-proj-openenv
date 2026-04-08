from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_db, optional_current_user
from ..db import User
from ..services.chat_service import answer_query
from ..services.chat_runtime import chat_runtime

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None


async def _chat_impl(
    body: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[Optional[User], Depends(optional_current_user)],
):
    session_key = body.conversation_id or (user.email if user else "anonymous")
    if not session_key:
        session_key = "anonymous"

    # smart dynamic conversation engine with context memory
    runtime = chat_runtime.handle(body.message, session_key=session_key, user_name=(user.username if user else None))

    # optional OpenAI enhancement path (existing logic), only when API quota allows
    state = user.state if user else None
    role = user.role if user else "citizen"
    username = user.username if user else None
    result = await answer_query(db, body.message, state, role=role, username=username)
    answer = str(result.get("answer", ""))
    if "OpenAI error" in answer or "insufficient_quota" in answer or "RateLimitError" in answer:
        result["answer"] = (
            "AI guidance is temporarily unavailable, but I can still help from local safety data. "
            "Tell me what happened, where, and when, and I will guide your next steps."
        )
        result["source"] = "db"
    # Prefer OpenAI reply if it succeeds; otherwise keep smart runtime reply.
    if result.get("source") == "openai" and answer:
        runtime["reply"] = answer
        runtime["source"] = "openai"
    else:
        runtime["source"] = "runtime"

    # Backward compatibility for old UI expecting `answer`.
    runtime["answer"] = runtime["reply"]
    return runtime


@router.post("/")
async def chat(
    body: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[Optional[User], Depends(optional_current_user)],
):
    return await _chat_impl(body, db, user)


@router.post("")
async def chat_no_slash(
    body: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[Optional[User], Depends(optional_current_user)],
):
    return await _chat_impl(body, db, user)
