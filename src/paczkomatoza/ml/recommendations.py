"""Residual scoring — generowanie rekomendacji lokalizacji paczkomatów.

Logika:
    1. Wczytanie zapisanego modelu XGBoost
    2. Wczytanie listy feature'ów z metadanych modelu.
    3. Filtrowanie hex z populacją >= MIN_POPULATION_FILTER (odsiewa parki/lasy).
    4. Predict: model szacuje ile maszyn "powinno" być w każdym hex.
    5. Residual = prediction - actual:
         > 0  → niedoinwestowane (kandydat na nową lokalizację)
         < 0  → nadinwestowane
         ≈ 0  → zgodne z wzorcem
    6. Filtruj kandydatów: residual > 0, n_machines == 0, population >= próg.
    7. Posortuj malejąco po residualu i zapisz.

Ref: notebook 11_ml_residual_model.ipynb
"""
from __future__ import annotations

import json

import geopandas as gpd
import numpy as np
import pandas as pd
import xgboost as xgb

from paczkomatoza.io.paths import model_path, recommendations_path

# ── progi (zgodne z notebookiem) ─────────────────────────────────────────────

MIN_POPULATION_FILTER: int = 10
"""Hex z mniejszą populacją są pomijane przy predykcji (parki, lasy, rzeki)."""

MIN_CANDIDATE_POPULATION: int = 100
"""Minimalna populacja hex żeby trafił do rekomendacji."""

MIN_RESIDUAL: float = 0.0
"""Minimalny residual żeby hex był uznany za kandydata."""

# Kolumny zapisywane w wynikowym pliku rekomendacji
_OUTPUT_COLUMNS = [
    "h3_index", "center_lat", "center_lng",
    "prediction", "residual", "n_machines",
    "population", "population_density_class",
    "n_shops", "n_food", "n_markets", "n_transport", "n_offices",
    "n_education", "n_healthcare",
    "google_maps_url", "geometry",
]


# ── ładowanie modelu

def load_model() -> xgb.XGBRegressor:
    """Wczytuje wytrenowany model XGBoost z dysku.

    Model jest wczytywany z pliku JSON — format XGBoost zachowuje
    architekturę drzew, hyperparametry i konfigurację kategorycznych.
    """
    path = model_path()
    if not path.exists():
        raise FileNotFoundError(
            f"Brak modelu pod: {path}\n"
            "Model nie jest trenowany przez pipeline — użyj "
            "notebook 11_ml_residual_model.ipynb, żeby go wytrenować i zapisać."
        )
    model = xgb.XGBRegressor()
    model.load_model(path)
    return model


def load_model_metadata() -> dict:
    """Wczytuje metadane modelu (lista feature'ów, hyperparametry, CV metryki)."""
    meta_path = model_path().with_suffix(".meta.json")
    if not meta_path.exists():
        raise FileNotFoundError(f"Brak metadanych modelu: {meta_path}")
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f)


def load_model_features() -> list[str]:
    """Zwraca listę feature'ów w kolejności w jakiej model był trenowany."""
    return load_model_metadata()["features"]


# ── predykcja i residual scoring 

def _prepare_features(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Przygotowuje DataFrame do predykcji.

    Obsługuje:
    - Brakujące kolumny (np. nowe miasto nie ma danego POI) → wypełnia zerami.
    - Kodowanie kategorycznych jako dtype 'category' (wymagane przez
      XGBoost enable_categorical=True).
    """
    df = df.copy()

    # Brakujące kolumny → 0 (nowe miasto może nie mieć wszystkich kategorii POI)
    for col in features:
        if col not in df.columns:
            df[col] = 0

    X = df[features].copy()

    # Kategoryczne muszą mieć dtype 'category' — XGBoost tego wymaga przy predykcji
    for col in X.select_dtypes(include="object").columns:
        X[col] = X[col].astype("category")

    return X


def build_recommendations(
    df: gpd.GeoDataFrame,
    min_population_filter: int = MIN_POPULATION_FILTER,
    min_candidate_population: int = MIN_CANDIDATE_POPULATION,
    min_residual: float = MIN_RESIDUAL,
) -> gpd.GeoDataFrame:
    """Generuje ranked listę kandydatów na nowe lokalizacje paczkomatów.

    Args:
        df:                        Pełna tabela metryk hex (hex_metrics_res9_full).
        min_population_filter:     Hex z mniejszą populacją są pomijane.
        min_candidate_population:  Minimalna populacja kandydata w rekomendacjach.
        min_residual:              Minimalny residual żeby hex trafił do wyników.

    Returns:
        GeoDataFrame posortowany malejąco po residualu — im wyższy,
        tym silniejsza rekomendacja ("tu powinno być więcej maszyn niż jest").
    """
    model = load_model()
    features = load_model_features()

    # ── filtr populacji
    df_filtered = df[df["population"] >= min_population_filter].copy()

    if df_filtered.empty:
        raise ValueError(
            f"Po filtrze populacji >= {min_population_filter} nie pozostały żadne hexagony. "
            "Sprawdź czy step_population i step_poi zostały uruchomione."
        )

    # ── predykcja
    X = _prepare_features(df_filtered, features)
    raw_predictions = model.predict(X)

    # Przycinamy ujemne do 0 — model nie zna ograniczenia nieujemności
    df_filtered["prediction"] = np.clip(raw_predictions, 0, None).round(2)

    # > 0 → tu "powinno być więcej niż jest" = kandydat na nową lokalizację
    df_filtered["residual"] = (
        df_filtered["prediction"] - df_filtered["n_machines"]
    ).round(2)

    # ── filtr kandydatów 
    candidates = df_filtered[
        (df_filtered["residual"] > min_residual)
        & (df_filtered["n_machines"] == 0)              # hex bez maszyny
        & (df_filtered["population"] >= min_candidate_population)
    ].copy()

    candidates = candidates.sort_values("residual", ascending=False)

    # Link do weryfikacji w Google Maps
    candidates["google_maps_url"] = (
        "https://www.google.com/maps?q="
        + candidates["center_lat"].astype(str)
        + ","
        + candidates["center_lng"].astype(str)
    )

    # ─ output
    keep = [c for c in _OUTPUT_COLUMNS if c in candidates.columns]

    if "geometry" in keep:
        return gpd.GeoDataFrame(candidates[keep], crs=df.crs)
    return candidates[keep]
