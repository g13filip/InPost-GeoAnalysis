"""Mapy heksagonalne PyDeck — alternatywa dla Folium z WebGL renderingiem.

TODO: Zaimplementuj warstwy H3HexagonLayer dla dużych zbiorów danych,
gdzie Folium/GeoJSON byłby zbyt wolny (> 10k heksów).
"""
from __future__ import annotations

import pandas as pd


def hex_layer(df: pd.DataFrame, color_column: str) -> None:
    """H3HexagonLayer kolorowana wg wybranej kolumny metryk.

    Ref: https://deck.gl/docs/api-reference/geo-layers/h3-hexagon-layer
    """
    raise NotImplementedError
