"""Wrapper renderowania map Folium w Streamlit z cache'owaniem HTML."""
from __future__ import annotations

import streamlit as st
from streamlit_folium import st_folium
import folium

MAP_HEIGHT = 600


def render_map(m: folium.Map, key: str, height: int = MAP_HEIGHT) -> None:
    """Renderuje mapę Folium w Streamlit bez zwracania interakcji."""
    st_folium(m, height=height, use_container_width=True, returned_objects=[], key=key)


def machine_legend_caption(df_machines) -> None:
    """Wyświetla podpis legendy typów paczkomatów."""
    if df_machines is not None and not df_machines.empty:
        st.caption(
            f"🔵 **Outdoor** · 🟠 **Indoor** · 🟣 **POP** — "
            f"łącznie {len(df_machines):,} paczkomatów"
        )


def machines_checkbox(label: str, key: str) -> bool:
    return st.checkbox(
        label,
        value=True,
        key=key,
        help="Nakłada punkty istniejących paczkomatów (🔵 Outdoor · 🟠 Indoor · 🟣 POP).",
    )
