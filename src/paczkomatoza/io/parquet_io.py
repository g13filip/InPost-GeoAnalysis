"""Helpery do wczytywania i zapisywania plików Parquet z walidacją schematu."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import geopandas as gpd

from paczkomatoza.config import DATA_ROOT
from paczkomatoza.io.paths import (
    boundary_path,
    hex_metrics_path,
    hex_metrics_path_full,
    raw_snapshot_path,
    recommendations_path,
)


# ── wczytywanie ───────────────────────────────────────────────────────────────

def load_hex_metrics(city_slug: str) -> pd.DataFrame | None:
    """Wczytuje metryki heksagonów.

    Preferuje pełny plik (po populacji + POI). Jeśli nie istnieje,
    cofa się do pliku po kroku 3 (bez populacji).
    """
    full = hex_metrics_path_full(city_slug)
    if full.exists():
        return pd.read_parquet(full)
    basic = hex_metrics_path(city_slug)
    return pd.read_parquet(basic) if basic.exists() else None


def load_recommendations(city_slug: str) -> pd.DataFrame | None:
    path = recommendations_path(city_slug)
    return pd.read_parquet(path) if path.exists() else None


def load_raw_machines(city_slug: str) -> pd.DataFrame | None:
    path = raw_snapshot_path(city_slug)
    return pd.read_parquet(path) if (path and path.exists()) else None


def load_boundary_geojson(city_slug: str) -> str | None:
    path = boundary_path(city_slug)
    return path.read_text(encoding="utf-8") if path.exists() else None


def available_cities(known_cities: dict[str, str] | None = None) -> list[str]:
    """Odkrywa miasta z pełnymi danymi analitycznymi na dysku.

    Skanuje data/analytics/cities/ w poszukiwaniu hex_metrics_res9_full.parquet.
    Nie ogranicza się do known_cities — wykrywa też nowe miasta z pipeline'u.

    Args:
        known_cities: ignorowany (zachowany dla wstecznej kompatybilności).
    """
    analytics_dir = DATA_ROOT / "analytics" / "cities"
    if not analytics_dir.exists():
        return []
    return sorted(
        p.parent.name
        for p in analytics_dir.glob("*/hex_metrics_res9_full.parquet")
    )


# ── zapisywanie ───────────────────────────────────────────────────────────────

def save_parquet(df: pd.DataFrame, path: Path, metadata: dict | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(df, gpd.GeoDataFrame):
        df.to_parquet(path)                          # GeoDataFrame → GeoParquet natywnie
    elif "geometry" in df.columns and df["geometry"].dtype == object:
        gdf = gpd.GeoDataFrame(                      # WKB bytes → konwersja → GeoParquet
            df,
            geometry=gpd.GeoSeries.from_wkb(df["geometry"]),
            crs="EPSG:4326",
        )
        gdf.to_parquet(path)
    else:
        df.to_parquet(path, index=False)             # zwykły DataFrame

    if metadata is not None:
        meta_path = path.with_suffix(".meta.json")
        meta_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")


# ── KPI ───────────────────────────────────────────────────────────────────────

def compute_kpis(df: pd.DataFrame) -> dict:
    """Wylicza KPI do wyświetlenia w nagłówku aplikacji."""
    total_machines = int(df["n_machines"].sum())
    total_population = df["population"].sum()
    served_pop = df["served_population"].sum()
    unserved_pop = df["unserved_population"].sum()
    unserved_hexes = int(df["is_unserved"].sum())

    pct_served = (served_pop / total_population * 100) if total_population > 0 else 0.0
    avg_dist = df.loc[df["n_machines"] == 0, "dist_to_nearest_m"].median()

    return {
        "total_machines": total_machines,
        "total_population": int(total_population),
        "pct_served": round(pct_served, 1),
        "unserved_hexes": unserved_hexes,
        "unserved_population": int(unserved_pop),
        "median_dist_unserved_m": int(avg_dist) if not pd.isna(avg_dist) else 0,
    }
