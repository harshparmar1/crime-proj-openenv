from __future__ import annotations

from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.state_regions import STATE_REGIONS
from ..deps import get_db
from ..services.image_service import analyze_image_bytes, map_cv_to_form_fields
from ..services.nlp_service import extract_from_text, time_of_day_hint
from ..services.predict_service import predict_risk

router = APIRouter(prefix="/ai", tags=["ai"])
legacy = APIRouter(tags=["ai"])


class PredictRequest(BaseModel):
    state: str
    region: str
    time: str
    crime_type: str
    actor_type: str


def _predict_impl(body: PredictRequest, db: Session):
    if body.state not in STATE_REGIONS:
        raise HTTPException(status_code=400, detail="Invalid state")
    if body.region not in STATE_REGIONS[body.state]:
        raise HTTPException(status_code=400, detail="Invalid region")
    return predict_risk(db, body.state, body.region, body.time, body.crime_type, body.actor_type)


@router.post("/predict")
def predict(body: PredictRequest, db: Annotated[Session, Depends(get_db)]):
    return _predict_impl(body, db)


@legacy.post("/predict")
def predict_top_level(body: PredictRequest, db: Annotated[Session, Depends(get_db)]):
    return _predict_impl(body, db)


@router.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...)):
    data = await file.read()
    analysis = analyze_image_bytes(data)
    form_hints = map_cv_to_form_fields(analysis)
    return {"analysis": analysis, "form_hints": form_hints}


class NlpRequest(BaseModel):
    text: str
    default_state: Optional[str] = None


@router.post("/nlp/extract")
def nlp_extract(body: NlpRequest):
    ex = extract_from_text(body.text, body.default_state)
    ex["time_hint"] = time_of_day_hint(body.text)
    return ex
