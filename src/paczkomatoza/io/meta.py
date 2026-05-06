from datetime import datetime, timezone
from paczkomatoza.io.paths import hex_metrics_with_pop_path
import geopandas as gpd

def create_pop_metadata(city_slug: str, df: gpd.GeoDataFrame) -> dict:
    """Tworzy metadata dla siatki populacji: bbox, crs, n_rows, n_cols."""

    total_pop = df['population'].sum()
    served_pop = df[~df['is_unserved']]['population'].sum()

    meta = {
    "city_slug": city_slug,
    "resolution": 9,
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "source_hex_metrics": hex_metrics_with_pop_path(city_slug).name,
    "population_dataset": "Eurostat GEOSTAT census grid 2021 (TOT_P_2021)",
    "areal_weighting_crs": "CRS EPSG:3035",
    "city_total_population": float(total_pop),
    "city_served_population_500m": float(served_pop),
    "city_served_pct": round(served_pop / total_pop * 100, 2) if total_pop else 0,
    "unserved_threshold_population": 50,
    "unserved_threshold_distance_m": 500,
}
    return meta