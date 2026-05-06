"""Operacje geoprzestrzenne: dystanse, centroidy, k-ring.

TODO: Zaimplementuj w oparciu o notebook 05_assign_machines_to_hex.
Kluczowe: BallTree haversine do query_nearest i query_within_radius,
h3.grid_disk dla sąsiedztwa k-ring.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_balltree(lats: np.ndarray, lngs: np.ndarray):
    """Buduje BallTree (haversine) dla zbioru punktów.

    Ref: notebook 05 — sklearn.neighbors.BallTree z metryką haversine
    """
    raise NotImplementedError


def query_nearest(tree, query_lats: np.ndarray, query_lngs: np.ndarray) -> np.ndarray:
    """Zwraca odległość [m] do najbliższego punktu w drzewie dla każdego zapytania.

    Ref: notebook 05 — dist_to_nearest_m
    """
    raise NotImplementedError


def query_within_radius(
    tree, query_lats: np.ndarray, query_lngs: np.ndarray, radius_m: float
) -> np.ndarray:
    """Zwraca liczbę punktów w promieniu radius_m dla każdego zapytania.

    Ref: notebook 05 — n_machines_within_500m / n_machines_within_1000m
    """
    raise NotImplementedError


def kring_counts(df: pd.DataFrame, h3_col: str, count_col: str, k: int) -> pd.Series:
    """Dla każdego heksu sumuje count_col w k-ring sąsiedztwie.

    Ref: notebook 05 — n_in_neighborhood_k1/k2
    """
    raise NotImplementedError
