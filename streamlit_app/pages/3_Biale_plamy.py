"""Strona 3 — Białe plamy: obszary nieobsłużone i rekomendacje ML."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "streamlit_app"))

import pandas as pd
import streamlit as st

from components.city_selector import render_sidebar
from components.map_renderer import machine_legend_caption, machines_checkbox, render_map
from paczkomatoza.io.parquet_io import (
    compute_kpis,
    load_hex_metrics,
    load_raw_machines,
    load_recommendations,
)
from paczkomatoza.viz.folium_maps import recommendations_map, unserved_map

st.set_page_config(page_title="Białe plamy · Paczkomatoza", page_icon="🔍", layout="wide")

with st.sidebar:
    city_slug, city_name, data_ready = render_sidebar()

if not data_ready:
    st.title(f"🔍 {city_name}")
    st.info("Brak danych. Uruchom pipeline ze strony głównej.")
    st.stop()

@st.cache_data(show_spinner=False)
def _load(slug: str):
    return load_hex_metrics(slug), load_recommendations(slug), load_raw_machines(slug)

with st.spinner(f"Ładowanie danych dla {city_name}…"):
    df, df_rec, df_machines = _load(city_slug)

if df is None:
    st.error("Nie udało się załadować hex_metrics_res9_full.parquet.")
    st.stop()

kpis = compute_kpis(df)
st.title(f"🔍 {city_name} — białe plamy i rekomendacje")

tab_unserved, tab_recs = st.tabs(["🔴 Obszary nieobsłużone", "🤖 Rekomendacje ML"])

# ── nieobsłużone ──────────────────────────────────────────────────────────────

with tab_unserved:
    n = kpis["unserved_hexes"]
    st.subheader(f"Obszary nieobsłużone — {n} heksagonów")
    st.caption(
        "Czerwone heksagony: populacja ≥ 50 osób i odległość do paczkomatu > 500 m. "
        "Tło pokazuje gęstość zaludnienia."
    )

    show_m = machines_checkbox("Pokaż lokalizacje paczkomatów", key="machines_unserved")
    machines_layer = df_machines if show_m else None

    with st.spinner("Renderowanie mapy…"):
        render_map(unserved_map(df, df_machines=machines_layer), key="unserved")

    machine_legend_caption(machines_layer)

# ── rekomendacje ML ───────────────────────────────────────────────────────────

with tab_recs:
    if df_rec is None or df_rec.empty:
        st.info("Brak rekomendacji ML. Uruchom notebook 11 (krok ML w pipeline).")
    else:
        n_rec = len(df_rec)
        st.subheader(f"Rekomendacje ML — {n_rec} kandydatów")
        st.caption(
            "**Residual** = ile maszyn brakuje wg modelu XGBoost. "
            "Im wyższy, tym silniejsza rekomendacja lokalizacji."
        )

        show_m = machines_checkbox("Pokaż lokalizacje paczkomatów", key="machines_recs")
        machines_layer = df_machines if show_m else None

        col_map, col_table = st.columns([3, 2])

        with col_map:
            with st.spinner("Renderowanie mapy…"):
                render_map(
                    recommendations_map(df_rec, df_machines=machines_layer),
                    key="recommendations",
                )
            machine_legend_caption(machines_layer)

        with col_table:
            st.markdown("**Top kandydaci**")
            DISPLAY = [
                "center_lat", "center_lng", "residual", "prediction",
                "n_machines", "population", "n_shops", "n_food",
                "population_density_class", "google_maps_url",
            ]
            cols = [c for c in DISPLAY if c in df_rec.columns]
            top = (
                df_rec[cols]
                .sort_values("residual", ascending=False)
                .head(50)
                .reset_index(drop=True)
            )
            top.index += 1

            if "google_maps_url" in top.columns:
                top["google_maps_url"] = top["google_maps_url"].apply(
                    lambda u: f'<a href="{u}" target="_blank">🗺</a>' if pd.notna(u) else ""
                )

            st.write(top.to_html(escape=False, index=True), unsafe_allow_html=True)
