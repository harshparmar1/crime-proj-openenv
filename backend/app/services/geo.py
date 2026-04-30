"""Approximate coordinates for state/region (deterministic) — for mapping without geocoder."""

from __future__ import annotations

import hashlib

from ..core.state_regions import STATE_REGIONS

# Accurate state/capital centers (India)
STATE_CENTERS: dict[str, tuple[float, float]] = {
    "Andhra Pradesh": (16.5, 80.5),
    "Arunachal Pradesh": (27.1, 93.6),
    "Assam": (26.1, 91.8),
    "Bihar": (25.6, 85.1),
    "Chhattisgarh": (21.3, 81.6),
    "Goa": (15.5, 73.8),
    "Gujarat": (23.2, 72.6),
    "Haryana": (30.7, 76.8),
    "Himachal Pradesh": (31.1, 77.2),
    "Jharkhand": (23.3, 85.3),
    "Karnataka": (12.97, 77.59),
    "Kerala": (8.5, 76.9),
    "Madhya Pradesh": (23.3, 77.4),
    "Maharashtra": (19.1, 72.9),
    "Manipur": (24.8, 93.9),
    "Meghalaya": (25.6, 91.9),
    "Mizoram": (23.7, 92.7),
    "Nagaland": (25.7, 94.1),
    "Odisha": (20.3, 85.8),
    "Punjab": (30.7, 76.8),
    "Rajasthan": (26.9, 75.8),
    "Sikkim": (27.3, 88.6),
    "Tamil Nadu": (13.08, 80.27),
    "Telangana": (17.4, 78.5),
    "Tripura": (23.8, 91.3),
    "Uttar Pradesh": (26.8, 80.9),
    "Uttarakhand": (30.3, 78.0),
    "West Bengal": (22.6, 88.4),
    "Andaman and Nicobar Islands": (11.7, 92.7),
    "Chandigarh": (30.7, 76.8),
    "Dadra and Nagar Haveli and Daman and Diu": (20.4, 72.9),
    "Delhi": (28.6, 77.2),
    "Jammu and Kashmir": (34.1, 74.8),
    "Ladakh": (34.2, 77.6),
    "Lakshadweep": (10.6, 72.6),
    "Puducherry": (11.9, 79.8),
}


def approximate_lat_lng(state: str, region: str) -> tuple[float, float]:
    base_lat, base_lng = STATE_CENTERS.get(state, (22.5, 79.0))
    # Small offset based on region name to avoid overlap
    h = hashlib.sha256(f"{state}|{region}".encode()).digest()
    dlat = (int.from_bytes(h[:2], "big") / 65535.0 - 0.5) * 0.5
    dlng = (int.from_bytes(h[2:4], "big") / 65535.0 - 0.5) * 0.5
    return round(base_lat + dlat, 5), round(base_lng + dlng, 5)


def gps_to_state_region_hint(lat: float, lng: float) -> tuple[str, str]:
    """Find the nearest (state, region) pair using approximate coordinates."""
    best_state = "Maharashtra"
    best_region = "Mumbai"
    best_d = 1e9

    for st, regions in STATE_REGIONS.items():
        for rg in regions:
            rlat, rlng = approximate_lat_lng(st, rg)
            d = (rlat - lat) ** 2 + (rlng - lng) ** 2
            if d < best_d:
                best_d = d
                best_state = st
                best_region = rg

    return best_state, best_region


def format_current_location(lat: float | None, lng: float | None) -> str | None:
    if lat is None or lng is None:
        return None
    state, region = gps_to_state_region_hint(lat, lng)
    return f"{state}, {region}"
