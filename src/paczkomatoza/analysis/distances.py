"""Obliczanie odległości do najbliższej maszyny dla każdego heksagonu.

TODO: Zaimplementuj w oparciu o notebook 05_assign_machines_to_hex.
Używa BallTree z metryką haversine (sklearn) dla O(n log n) złożoności.
"""
from __future__ import annotations

import h3
from sklearn.neighbors import BallTree
import pandas as pd
import numpy as np

from paczkomatoza.io.paths import hexagons_path

def build_balltree(coords_df: pd.DataFrame) -> BallTree | None:
    """Buduje BallTree z DataFrame zawierającego latitude/longitude.
    Zwraca None, jeśli DataFrame pusty.
    """

    if len(coords_df) == 0:
        return None
    coords_rad = np.radians(coords_df[["latitude", "longitude"]].values)
    return BallTree(coords_rad, metric="haversine")

def query_nearest(tree: BallTree | None, points_latlng: np.ndarray) -> np.ndarray:
    """Zwraca odległości w METRACH od każdego punktu do najbliższego punktu w drzewie.
    
    Jeśli drzewo jest puste/None, zwraca tablicę np.inf (nie ma do czego liczyć).
    """
    earth_radius = 6371000  

    if tree is None:
        return np.full(len(points_latlng), np.inf)
    
    points_rad = np.radians(points_latlng)
    distances_rad, _ = tree.query(points_rad, k=1)
    return distances_rad[:, 0] * earth_radius

def query_within_radius(tree: BallTree | None, points_latlng: np.ndarray, radius_m: float) -> np.ndarray:
    """Zwraca count sąsiadów w promieniu radius_m wokół każdego punktu."""

    earth_radius = 6371000

    if tree is None:
        return np.zeros(len(points_latlng), dtype=int)
    
    points_rad = np.radians(points_latlng)
    radius_rad = radius_m / earth_radius
    indices = tree.query_radius(points_rad, r=radius_rad)
    return np.array([len(arr) for arr in indices])

def compute_distances(df_hexes: pd.DataFrame,
    df_machines: pd.DataFrame,
) -> pd.DataFrame:
    """Dodaje do df_hexes kolumny dist_to_nearest_m, dist_to_nearest_outdoor_m,
    n_machines_within_500m, n_machines_within_1000m.
    """

    tree_all = build_balltree(df_machines)
    tree_outdoor = build_balltree(df_machines[df_machines["is_outdoor"]])
    tree_operating = build_balltree(df_machines[df_machines["is_operating"]])

    hex_centers = df_hexes[["center_lat", "center_lng"]].rename(
    columns={"center_lat": "latitude", "center_lng": "longitude"}
    ).values

    dist_to_nearest = query_nearest(tree_all, hex_centers)
    dist_to_nearest_outdoor = query_nearest(tree_outdoor, hex_centers)
    dist_to_nearest_operating = query_nearest(tree_operating, hex_centers)

    distances_df = pd.DataFrame({
    "h3_index": df_hexes["h3_index"].values,
    "dist_to_nearest_m": np.where(np.isinf(dist_to_nearest), 999_999, dist_to_nearest.round(0)).astype(int),
    "dist_to_nearest_outdoor_m": np.where(np.isinf(dist_to_nearest_outdoor), 999_999, dist_to_nearest_outdoor.round(0)).astype(int),
    "dist_to_nearest_operating_m": np.where(np.isinf(dist_to_nearest_operating), 999_999, dist_to_nearest_operating.round(0)).astype(int),
})
    for radius in [500 , 1000]:
        col = f"n_machines_within_{radius}m"
        distances_df[col] = query_within_radius(tree_all, hex_centers, radius)

    return distances_df


def neighborhood_disk(hexagons: pd.DataFrame, 
                      counts: pd.DataFrame) -> pd.DataFrame:
    """Buduje DataFrame z h3_index i n_machines w sąsiedztwie 1 oraz 2 heksagonów."""

    machine_count_by_hex = dict(zip(counts["h3_index"], counts["n_machines"]))

    neighborhood_data = {"h3_index": hexagons["h3_index"].values}

    for k in [1,2]:
        col = f"n_in_neighborhood_k{k}"
        counts_in_k = []
        for cell in hexagons["h3_index"]:
            # grid_disk zwraca cell + sąsiadów do k kroków
            disk = h3.grid_disk(cell, k)
            total = sum(machine_count_by_hex.get(c, 0) for c in disk)
            counts_in_k.append(total)
        neighborhood_data[col] = counts_in_k

    neighborhood_df = pd.DataFrame(neighborhood_data)

    neighborhood_df["is_isolated"] = neighborhood_df["n_in_neighborhood_k1"] == 0

    return neighborhood_df