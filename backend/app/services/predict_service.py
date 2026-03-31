"""Train / apply RandomForest risk classifier from historical reports."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import Report


CRIME_LABELS = ["Theft", "Robbery", "Assault", "Cybercrime", "Fraud"]


def hour_bucket(time_str: str) -> int:
    if not time_str:
        return 12
    parts = str(time_str).strip().split()
    if not parts:
        return 12
    t = parts[0]
    try:
        h, m = t.split(":", 1)
        hour = int(h) % 24
        if len(parts) > 1 and parts[-1].upper() == "PM" and hour < 12:
            hour = (hour + 12) % 24
        if len(parts) > 1 and parts[-1].upper() == "AM" and hour == 12:
            hour = 0
        return hour
    except Exception:
        return 12


def _encode_crime(ct: str) -> int:
    try:
        return CRIME_LABELS.index(ct)
    except ValueError:
        return 0


def _risk_from_count(c: int) -> int:
    if c >= 8:
        return 2
    if c >= 3:
        return 1
    return 0


@dataclass
class TrainedModel:
    clf: RandomForestClassifier
    region_index: Dict[str, int]


def _build_training_matrix(db: Session, state: Optional[str]) -> Tuple[np.ndarray, np.ndarray, Dict[str, int]]:
    q = db.query(Report.region, Report.crime_type, Report.time, Report.actor_type)
    if state:
        q = q.filter(Report.state == state)
    rows = q.all()

    region_counts: defaultdict[str, int] = defaultdict(int)
    for reg, _, _, _ in rows:
        region_counts[reg] += 1

    regions = sorted({reg for reg, _, _, _ in rows}) or ["Unknown"]
    region_index = {r: i for i, r in enumerate(regions)}

    if len(rows) < 5:
        return np.zeros((0, 4), dtype=np.float32), np.zeros((0,), dtype=np.int32), region_index

    X: List[List[float]] = []
    y: List[int] = []
    for reg, crime, time_s, actor in rows:
        rc = region_counts.get(reg, 0)
        y.append(_risk_from_count(rc))
        X.append(
            [
                float(region_index.get(reg, 0)),
                float(hour_bucket(time_s)),
                float(_encode_crime(crime)),
                1.0 if (actor or "").lower() == "group" else 0.0,
            ]
        )
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int32), region_index


def train_model(db: Session, state: Optional[str] = None) -> Optional[TrainedModel]:
    X, y, region_index = _build_training_matrix(db, state)
    if X.shape[0] < 5 or len(np.unique(y)) < 2:
        return None
    clf = RandomForestClassifier(
        n_estimators=80,
        max_depth=6,
        random_state=42,
        class_weight="balanced_subsample",
    )
    clf.fit(X, y)
    return TrainedModel(clf=clf, region_index=region_index)


def predict_risk(
    db: Session,
    state: str,
    region: str,
    time_str: str,
    crime_type: str,
    actor_type: str,
) -> Dict[str, Any]:
    tm = train_model(db, state=state)
    hour = hour_bucket(time_str)
    crime = _encode_crime(crime_type)
    group = 1.0 if (actor_type or "").lower() == "group" else 0.0

    if tm is None:
        # Frequency fallback when too little labeled training signal
        cnt = (
            db.query(func.count(Report.id))
            .filter(Report.state == state, Report.region == region)
            .scalar()
            or 0
        )
        bucket = _risk_from_count(int(cnt))
        labels = ["Low", "Medium", "High"]
        return {
            "risk_level": labels[bucket],
            "confidence": 0.55,
            "model": "frequency_fallback",
            "features": {"region_reports": int(cnt), "hour": hour},
        }

    idx = tm.region_index.get(region, 0)
    X = np.array([[float(idx), float(hour), float(crime), group]], dtype=np.float32)
    proba = tm.clf.predict_proba(X)[0]
    pred = int(tm.clf.predict(X)[0])
    labels = ["Low", "Medium", "High"]
    return {
        "risk_level": labels[min(pred, 2)],
        "confidence": round(float(np.max(proba)), 3),
        "model": "random_forest",
        "features": {
            "region_index": idx,
            "hour": hour,
            "crime_index": crime,
            "group": bool(group),
        },
        "probabilities": {labels[i]: round(float(p), 3) for i, p in enumerate(proba)},
    }


def high_risk_zones(db: Session, state: str, top_n: int = 6) -> List[Dict[str, Any]]:
    rows = (
        db.query(Report.region, func.count(Report.id))
        .filter(Report.state == state)
        .group_by(Report.region)
        .all()
    )
    scored = []
    for reg, c in rows:
        r = predict_risk(db, state, reg, "12:00 PM", "Theft", "Individual")
        scored.append({"region": reg, "reports": int(c), **{k: r[k] for k in ("risk_level", "confidence") if k in r}})
    scored.sort(key=lambda x: ({"High": 3, "Medium": 2, "Low": 1}.get(x["risk_level"], 0), x["reports"]), reverse=True)
    return scored[:top_n]
