"""Pobieranie i cache'owanie danych populacyjnych GEOSTAT 2021.

Dane: Eurostat GISCO grid 1km² — populacja rezydentna per komórka dla całej Europy.
Cache trójpoziomowy:
    1. poland_pop_1km.parquet istnieje → wczytaj (99% przypadków po pierwszym run)
    2. grid_1km_surf.gpkg istnieje    → filtruj do Polski → zapisz parquet
    3. Nic nie ma                     → pobierz .gpkg (1.7 GB) → filtruj → zapisz
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import geopandas as gpd
import httpx
from shapely.geometry import box

from paczkomatoza.io.paths import europe_gpkg_path, poland_population_path

GEOSTAT_URL = "https://gisco-services.ec.europa.eu/grid/grid_1km_surf.gpkg"

# Bbox Polski z zapasem w EPSG:4326
POLAND_BBOX_4326 = (13.5, 48.9, 24.5, 55.0)

GEOSTAT_CRS = "EPSG:3035" 
WGS84 = "EPSG:4326"

# Kolumny które zachowujemy po filtrowaniu
KEEP_COLUMNS = ["GRD_ID", "TOT_P_2021", "geometry"]


# ── główne API ────────────────────────────────────────────────────────────────

def load_poland_population(
    force: bool = False,
    delete_gpkg_after: bool = True,
    on_progress: Callable[[float, float], None] | None = None,
) -> gpd.GeoDataFrame:
    """Wczytuje siatkę populacji Polski z cache lub pobiera z Eurostat.

    Args:
        force:            Jeśli True, ignoruje cache i pobiera ponownie.
        delete_gpkg_after: Usuwa tymczasowy .gpkg (1.7 GB) po filtrowaniu.
        on_progress:      Callback(downloaded_mb, total_mb) — wywoływany co chunk
                          podczas pobierania. Przydatny do aktualizacji st.progress().

    Returns:
        GeoDataFrame z kolumnami [GRD_ID, TOT_P_2021, geometry] w EPSG:3035.
    """
    cache = poland_population_path()

    if not force and cache.exists():
        return gpd.read_parquet(cache)

    gpkg = europe_gpkg_path()
    if not force and gpkg.exists():
        return _filter_and_cache(gpkg, cache, delete_gpkg_after)

    # Pobierz pełny plik Europy
    cache.parent.mkdir(parents=True, exist_ok=True)
    gpkg.parent.mkdir(parents=True, exist_ok=True)
    _download(GEOSTAT_URL, gpkg, on_progress)

    return _filter_and_cache(gpkg, cache, delete_gpkg_after)


def clear_population_cache() -> None:
    """Usuwa zapisany cache populacji. Kolejne wywołanie load_poland_population
    spowoduje ponowne pobranie z Eurostat."""
    path = poland_population_path()
    if path.exists():
        path.unlink()


def population_cache_exists() -> bool:
    return poland_population_path().exists()


# ── wewnętrzne ────────────────────────────────────────────────────────────────

def _download(
    url: str,
    dest: Path,
    on_progress: Callable[[float, float], None] | None,
    chunk_size: int = 1024 * 1024,
) -> None:
    """Pobiera plik strumieniowo. Pisze do pliku .part, przemianowuje po sukcesie."""
    tmp = dest.with_suffix(dest.suffix + ".part")

    with httpx.stream("GET", url, follow_redirects=True, timeout=600.0) as response:
        response.raise_for_status()
        total_bytes = int(response.headers.get("content-length", 0))
        total_mb = total_bytes / 1024 ** 2
        downloaded = 0

        with open(tmp, "wb") as f:
            for chunk in response.iter_bytes(chunk_size=chunk_size):
                f.write(chunk)
                downloaded += len(chunk)
                if on_progress and total_bytes:
                    on_progress(downloaded / 1024 ** 2, total_mb)

    tmp.rename(dest)


def _filter_and_cache(
    gpkg: Path,
    output: Path,
    delete_gpkg: bool,
) -> gpd.GeoDataFrame:
    """Filtruje plik Europy do bbox Polski i zapisuje jako Parquet."""
    # Bbox w EPSG:3035 (natywny CRS pliku)
    bbox_wgs = gpd.GeoSeries([box(*POLAND_BBOX_4326)], crs=WGS84)
    bbox_3035 = tuple(bbox_wgs.to_crs(GEOSTAT_CRS).total_bounds)

    gdf = gpd.read_file(gpkg, bbox=bbox_3035)

    available = [c for c in KEEP_COLUMNS if c in gdf.columns]
    if "TOT_P_2021" not in available:
        # Fallback — czasem kolumna ma inną nazwę
        pop_cols = [c for c in gdf.columns if "TOT_P" in c.upper()]
        if pop_cols:
            available.append(pop_cols[0])

    gdf = gdf[available].copy()
    output.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(output, compression="zstd")

    if delete_gpkg and gpkg.exists():
        gpkg.unlink()

    return gdf
