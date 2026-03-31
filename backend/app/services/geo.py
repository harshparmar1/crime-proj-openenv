"""Approximate coordinates for state/region (deterministic) — for mapping without geocoder."""

from __future__ import annotations

import hashlib

from ..core.state_regions import STATE_REGIONS

# Approximate state centers (India + islands)
STATE_CENTERS: dict[str, tuple[float, float]] = {
    "Andhra Pradesh": (15.9, 79.7),
    "Arunachal Pradesh": (27.1, 93.6),
    "Assam": (26.2, 92.9),
    "Bihar": (25.6, 85.1),
    "Chhattisgarh": (21.3, 81.9),
    "Goa": (15.5, 74.0),
    "Gujarat": (22.3, 71.2),
    "Haryana": (29.1, 76.1),
    "Himachal Pradesh": (31.8, 77.2),
    "Jharkhand": (23.6, 85.3),
    "Karnataka": (15.3, 75.7),
    "Kerala": (10.9, 76.3),
    "Madhya Pradesh": (22.9, 78.7),
    "Maharashtra": (19.8, 75.7),
    "Manipur": (24.8, 93.9),
    "Meghalaya": (25.5, 91.4),
    "Mizoram": (23.2, 92.9),
    "Nagaland": (26.2, 94.5),
    "Odisha": (20.9, 85.1),
    "Punjab": (31.1, 75.3),
    "Rajasthan": (27.0, 74.2),
    "Sikkim": (27.5, 88.5),
    "Tamil Nadu": (11.1, 78.7),
    "Telangana": (18.0, 79.0),
    "Tripura": (23.8, 91.3),
    "Uttar Pradesh": (27.6, 80.7),
    "Uttarakhand": (30.1, 79.0),
    "West Bengal": (22.9, 87.9),
    "Andaman and Nicobar Islands": (11.7, 92.7),
    "Chandigarh": (30.7, 76.8),
    "Dadra and Nagar Haveli and Daman and Diu": (20.4, 72.9),
    "Delhi": (28.6, 77.2),
    "Jammu and Kashmir": (33.8, 76.6),
    "Ladakh": (34.2, 77.6),
    "Lakshadweep": (10.6, 72.6),
    "Puducherry": (11.9, 79.8),
}


def approximate_lat_lng(state: str, region: str) -> tuple[float, float]:
    base_lat, base_lng = STATE_CENTERS.get(state, (22.5, 79.0))
    h = hashlib.sha256(f"{state}|{region}".encode()).digest()
    dlat = (int.from_bytes(h[:2], "big") / 65535.0 - 0.5) * 0.9
    dlng = (int.from_bytes(h[2:4], "big") / 65535.0 - 0.5) * 0.9
    return round(base_lat + dlat, 5), round(base_lng + dlng, 5)


def gps_to_state_region_hint(lat: float, lng: float) -> tuple[str, str]:
    """Pick nearest state center + first region (coarse)."""
    best_state = "Maharashtra"
    best_d = 1e9
    for st, (slat, slng) in STATE_CENTERS.items():
        d = (slat - lat) ** 2 + (slng - lng) ** 2
        if d < best_d:
            best_d = d
            best_state = st
    regions = STATE_REGIONS.get(best_state, ["Unknown"])
    return best_state, regions[0]
