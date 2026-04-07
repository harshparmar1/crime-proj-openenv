from __future__ import annotations

from collections import Counter, defaultdict
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..core.state_regions import STATE_REGIONS
from ..db import Report
from ..deps import get_db
from ..rl_service import get_rl_zones_for_state, risk_from_frequency
from ..services.geo import approximate_lat_lng, gps_to_state_region_hint
from ..services.predict_service import high_risk_zones, hour_bucket, predict_risk

router = APIRouter(tags=["analytics"])


@router.get("/analytics/state-heatmap")
def state_heatmap(
    db: Annotated[Session, Depends(get_db)],
    crime_type: Optional[str] = None,
):
    q = db.query(Report.state, func.count(Report.id)).group_by(Report.state)
    if crime_type:
        q = q.filter(Report.crime_type == crime_type)
    rows = q.all()
    return [{"state": st, "value": int(cnt)} for (st, cnt) in rows]


@router.get("/analytics")
def analytics(
    db: Annotated[Session, Depends(get_db)],
    state: Optional[str] = None,
    region: Optional[str] = None,
    crime_type: Optional[str] = None,
    actor_type: Optional[str] = None,
):
    q = db.query(Report)
    if state:
        q = q.filter(Report.state == state)
    if region:
        q = q.filter(Report.region == region)
    if crime_type:
        q = q.filter(Report.crime_type == crime_type)
    if actor_type:
        q = q.filter(Report.actor_type == actor_type)
    rows = q.all()

    def to_series(counter: Counter):
        return [{"name": k, "value": v} for k, v in counter.items()]

    peak_hours: Counter[int] = Counter()
    for r in rows:
        peak_hours[hour_bucket(r.time or "")] += 1
    peak_chart = [{"name": f"{h}:00", "value": c} for h, c in sorted(peak_hours.items())]

    return {
        "crime_type": to_series(Counter(r.crime_type for r in rows)),
        "actor_type": to_series(Counter(r.actor_type for r in rows)),
        "time": to_series(Counter((r.time or "").split(" ")[0] for r in rows)),
        "region": to_series(Counter(r.region for r in rows)),
        "vehicle": to_series(Counter(r.vehicle for r in rows)),
        "peak_hours": peak_chart,
        "total": len(rows),
    }


@router.get("/zones")
def zones(
    db: Annotated[Session, Depends(get_db)],
    state: Optional[str] = None,
    mode: str = "rl",
):
    if state:
        if state not in STATE_REGIONS:
            raise HTTPException(status_code=400, detail="Invalid state")

        if mode == "rl":
            return get_rl_zones_for_state(db, state, STATE_REGIONS[state])

        rows = db.query(Report.region).filter(Report.state == state).all()
        frequency = defaultdict(int)
        for (rg,) in rows:
            frequency[rg] += 1
        return [
            {
                "state": state,
                "zone": rg,
                "risk": risk_from_frequency(frequency.get(rg, 0)),
                "crime_frequency": frequency.get(rg, 0),
            }
            for rg in STATE_REGIONS[state]
        ]

    rows = db.query(Report.state, Report.region).all()
    frequency = defaultdict(int)
    for st, rg in rows:
        frequency[(st, rg)] += 1

    result = []
    for st, regions in STATE_REGIONS.items():
        for rg in regions:
            count = frequency.get((st, rg), 0)
            result.append(
                {"state": st, "zone": rg, "risk": risk_from_frequency(count), "crime_frequency": count}
            )
    return result


@router.get("/map/incidents")
def map_incidents(
    db: Annotated[Session, Depends(get_db)],
    state: Optional[str] = None,
    limit: int = 200,
):
    q = db.query(Report).order_by(Report.created_at.desc())
    if state:
        q = q.filter(Report.state == state)
    out = []
    for r in q.limit(min(limit, 500)).all():
        lat, lng = r.latitude, r.longitude
        if lat is None or lng is None:
            lat, lng = approximate_lat_lng(r.state, r.region)
        out.append(
            {
                "public_id": r.public_id,
                "state": r.state,
                "region": r.region,
                "crime_type": r.crime_type,
                "latitude": lat,
                "longitude": lng,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "is_panic": r.is_panic,
            }
        )
    return out


@router.get("/map/region-stats")
def region_stats(
    db: Annotated[Session, Depends(get_db)],
    state: str,
    region: str,
):
    if state not in STATE_REGIONS or region not in STATE_REGIONS[state]:
        raise HTTPException(status_code=400, detail="Invalid state/region")
    rows = db.query(Report).filter(Report.state == state, Report.region == region).all()
    pred = predict_risk(db, state, region, "12:00 PM", "Theft", "Individual")
    return {
        "state": state,
        "region": region,
        "total": len(rows),
        "by_crime": [{"name": k, "value": v} for k, v in Counter(r.crime_type for r in rows).items()],
        "prediction": pred,
    }


@router.get("/predict/zones")
def predict_zones(
    db: Annotated[Session, Depends(get_db)],
    state: str,
):
    if state not in STATE_REGIONS:
        raise HTTPException(status_code=400, detail="Invalid state")
    return {"state": state, "high_risk": high_risk_zones(db, state)}


@router.get("/states")
def states_regions():
    return STATE_REGIONS


@router.get("/geo/hint")
def geo_hint(lat: float, lng: float):
    st, rg = gps_to_state_region_hint(lat, lng)
    return {"state": st, "region": rg}
