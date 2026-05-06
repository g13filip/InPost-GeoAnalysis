"""Zarządzanie ścieżkami do plików danych."""
from __future__ import annotations

from pathlib import Path

from paczkomatoza.config import DATA_ROOT


def raw_snapshot_path(city_slug: str) -> Path | None:
    """Najnowszy snapshot surowych danych API (lub None jeśli brak)."""
    candidates = sorted(
        (DATA_ROOT / "raw" / "inpost").glob(f"{city_slug}_*.parquet"),
        reverse=True,
    )
    return candidates[0] if candidates else None


def hex_metrics_path(city_slug: str) -> Path:
    return DATA_ROOT / "analytics" / "cities" / city_slug / "hex_metrics_res9.parquet"

def hex_metrics_path_full(city_slug: str) -> Path:
    return DATA_ROOT / "analytics" / "cities" / city_slug / "hex_metrics_res9_full.parquet"


def recommendations_path(city_slug: str) -> Path:
    return DATA_ROOT / "analytics" / "cities" / city_slug / "ml_recommendations.parquet"


def boundary_path(city_slug: str) -> Path:
    return DATA_ROOT / "processed" / "cities" / city_slug / "boundary.geojson"


def hexagons_path(city_slug: str, resolution: int = 9) -> Path:
    return DATA_ROOT / "processed" / "cities" / city_slug / f"hexagons_res{resolution}.parquet"


def hex_metrics_with_pop_path(city_slug: str) -> Path:
    return DATA_ROOT / "analytics" / "cities" / city_slug / "hex_metrics_res9_with_pop.parquet"


def pois_path(city_slug: str) -> Path:
    return DATA_ROOT / "external" / "osm" / f"{city_slug}_pois.parquet"


def model_path() -> Path:
    return DATA_ROOT / "models" / "xgb_machine_count.json"


# ── dane zewnętrzne ────────────────────────────────────────────────────────────

def poland_population_path() -> Path:
    return DATA_ROOT / "external" / "geostat" / "poland_pop_1km.parquet"


def europe_gpkg_path() -> Path:
    """Tymczasowy plik 1.7 GB — można usunąć po pierwszym filtrowaniu do Polski."""
    return DATA_ROOT / "external" / "geostat" / "grid_1km_surf.gpkg"


def overpass_cache_dir() -> Path:
    return DATA_ROOT / "external" / "osm" / "_osmnx_cache"
