"""Ważony score jakości pokrycia paczkomatem.

TODO: Zaimplementuj w oparciu o notebook 05_assign_machines_to_hex.
Wagi: Outdoor=1.0, Indoor=0.5, POP=0.3; lokalizacja: zewnętrzna=1.0, wewnętrzna=0.6.
"""
from __future__ import annotations

import pandas as pd


def compute_weighted_score(df_machines: pd.DataFrame) -> pd.Series:
    """Wylicza ważony score per paczkomat na podstawie typu i lokalizacji."""
    weights = {
    ("parcel_locker", "Outdoor"): 1.0,
    ("parcel_locker", "Indoor"): 0.5,
    ("pop", "Outdoor"): 0.3,
    ("pop", "Indoor"): 0.2,
    }

    df_machines["weight"] = [
        weights.get((t,l), 0.1)
        for t, l in zip(df_machines["type_primary"], df_machines["location_type"])
    ]

    scores = df_machines.groupby("h3_index")["weight"].sum().reset_index(name="weighted_score")
    scores["weighted_score"] = scores["weighted_score"].round(2)


    return scores


def classify_accessibility(dist_m: float) -> str:
    """Dodaje accessibility_class na podstawie dist_to_nearest_m.
    Progi: excellent < 200m, good < 500m, fair < 1000m, poor >= 1000m.
    """
    if dist_m < 200:
        return "excellent"
    if dist_m < 500:
        return "good"
    if dist_m < 1000:
        return "fair"
    return "poor"
