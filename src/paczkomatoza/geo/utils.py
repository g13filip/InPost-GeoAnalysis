import geopandas as gpd
from pathlib import Path
from paczkomatoza.config import PROCESSED_DIR
from datetime import datetime, timezone
import json
import h3


def save_hex_to_parquet(gdfs: dict, city_slug: str) -> None:
    """Zapisuje GeoDataFrame z heksagonami do GeoParquet."""

    (PROCESSED_DIR / "cities" / city_slug).mkdir(parents=True, exist_ok=True)

    for resolution in gdfs.keys():
        res_gdf = gdfs[resolution]
        output_path = PROCESSED_DIR / "cities" / city_slug / f"hexagons_res{resolution}.parquet"
        res_gdf.to_parquet(output_path, compression="zstd")

    save_metadata(gdfs, city_slug)

def save_metadata(gdfs:dict, city_slug: str) -> None:
    """Zapisuje metadane o heksagonach do CSV."""

    meta = {
    "city_slug": city_slug,
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "boundary_source": "osmnx",
    "resolutions": [
        {
            "resolution": res,
            "n_hexagons": len(gdf),
            "avg_hex_area_km2": h3.average_hexagon_area(res, unit="km^2"),
            "approx_total_area_km2": len(gdf) * h3.average_hexagon_area(res, unit="km^2"),
            "file": f"hexagons_res{res}.parquet",
        }for res, gdf in gdfs.items()]
}
    output_path = PROCESSED_DIR / "cities" / city_slug / f"hexagons.meta.json"
    output_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False))

def save_boundary(boundary: gpd.GeoDataFrame, city_slug: str) -> None:
    """Zapisuje granicę miasta do GeoParquet."""

    city_dir = PROCESSED_DIR / "cities" / city_slug
    city_dir.mkdir(parents=True, exist_ok=True)
    output_path = city_dir / f"boundary.geojson"

    boundary.to_file(output_path, driver="GeoJSON")

