import pandas as pd
import geopandas as gpd
import h3

def assign_h3_to_pois(df_pois: gpd.GeoDataFrame
) -> pd.DataFrame:
    """Przypisuje każdemu POI indeks H3 na podstawie jego geometrii."""

    df = df_pois.copy()
    df["longitude"] = df.geometry.x
    df["latitude"] = df.geometry.y

    df = df.dropna(subset=["latitude", "longitude"])

    df["h3_index"] = [
        h3.latlng_to_cell(lat, lng, 9)
        for lat, lng in zip(df["latitude"], df["longitude"])
    ]
    return df.drop(columns=["geometry"])