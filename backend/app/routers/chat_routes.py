from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_db, optional_current_user
from ..db import User
from ..services.chat_service import answer_query

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


@router.post("/")
async def chat(
    body: ChatRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[Optional[User], Depends(optional_current_user)],
):
    state = user.state if user else None
    return await answer_query(db, body.message, state)
