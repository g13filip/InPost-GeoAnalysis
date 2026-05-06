import pandas as pd

from paczkomatoza.analysis.coverage import classify_coverage
from paczkomatoza.analysis.scoring import classify_accessibility
from paczkomatoza.io.paths import hexagons_path

from datetime import datetime, timezone

def merge_dfs(city_slug: str,
              counts: pd.DataFrame,
              scores: pd.DataFrame,
              distances_df: pd.DataFrame,
              neighborhood_df: pd.DataFrame) -> pd.DataFrame:
    """Łączy counts, machines, distances_df, neighborhood_df w jeden df na poziomie heksagonów."""

    hexagons = pd.read_parquet(hexagons_path(city_slug))

    metrics = hexagons.merge(counts, on="h3_index", how="left")
    metrics = metrics.merge(scores, on="h3_index", how="left")
    metrics = metrics.merge(distances_df, on="h3_index", how="left")
    metrics = metrics.merge(neighborhood_df, on="h3_index", how="left")

    # Wypełnienie zerami dla heksagonów bez punktów
    count_cols = [c for c in metrics.columns if c.startswith("n_")]
    metrics[count_cols] = metrics[count_cols].fillna(0).astype(int)
    metrics["weighted_score"] = metrics["weighted_score"].fillna(0.0)

    metrics["coverage_class"] = metrics["n_machines"].apply(classify_coverage)
    metrics["accessibility_class"] = metrics["dist_to_nearest_m"].apply(classify_accessibility)

    # is_isolated mógł zostać nullem dla hex bez wpisu — naprawiamy
    metrics["is_isolated"] = metrics["is_isolated"].fillna(True).astype(bool)

    return metrics

def create_metadata(city_slug, df: pd.DataFrame) -> dict:
    """Tworzy słownik z metadanymi do zapisania w sidecar JSON."""
    metadata = {
    "city_slug": city_slug,
    "resolution": 9,
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "source_hexagons": str(hexagons_path(city_slug)),
    "n_hexagons_total": len(df),
    "n_hexagons_with_machines": int((df["n_machines"] > 0).sum()),
    "n_machines_total": int(df["n_machines"].sum()),
    "buffer_radii_m": [500,1000],
    "neighborhood_k": [1,2],
}
    return metadata

def merge_full_metrics(
                       df_with_metrics: pd.DataFrame,
                       df_poi_features: pd.DataFrame) -> pd.DataFrame:
    """Łączy df_with_metrics z df_poi_features (na podstawie h3_index)."""

    full_df = df_with_metrics.merge(df_poi_features, on="h3_index", how="left")
    
    poi_cols = [c for c in df_poi_features.columns if c != "h3_index"]
    full_df[poi_cols] = full_df[poi_cols].fillna(0).astype(int)

    return full_df
