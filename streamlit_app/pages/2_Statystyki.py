"""Strona 2 — KPI, rozkłady, tabela heksagonów z filtrami."""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "streamlit_app"))

import streamlit as st

from components.city_selector import render_sidebar
from paczkomatoza.io.parquet_io import compute_kpis, load_hex_metrics

st.set_page_config(page_title="Statystyki · Paczkomatoza", page_icon="📊", layout="wide")

with st.sidebar:
    city_slug, city_name, data_ready = render_sidebar()

if not data_ready:
    st.title(f"📊 {city_name}")
    st.info("Brak danych. Uruchom pipeline ze strony głównej.")
    st.stop()

@st.cache_data(show_spinner=False)
def _load(slug: str):
    return load_hex_metrics(slug)

with st.spinner(f"Ładowanie danych dla {city_name}…"):
    df = _load(city_slug)

if df is None:
    st.error("Nie udało się załadować hex_metrics_res9_full.parquet.")
    st.stop()

kpis = compute_kpis(df)

st.title(f"📊 {city_name} — statystyki")

# ── KPI ──────────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Paczkomaty", f"{kpis['total_machines']:,}")
col2.metric("Populacja w zasięgu", f"{kpis['pct_served']} %")
col3.metric("Nieobsłużona populacja", f"{kpis['unserved_population']:,}")
col4.metric("Nieobsłużone heksy", f"{kpis['unserved_hexes']:,}")
col5.metric("Mediana odl. (bez pokrycia)", f"{kpis['median_dist_unserved_m']} m")

st.divider()

# ── filtry + tabela ───────────────────────────────────────────────────────────
st.subheader("Dane per heksagon")

col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    coverage_filter = st.multiselect(
        "Pokrycie",
        options=["none", "sparse", "moderate", "dense"],
        default=["none", "sparse", "moderate", "dense"],
    )
with col_f2:
    min_pop = st.number_input("Min. populacja w heksie", min_value=0, value=0, step=50)
with col_f3:
    only_unserved = st.checkbox("Tylko nieobsłużone heksy")

filtered = df.copy()
if coverage_filter:
    filtered = filtered[filtered["coverage_class"].isin(coverage_filter)]
filtered = filtered[filtered["population"] >= min_pop]
if only_unserved:
    filtered = filtered[filtered["is_unserved"]]

DISPLAY_COLS = [
    "h3_index", "coverage_class", "accessibility_class", "n_machines",
    "population", "dist_to_nearest_m", "is_unserved", "unserved_population",
    "n_shops", "n_food", "n_transport", "population_density_class",
]
cols = [c for c in DISPLAY_COLS if c in filtered.columns]

st.caption(f"Wyświetlono {len(filtered):,} z {len(df):,} heksagonów")
st.dataframe(filtered[cols].reset_index(drop=True), use_container_width=True, height=480)

st.download_button(
    "⬇ Pobierz CSV",
    data=filtered[cols].to_csv(index=False).encode("utf-8"),
    file_name=f"{city_slug}_hex_metrics.csv",
    mime="text/csv",
)
