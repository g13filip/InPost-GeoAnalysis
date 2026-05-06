"""Czyszczenie danych surowych i przypisanie h3_index do każdego paczkomatu.

TODO: Zaimplementuj w oparciu o notebook 05_assign_machines_to_hex.
Kluczowe: filtrowanie po mieście (address_details.city), obsługa
duplikatów, przypisanie h3.latlng_to_cell(lat, lng, resolution).
"""
from __future__ import annotations
import numpy as np
import h3

import pandas as pd
from paczkomatoza.io.paths import raw_snapshot_path


def assign_h3_index(city_slug: str, resolution: int = 9) -> pd.DataFrame:
    """Dodaje kolumnę h3_index na podstawie latitude/longitude."""

    snapshot_path = raw_snapshot_path(city_slug)
    df = pd.read_parquet(snapshot_path)

    machines = df.dropna(subset=["latitude", "longitude"]).copy()
    machines["is_operating"] = machines["status"].fillna("").str.lower() == "operating"

    def get_primary_type(t):
        if isinstance(t, (list, np.ndarray)) and len(t) > 0:
            return t[0]
        return None

    machines["type_primary"] = machines["type"].apply(get_primary_type)

    machines["h3_index"] = [
        h3.latlng_to_cell(lat, lng, resolution)
        for lat, lng in zip(machines["latitude"], machines["longitude"])
    ]
    return machines

