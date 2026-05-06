"""Pobieranie granic administracyjnych miast z OSM/Nominatim.

TODO: Zaimplementuj w oparciu o notebook 04_city_boundary_to_hexagons.
Dwie wersje: fetch_boundary_osmnx (łatwa, wymaga scipy) i
fetch_boundary_nominatim (minimalne zależności, raw API).
"""
from __future__ import annotations

import osmnx as ox
import geopandas as gpd


def fetch_boundary_osmnx(city: str, country: str = "Poland") -> gpd.GeoDataFrame:
    """Pobiera granicę przez osmnx.geocode_to_gdf (wymaga osmnx + scipy)."""
    
    gdf = ox.geocode_to_gdf(f"{city}, {country}")

    return gdf.to_crs("EPSG:4326")