"""Generowanie siatki heksagonów H3 dla obszaru miasta.

TODO: Zaimplementuj w oparciu o notebook 04_city_boundary_to_hexagons.
Kluczowe: h3.h3shape_to_cells, GeoDataFrame z geometrią granic heksów,
zapisywanie do GeoParquet z metadanymi.
"""
from __future__ import annotations

import geopandas as gpd
import h3
from shapely import MultiPolygon, Polygon


def polygon_to_cells(boundary: Polygon | MultiPolygon, resolution: int) -> list[str]:
    """Zwraca listę indeksów H3 pokrywających podany wielokąt."""

    if isinstance(boundary, Polygon):
        polygons = [boundary]
    elif isinstance(boundary, MultiPolygon):
        polygons = list(boundary.geoms)
    else:
        raise ValueError("Oczekiwano Polygon lub MultiPolygon")

    all_cells = set()

    for p in polygons:
        h3_shape = h3.geo_to_h3shape(p)
        cells = h3.h3shape_to_cells(h3_shape, resolution)
        all_cells.update(cells)

    return sorted(all_cells)

def cell_to_polygon(cell: str) -> Polygon:
    """H3 cell → shapely.Polygon (z odwróceniem lat/lng → lng/lat)."""
    boundary = h3.cell_to_boundary(cell)
    return Polygon([(lng, lat) for lat, lng in boundary])


def cells_to_gdf(cells: list[str], resolution: int) -> gpd.GeoDataFrame:
    """Buduje GeoDataFrame: h3_index, center_lat/lng, parent_res7/8, geometry."""
    rows = []
    for c in cells:
        center_lat, center_lng = h3.cell_to_latlng(c)
        rows.append({
            "h3_index": c,
            "resolution": resolution,
            "center_lat": center_lat,
            "center_lng": center_lng,
            "parent_res7": h3.cell_to_parent(c, 7),
            "parent_res8": h3.cell_to_parent(c, 8),
            "geometry": cell_to_polygon(c),
        })
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
