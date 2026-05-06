"""Strona 1 — Mapa miasta: pokrycie i dostępność paczkomatów."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "streamlit_app"))

import streamlit as st

from components.city_selector import render_sidebar
from components.map_renderer import machines_checkbox, machine_legend_caption, render_map
from paczkomatoza.io.parquet_io import load_hex_metrics, load_raw_machines
from paczkomatoza.viz.folium_maps import accessibility_map, coverage_map

st.set_page_config(page_title="Mapa miasta · Paczkomatoza", page_icon="🗺️", layout="wide")

with st.sidebar:
    city_slug, city_name, data_ready = render_sidebar()

if not data_ready:
    st.title(f"🗺️ {city_name}")
    st.info("Brak danych. Uruchom pipeline ze strony głównej.")
    st.stop()

@st.cache_data(show_spinner=False)
def _load(slug: str):
    return load_hex_metrics(slug), load_raw_machines(slug)

with st.spinner(f"Ładowanie danych dla {city_name}…"):
    df, df_machines = _load(city_slug)

if df is None:
    st.error("Nie udało się załadować hex_metrics_res9_full.parquet.")
    st.stop()

st.title(f"🗺️ {city_name} — mapa pokrycia i dostępności")

tab_cov, tab_acc = st.tabs(["🟦 Pokrycie", "🚶 Dostępność"])

with tab_cov:
    st.subheader("Pokrycie siecią paczkomatów")
    st.caption(
        "Heksagony res-9 (~200 m) kolorowane wg liczby paczkomatów. "
        "**Szary** = brak · **pomarańczowy** = rzadkie · "
        "**jasnoniebieski** = umiarkowane · **ciemnoniebieski** = gęste."
    )
    with st.spinner("Renderowanie mapy…"):
        render_map(coverage_map(df), key="coverage")

with tab_acc:
    st.subheader("Dostępność — odległość do najbliższego paczkomatu")
    st.caption(
        "**Zielony** = doskonała (< 200 m) · **jasnozielony** = dobra (< 500 m) · "
        "**pomarańczowy** = przeciętna (< 1 km) · **czerwony** = słaba (> 1 km)."
    )
    with st.spinner("Renderowanie mapy…"):
        render_map(accessibility_map(df), key="accessibility")
