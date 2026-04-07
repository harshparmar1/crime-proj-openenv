"""Computer-vision pipeline: OpenCV heuristics + optional Ultralytics YOLO when installed."""

from __future__ import annotations

from typing import Any, Dict, List

import numpy as np


def analyze_image_bytes(data: bytes) -> Dict[str, Any]:
    """Detect weapon / vehicle cues from image bytes."""
    result: Dict[str, Any] = {
        "weapon": {"detected": False, "confidence": 0.0, "labels": []},
        "vehicle": {"detected": False, "confidence": 0.0, "labels": []},
        "notes": [],
    }
    if not data:
        result["notes"].append("empty_image")
        return result

    yolo_hits = _try_yolo(data)
    if yolo_hits:
        return yolo_hits

    try:
        import cv2
    except ImportError:
        result["notes"].append("opencv_not_installed")
        return result

    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        result["notes"].append("decode_failed")
        return result

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 60, 180)
    long_lines = 0
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=40, maxLineGap=10)
    if lines is not None:
        for ln in lines:
            x1, y1, x2, y2 = ln[0]
            length = float(np.hypot(x2 - x1, y2 - y1))
            if length > 80:
                long_lines += 1

    # Elongated dark regions (very rough "object" cue)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    _, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(th, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    large_boxes = 0
    weapon_like = 0
    for c in contours:
        area = cv2.contourArea(c)
        if area < 800:
            continue
        x, y, w, h = cv2.boundingRect(c)
        ar = max(w, h) / max(min(w, h), 1)
        if area > 8000 and ar < 2.5:
            large_boxes += 1
        if area > 1500 and ar > 3.0 and long_lines >= 3:
            weapon_like += 1

    vehicle_score = min(1.0, large_boxes * 0.25 + (1.0 if len(contours) > 40 else 0.0) * 0.15)
    weapon_score = min(1.0, weapon_like * 0.35 + (long_lines / 15.0) * 0.2)

    if vehicle_score >= 0.35:
        result["vehicle"] = {
            "detected": True,
            "confidence": round(vehicle_score, 2),
            "labels": ["vehicle_shape_candidate"],
        }
    if weapon_score >= 0.35:
        result["weapon"] = {
            "detected": True,
            "confidence": round(weapon_score, 2),
            "labels": ["elongated_object_lines"],
        }

    result["notes"].append("opencv_heuristic")
    return result


def _try_yolo(data: bytes) -> Dict[str, Any] | None:
    try:
        from ultralytics import YOLO
    except ImportError:
        return None
    import cv2

    arr = np.frombuffer(data, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    model = YOLO("yolov8n.pt")
    pred = model(img, verbose=False)[0]
    names = pred.names or {}
    weapon_ids = {k for k, v in names.items() if any(x in v.lower() for x in ("knife", "scissors"))}
    vehicle_ids = {k for k, v in names.items() if any(x in v.lower() for x in ("car", "bus", "truck", "motor", "bike", "bicycle"))}

    w_conf = 0.0
    v_conf = 0.0
    w_labs: List[str] = []
    v_labs: List[str] = []
    if pred.boxes is not None:
        for b in pred.boxes:
            cls = int(b.cls[0])
            conf = float(b.conf[0])
            name = names.get(cls, str(cls))
            if cls in weapon_ids:
                w_conf = max(w_conf, conf)
                w_labs.append(name)
            if cls in vehicle_ids:
                v_conf = max(v_conf, conf)
                v_labs.append(name)

    if w_conf == 0 and v_conf == 0:
        return {
            "weapon": {"detected": False, "confidence": 0.0, "labels": []},
            "vehicle": {"detected": False, "confidence": 0.0, "labels": []},
            "notes": ["yolo_no_vehicle_weapon_class"],
        }
    return {
        "weapon": {"detected": w_conf >= 0.25, "confidence": round(w_conf, 2), "labels": list(set(w_labs))},
        "vehicle": 
        {"detected": v_conf >= 0.25, "confidence": round(v_conf, 2), "labels": list(set(v_labs))},
        "notes": ["yolov8n"],
    }


def map_cv_to_form_fields(analysis: Dict[str, Any]) -> Dict[str, str]:
    weapon = "Yes" if analysis.get("weapon", {}).get("detected") else "No"
    vehicle = "Yes" if analysis.get("vehicle", {}).get("detected") else "No"
    vs = []
    if analysis.get("vehicle", {}).get("detected"):
        labs = analysis.get("vehicle", {}).get("labels") or []
        if any("truck" in str(x).lower() for x in labs):
            vs.append("Truck")
        elif any("bus" in str(x).lower() for x in labs):
            vs.append("Truck")
        elif any("bike" in str(x).lower() or "bicycle" in str(x).lower() for x in labs):
            vs.append("Bike")
        elif any("car" in str(x).lower() or "motor" in str(x).lower() for x in labs):
            vs.append("Car")
    vehicle_selection = vs[0] if vs else "None"
    return {"weaponUsed": weapon, "vehicleUsed": vehicle, "vehicleSelection": vehicle_selection}
