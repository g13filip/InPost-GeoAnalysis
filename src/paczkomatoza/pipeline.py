"""Orkiestracja pipeline'u dla nowego miasta.

Konwencja parametrów kroków:
    city_slug  — identyfikator do ścieżek plików (np. "lodz")
    city_name  — oryginalna nazwa przekazywana do API i OSM (np. "Łódź")
    opts       — PipelineOptions: flagi force_refresh i cache management
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Callable

import geopandas as gpd
import pandas as pd

from paczkomatoza.ingest.exceptions import CityAlreadyCachedException, CityNotFoundInAPIException
from paczkomatoza.ingest.geostat_client import load_poland_population
from paczkomatoza.ingest.inpost_client import fetch_all_pages_for_city
from paczkomatoza.ingest.osm_client import fetch_pois_for_city
from paczkomatoza.ingest.utils import does_city_exist_in_api, is_cached, save_city_data_parquet
from paczkomatoza.geo.boundaries import fetch_boundary_osmnx
from paczkomatoza.geo.hex_grid import cells_to_gdf, polygon_to_cells
from paczkomatoza.geo.utils import save_boundary, save_hex_to_parquet
from paczkomatoza.transform.machines import assign_h3_index
from paczkomatoza.transform.metrics import aggregate_machines_per_hex, assign_population_to_hexagons, build_poi_features
from paczkomatoza.transform.poi import assign_h3_to_pois
from paczkomatoza.analysis.distances import compute_distances, neighborhood_disk
from paczkomatoza.analysis.scoring import compute_weighted_score
from paczkomatoza.analysis.coverage import flag_unserved
from paczkomatoza.transform.utils import create_metadata, merge_dfs, merge_full_metrics
from paczkomatoza.io.parquet_io import save_parquet
from paczkomatoza.io.paths import hex_metrics_path, hex_metrics_with_pop_path, hexagons_path, hex_metrics_path_full, recommendations_path
from paczkomatoza.io.meta import create_pop_metadata
from paczkomatoza.ml.recommendations import build_recommendations


# ── opcje pipeline'u ─────────────────────────────────────────────────────────

@dataclass
class PipelineOptions:
    """Flagi sterujące zachowaniem pipeline'u.

    Domyślnie: używaj cache, nie czyść niczego.
    """
    force_refresh_population: bool = False
    """Ignoruje cached poland_pop_1km.parquet i pobiera GEOSTAT od nowa."""

    force_refresh_pois: bool = False
    """Ignoruje cached {city}_pois.parquet i pobiera POI z OSM od nowa."""

    clear_overpass_cache: bool = False
    """Czyści wewnętrzny cache Overpass (JSON pliki osmnx) przed pobraniem POI."""

    delete_gpkg_after_filter: bool = True
    """Usuwa tymczasowy .gpkg (1.7 GB) po filtrowaniu do Polski."""


# ── krok ─────────────────────────────────────────────────────────────────────

@dataclass
class PipelineStep:
    name: str
    description: str
    fn: Callable[[str, str, PipelineOptions], None]
    done: bool = False
    error: str | None = None


# ── implementacje kroków ──────────────────────────────────────────────────────

def step_fetch(city_slug: str, city_name: str, opts: PipelineOptions = PipelineOptions()) -> None:
    """Pobieranie paczkomatów z API InPost i zapisz snapshot .parquet."""
    if is_cached(city_name):
        raise CityAlreadyCachedException(f"Dane dla {city_name} są już zcache'owane.")

    if not does_city_exist_in_api(city_name):
        raise CityNotFoundInAPIException(
            f"API InPost nie zwraca danych dla miasta '{city_name}'. "
            "Sprawdź pisownię (API wymaga pełnej nazwy, np. 'Łódź', nie 'lodz')."
        )

    points = asyncio.run(fetch_all_pages_for_city(city_name))
    save_city_data_parquet(city_slug, points)


def step_boundary(city_slug: str, city_name: str, opts: PipelineOptions = PipelineOptions()) -> None:
    """pobieranie granic miasta i generowanie siatki heksagonów H3."""
    boundary = fetch_boundary_osmnx(city_name, "Poland")
    save_boundary(boundary, city_slug)

    gdfs_by_resolution: dict[int, gpd.GeoDataFrame] = {}
    for resolution in [8, 9]:
        cells = polygon_to_cells(boundary.geometry.iloc[0], resolution=resolution)
        gdfs_by_resolution[resolution] = cells_to_gdf(cells, resolution=resolution)

    save_hex_to_parquet(gdfs_by_resolution, city_slug)


def step_metrics(city_slug: str, city_name: str, opts: PipelineOptions = PipelineOptions()) -> None:
    """Przypisanie paczkomatów do heksów, liczenie metryki odległości i pokrycia."""
    hexagons = pd.read_parquet(hexagons_path(city_slug))
    machines = assign_h3_index(city_slug, resolution=9)

    counts = aggregate_machines_per_hex(machines)
    scores = compute_weighted_score(machines)
    distances_df = compute_distances(hexagons, machines)
    neighborhood_df = neighborhood_disk(hexagons, counts)

    result_df = merge_dfs(city_slug, counts, scores, distances_df, neighborhood_df)
    metadata = create_metadata(city_slug, result_df)
    save_parquet(result_df, hex_metrics_path(city_slug), metadata=metadata)


def step_population(city_slug: str, city_name: str, opts: PipelineOptions = PipelineOptions()) -> None:
    """Nałożenie danych populacyjnych GEOSTAT na siatkę heksów.
    Fetching: pobieranie siatki populacji Polski (z cache lub Eurostat).
    """
    # ── fetching 
    pop_grid = load_poland_population(
        force=opts.force_refresh_population,
        delete_gpkg_after=opts.delete_gpkg_after_filter,
    )

    hex_metrics = gpd.read_parquet(hex_metrics_path(city_slug))

    metrics_with_pop = assign_population_to_hexagons(hex_metrics, pop_grid)

    hex_popmetrics = flag_unserved(metrics_with_pop)

    metadata = create_pop_metadata(city_slug, hex_popmetrics)
    save_parquet(hex_popmetrics, hex_metrics_with_pop_path(city_slug), metadata=metadata)


def step_poi(city_slug: str, city_name: str, opts: PipelineOptions = PipelineOptions()) -> None:
    """Pobranie punktów POI z OpenStreetMap i dołączenie cech do heksów."""
    # ── fetching (zaimplementowane) ───────────────────────────────────────────
    pois = fetch_pois_for_city(
        city_slug,
        force=opts.force_refresh_pois,
        clear_overpass=opts.clear_overpass_cache,
    )

    h3_poi = assign_h3_to_pois(pois)

    counts = build_poi_features(h3_poi)
    last_metrics = pd.read_parquet(hex_metrics_with_pop_path(city_slug)) 
    full_metrics = merge_full_metrics(last_metrics, counts)

    save_parquet(full_metrics, hex_metrics_path_full(city_slug), metadata=None)


def step_ml(city_slug: str, city_name: str, opts: PipelineOptions = PipelineOptions()) -> None:
    """Zastosowanie modelu XGBoost do wygenerowania rekomendacji lokalizacji dla nowych paczkomatów."""
    full_metrics = gpd.read_parquet(hex_metrics_path_full(city_slug))

    # Generuj rekomendacje (predykcja + residual scoring + filtrowanie kandydatów)
    recommendations = build_recommendations(full_metrics)

    # Zapisz — GeoDataFrame z geometrią, więc save_parquet zapisze jako GeoParquet
    out_path = recommendations_path(city_slug)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    recommendations.to_parquet(out_path, compression="zstd")


# ── rejestr kroków ────────────────────────────────────────────────────────────

PIPELINE_STEPS: list[PipelineStep] = [
    PipelineStep("Pobieranie danych API",     "Fetch paczkomatów z InPost API",             step_fetch),
    PipelineStep("Granica + siatka H3",       "Boundary OSMnx → hexagons res 8 & 9",        step_boundary),
    PipelineStep("Metryki paczkomat → hex",   "Przypisanie maszyn, odległości, klasy",       step_metrics),
    PipelineStep("Dane populacyjne",          "GEOSTAT 2021 — areal weighting",              step_population),
    PipelineStep("Cechy POI (OSM)",           "Sklepy, transport, gastronomia, …",           step_poi),
    PipelineStep("Rekomendacje ML (XGBoost)", "Residual scoring → kandydaci na lokalizacje", step_ml),
]


# ── runner ────────────────────────────────────────────────────────────────────

def run_pipeline(
    city_slug: str,
    city_name: str,
    on_step_start: Callable[[str], None] | None = None,
    on_step_done: Callable[[str], None] | None = None,
    on_step_error: Callable[[str, str], None] | None = None,
    on_city_cached: Callable[[str], None] | None = None,
    on_city_not_found: Callable[[str, str], None] | None = None,
    opts: PipelineOptions = PipelineOptions(),
) -> bool:
    """Uruchamia kolejno wszystkie kroki pipeline'u dla danego miasta.

    Args:
        city_slug:          identyfikator plików (np. "lodz")
        city_name:          pełna nazwa do API i OSM (np. "Łódź")
        opts:               opcje cache i force_refresh

    Callbacki:
        on_step_start(name)            — przed uruchomieniem kroku
        on_step_done(name)             — po sukcesie kroku
        on_step_error(name, msg)       — błąd techniczny (zatrzymuje pipeline)
        on_city_cached(name)           — dane już istnieją (nie jest błędem)
        on_city_not_found(name, msg)   — miasto nieznane w API InPost

    Zwraca True jeśli dane są dostępne (sukces lub już zcache'owane).
    Zwraca False przy błędzie.
    """
    for step in PIPELINE_STEPS:
        if on_step_start:
            on_step_start(step.name)
        try:
            step.fn(city_slug, city_name, opts)
            step.done = True
            if on_step_done:
                on_step_done(step.name)
        except CityAlreadyCachedException:
            if on_city_cached:
                on_city_cached(step.name)
            return True
        except CityNotFoundInAPIException as exc:
            step.error = str(exc)
            if on_city_not_found:
                on_city_not_found(step.name, step.error)
            elif on_step_error:
                on_step_error(step.name, step.error)
            return False
        except NotImplementedError as exc:
            step.error = str(exc)
            if on_step_error:
                on_step_error(step.name, step.error)
            return False
        except Exception as exc:
            step.error = str(exc)
            if on_step_error:
                on_step_error(step.name, step.error)
            return False
    return True
