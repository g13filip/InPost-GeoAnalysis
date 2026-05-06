"""Pobieranie i cache'owanie POI z OpenStreetMap przez OSMnx / Overpass API.

Cache dwupoziomowy:
    1. {city_slug}_pois.parquet istnieje → wczytaj
    2. Brak cache                        → pobierz przez osmnx → zapisz

Cache Overpass (wewnętrzny osmnx):
    Hashed JSON pliki w _osmnx_cache/ — przyspieszają ponowne odpytania
    tego samego obszaru. Można wyczyścić clear_overpass_cache().

Ref: notebook 10_external_features.ipynb
"""
from __future__ import annotations

import shutil

import geopandas as gpd
import pandas as pd

from paczkomatoza.io.paths import boundary_path, overpass_cache_dir, pois_path

# ── definicje kategorii ───────────────────────────────────────────────────────

POI_CATEGORIES: dict[str, dict] = {
    "shops":      {"shop": True},
    "food":       {"amenity": ["restaurant", "cafe", "fast_food", "bar", "pub"]},
    "markets":    {"amenity": ["marketplace"], "shop": ["mall", "supermarket"]},
    "transport":  {"highway": ["bus_stop"], "public_transport": ["stop_position", "platform"]},
    "rail":       {"railway": ["station", "halt", "tram_stop", "subway_entrance"]},
    "education":  {"amenity": ["school", "university", "college", "kindergarten"]},
    "offices":    {"office": True},
    "healthcare": {"amenity": ["hospital", "clinic", "doctors", "pharmacy"]},
    "buildings":  {"building": True},
}

# Dla tych kategorii obliczamy też sąsiedztwo k=1 w transform/poi_features.py
NEIGHBORHOOD_CATEGORIES: list[str] = ["shops", "food", "transport", "offices"]

# Bufor wokół granicy miasta przy pobieraniu POI (metry, w EPSG:3035)
BOUNDARY_BUFFER_M = 500


# ── główne API ────────────────────────────────────────────────────────────────

def fetch_pois_for_city(
    city_slug: str,
    force: bool = False,
    clear_overpass: bool = False,
) -> gpd.GeoDataFrame:
    """Pobiera POI dla miasta, korzystając z cache.

    Args:
        city_slug:      Slug miasta (np. "krakow").
        force:          Ignoruje cache per-miasto i pobiera ponownie z OSM.
        clear_overpass: Czyści cache Overpass przed pobraniem (świeże dane z OSM).

    Returns:
        GeoDataFrame z kolumnami [category, geometry] i punktowymi centroidami.
        Geometry w EPSG:4326.
    """
    import osmnx as ox

    cache = pois_path(city_slug)

    if clear_overpass:
        _clear_overpass_cache()

    if not force and cache.exists():
        return gpd.read_parquet(cache)

    _configure_osmnx()

    boundary_gdf = _load_boundary(city_slug)
    polygon = _buffer_boundary(boundary_gdf, BOUNDARY_BUFFER_M)

    all_pois: list[gpd.GeoDataFrame] = []

    for category, tags in POI_CATEGORIES.items():
        try:
            gdf = ox.features_from_polygon(polygon, tags=tags)
        except Exception:
            continue

        if gdf.empty:
            continue

        gdf = gdf.reset_index()
        gdf["category"] = category
        gdf["geometry"] = gdf.geometry.centroid

        # Zachowujemy tylko niezbędne kolumny
        keep = ["category", "geometry"]
        all_pois.append(gdf[keep])

    if not all_pois:
        raise RuntimeError(
            f"Nie pobrano żadnych POI dla '{city_slug}'. "
            "Sprawdź połączenie z Overpass API."
        )

    combined = gpd.GeoDataFrame(
        pd.concat(all_pois, ignore_index=True),
        crs="EPSG:4326",
    )

    cache.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(cache, compression="zstd")
    return combined


def clear_city_pois_cache(city_slug: str) -> None:
    """Usuwa cache POI per miasto. Kolejne fetch_pois_for_city pobierze dane z OSM."""
    path = pois_path(city_slug)
    if path.exists():
        path.unlink()


def clear_overpass_cache() -> None:
    """Usuwa wszystkie pliki cache Overpass (hashed JSON z osmnx).
    Użyj gdy chcesz wymusić świeże dane z OpenStreetMap.
    Nie usuwa per-city parquet — tylko wewnętrzny cache zapytań.
    """
    _clear_overpass_cache()


def pois_cache_exists(city_slug: str) -> bool:
    return pois_path(city_slug).exists()


# ── wewnętrzne ────────────────────────────────────────────────────────────────

def _configure_osmnx() -> None:
    import osmnx as ox
    cache_dir = overpass_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    ox.settings.cache_folder = str(cache_dir)
    ox.settings.use_cache = True
    ox.settings.log_console = False
    ox.settings.requests_timeout = 300


def _load_boundary(city_slug: str) -> gpd.GeoDataFrame:
    path = boundary_path(city_slug)
    if not path.exists():
        raise FileNotFoundError(
            f"Brak granicy dla '{city_slug}' ({path}). "
            "Najpierw uruchom step_boundary."
        )
    return gpd.read_file(path)


def _buffer_boundary(boundary_gdf: gpd.GeoDataFrame, buffer_m: int):
    """Bufor w EPSG:3035 (metryczna) → z powrotem do WGS84.
    Shapely union_all daje jeden Polygon/MultiPolygon do zapytania Overpass.
    """
    buffered = (
        boundary_gdf
        .to_crs("EPSG:3035")
        .buffer(buffer_m)
        .to_crs("EPSG:4326")
        .union_all()
    )
    return buffered


def _clear_overpass_cache() -> None:
    cache_dir = overpass_cache_dir()
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
