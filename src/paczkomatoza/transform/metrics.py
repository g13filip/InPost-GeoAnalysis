"""Obliczanie metryk per heksagon: pokrycie, odległości, populacja, POI.
"""

from __future__ import annotations

import h3
import pandas as pd
import geopandas as gpd
from shapely.geometry import box

from paczkomatoza.transform import machines


def aggregate_machines_per_hex(df_machines: pd.DataFrame) -> pd.DataFrame:
    """Grupuje maszyny per h3_index, wylicza n_machines, n_*, weighted_score."""

    df_machines["is_parcel_locker"] = df_machines["type_primary"] == "parcel_locker"
    df_machines["is_pop"] = df_machines["type_primary"] == "pop"
    df_machines["is_outdoor"] = df_machines["location_type"] == "Outdoor"
    df_machines["is_indoor"] = df_machines["location_type"] == "Indoor"

    counts = df_machines.groupby("h3_index").agg(
    n_machines=("name", "count"),
    n_parcel_lockers=("is_parcel_locker", "sum"),
    n_pop=("is_pop", "sum"),
    n_outdoor=("is_outdoor", "sum"),
    n_indoor=("is_indoor", "sum"),
    n_operating=("is_operating", "sum"),
    ).reset_index()

    for col in counts.columns:
        if col != "h3_index":
            counts[col] = counts[col].astype(int)

    return counts


def assign_population_to_hexagons(
    df_hexes_with_metrics: pd.DataFrame, df_population_grid: gpd.GeoDataFrame
) -> pd.DataFrame:
    """Nakłada GEOSTAT 1km² na heksy metodą areal weighting.
    Uwaga: wymaga reprojekcji do EPSG:3035 przed overlay.
    """

    hex_3035 = df_hexes_with_metrics.to_crs("EPSG:3035").copy()
    hex_bbox= hex_3035.total_bounds
    buffer_m = 1000

    minx, miny, maxx, maxy = hex_bbox
    buffered_bbox = box(minx - buffer_m, miny - buffer_m, maxx + buffer_m, maxy + buffer_m)

    population_grid_local = df_population_grid[df_population_grid.intersects(buffered_bbox)].copy()

    # Spatial overlay — nakładamy siatkę populacji na heksy, liczymy przecięcie geometryczne

    overlay = gpd.overlay(
        hex_3035,
        population_grid_local[["GRD_ID", "TOT_P_2021", "geometry"]],
        how="intersection",
        keep_geom_type=True
    )

    # pole każdego kawałka nakładki oraz pole pełnego kwadratu siatki

    overlay["piece_are_m2"] = overlay.geometry.area
    grid_areas = population_grid_local.set_index("GRD_ID").geometry.area
    overlay["grid_area_m2"] = overlay["GRD_ID"].map(grid_areas)

    # waga to stosunek pola kawałka nakładki do pola pełnego kwadratu siatki

    overlay["weight"] = overlay["piece_are_m2"] / overlay["grid_area_m2"]
    overlay["piece_population"] = overlay["weight"] * overlay["TOT_P_2021"]

    # Jako ostatnie agregacja po heksagonach

    population_per_hex = (
        overlay.groupby("h3_index")["piece_population"]
        .sum()
        .round(1)
        .reset_index(name="population")
    )

    # Merge z głównym dataframe z metrykami heksagonów

    result = df_hexes_with_metrics.merge(population_per_hex, on="h3_index", how="left")
    result["population"] = result["population"].fillna(0).round(1)

    return result


def build_poi_features(
    df_pois: pd.DataFrame
) -> pd.DataFrame:
    """Pivot POI categories → kolumny n_shops, n_food, … + warianty _k1."""

    counts = (
        df_pois.groupby("h3_index")["category"]
        .value_counts()
        .unstack(fill_value=0)
        .reset_index()
    )

    counts.columns = [
        "h3_index" if c == "h3_index" else f"n_{c}" for c in counts.columns
    ]

    # Sumowanie wraz z sąsiadującymi heksagonami (k1)

    for col in ["shops", "food", "transport", "offices"]:
        col_n = f"n_{col}"
        col_k1 = f"{col}_k1"

        if col_n not in counts.columns:
            counts[col_n] = 0
            continue

        count_dict = dict(zip(counts["h3_index"], counts[col_n]))

        def neighbour_sum(cell: str) -> int:
            neighbours = h3.grid_disk(cell, 1)
            return sum(count_dict.get(neigh, 0) for neigh in neighbours)
        
        counts[col_k1] = counts["h3_index"].apply(neighbour_sum)

    return counts