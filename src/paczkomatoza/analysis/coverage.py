"""Analiza pokrycia — białe plamy i obsługa populacji.

TODO: Zaimplementuj w oparciu o notebooki 05 i 08.
Kluczowe: klasyfikacja coverage_class, is_unserved, unserved_population.
"""
from __future__ import annotations

import pandas as pd
import numpy as np

from paczkomatoza.config import MIN_POPULATION, SERVED_RADIUS_M


def classify_coverage(n: int) -> str:
    """Dodaje coverage_class (none/sparse/moderate/dense) na podstawie n_machines."""

    if n == 0:
        return "none"
    if n == 1:
        return "sparse"
    if n <= 3:
        return "moderate"
    return "dense"
    

def flag_unserved(
    df: pd.DataFrame,
    radius_m: float = SERVED_RADIUS_M,
    min_population: int = MIN_POPULATION,
) -> pd.DataFrame:
    """Dodaje is_unserved, unserved_population, served_population.

    Heks jest nieobsłużony gdy: population >= min_population AND
    dist_to_nearest_m > radius_m
    """
    df["population_per_machine"] = np.where(
        df["n_machines"] > 0,
        (df["population"] / df["n_machines"]).round(1),
        np.nan
    )

    df['is_unserved'] = (
        (df['population'] >= min_population) 
        &   (df['dist_to_nearest_m'] > radius_m)
    )

    df['unserved_population'] = np.where(df["dist_to_nearest_m"] > radius_m, df['population'], 0).round(1)

    df['served_population'] = (df['population'] - df['unserved_population']).round(1)

    def classify_density(pop: float) -> str:
        if pop == 0:
            return "empty"
        if pop < 50:
            return "sparse"
        if pop < 500:
            return "moderate"
        if pop < 2000:
            return "dense"
        return "very_dense"
    
    df['population_density_class'] = df['population'].apply(classify_density)

    return df