"""Komponent sidebarowy: wybór miasta i (opcjonalnie) uruchamianie pipeline'u.

Tryb pracy kontroluje zmienna środowiskowa PIPELINE_ENABLED:
    brak / 1             → pełna wersja z pipeline'm (domyślnie lokalnie)
    PIPELINE_ENABLED=0   → tylko podgląd (ustaw na Streamlit Cloud / HF Spaces)

Wybór miast jest dynamiczny — każde nowe miasto przetworzone przez pipeline
pojawi się automatycznie na liście (skan data/analytics/cities/).
"""
from __future__ import annotations

import os
import sys
import unicodedata
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st

from paczkomatoza.config import CITIES
from paczkomatoza.io.parquet_io import available_cities

# Flaga trybu — domyślnie włączona. Na cloud ustaw PIPELINE_ENABLED=0.
PIPELINE_ENABLED: bool = os.getenv("PIPELINE_ENABLED", "1") == "1"


def _slugify(text: str) -> str:
    text = text.replace("ł", "l").replace("Ł", "L")
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_str = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_str.lower().strip().replace(" ", "_").replace("-", "_")


def _display_name(slug: str) -> str:
    """Zwraca ładną nazwę wyświetlaną dla sluga.

    Dla znanych miast używa CITIES dict. Dla nowych miast z pipeline'u
    formatuje slug jako Title Case (np. "lodz" → "Lodz").
    """
    return CITIES.get(slug, slug.replace("_", " ").title())


def render_sidebar() -> tuple[str, str, bool]:
    """Renderuje sidebar. Zwraca: (city_slug, city_name, data_ready)."""

    # Dynamiczne odkrywanie miast z pełnymi danymi na dysku
    ready = available_cities()          # skan data/analytics/cities/
    known_slugs = list(CITIES.keys())   # 5 pre-konfigurowanych miast

    # Widoczne w selectorze:
    # - view-only: tylko te z pełnymi danymi
    # - pipeline: znane + te z danymi (żeby pełna lista była dostępna)
    if PIPELINE_ENABLED:
        # Połącz znane miasta z nowymi z pipeline — bez duplikatów, z zachowaniem kolejności
        visible_slugs = known_slugs + [s for s in ready if s not in known_slugs]
    else:
        visible_slugs = ready  # tylko miasta z danymi

    st.title("📦 Paczkomatoza")
    st.caption("Analiza pokrycia paczkomatami InPost")

    if not visible_slugs:
        st.error("Brak danych. Skontaktuj się z autorem.")
        st.stop()

    # Domyślna pozycja: krakow jeśli istnieje, inaczej pierwsze z danymi
    default_slug = next(
        (s for s in ["krakow"] + ready if s in visible_slugs),
        visible_slugs[0],
    )
    default_index = visible_slugs.index(default_slug)

    city_slug = st.selectbox(
        "Wybierz miasto",
        options=visible_slugs,
        format_func=_display_name,
        index=default_index,
        key="selected_city",
    )
    city_name = _display_name(city_slug)
    data_ready = city_slug in ready

    st.divider()

    if PIPELINE_ENABLED:
        if data_ready:
            st.success(f"Dane dla **{city_name}** są dostępne.")
        else:
            st.warning(
                f"Brak danych dla **{city_name}**.\n\n"
                "Uruchom pipeline poniżej lub notebooki 02→11."
            )
        st.divider()

        # Lista miast: znane + nowe z pipeline (ze statusem)
        all_display = known_slugs + [s for s in ready if s not in known_slugs]
        st.markdown(
            "**Wszystkie miasta:**\n"
            + "\n".join(
                f"- {'✅' if s in ready else '⬜'} {_display_name(s)}"
                for s in all_display
            )
        )
    else:
        st.markdown(
            "**Dostępne miasta:**\n"
            + "\n".join(f"- {_display_name(s)}" for s in visible_slugs)
        )

    # ── sekcja pipeline — tylko w trybie lokalnym ────────────────────────────
    if PIPELINE_ENABLED:
        st.divider()
        st.markdown("#### ➕ Dodaj nowe miasto")
        new_city_input = st.text_input(
            "Nazwa miasta",
            placeholder="np. Łódź, Lublin, Katowice…",
            key="new_city_input",
        )
        if new_city_input.strip():
            new_slug = _slugify(new_city_input.strip())
            st.caption(f"Slug: `{new_slug}`")
            if new_slug in ready:
                st.info(f"Dane dla **{new_city_input}** już istnieją.")
            elif st.button("▶ Uruchom pipeline", type="primary", use_container_width=True):
                st.session_state["pipeline_city"] = new_slug
                st.session_state["pipeline_city_name"] = new_city_input.strip()
                st.session_state["pipeline_running"] = True
                st.rerun()

    return city_slug, city_name, data_ready
