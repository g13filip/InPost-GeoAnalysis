"""Paczkomatoza — strona główna i pipeline runner.

Uruchom lokalnie:
    pip install -e .                    # instaluje paczkomatoza z src/
    streamlit run streamlit_app/app.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Fallback dla lokalnego uruchamiania bez `pip install -e .`
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

_app_dir = Path(__file__).resolve().parent
if str(_app_dir) not in sys.path:
    sys.path.insert(0, str(_app_dir))

import streamlit as st

from components.city_selector import PIPELINE_ENABLED, render_sidebar

if PIPELINE_ENABLED:
    from paczkomatoza.pipeline import PIPELINE_STEPS, run_pipeline

st.set_page_config(
    page_title="Paczkomatoza",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

with st.sidebar:
    city_slug, city_name, data_ready = render_sidebar()

# ── pipeline runner (tylko w trybie lokalnym) 

if PIPELINE_ENABLED and st.session_state.get("pipeline_running"):
    pipe_slug = st.session_state["pipeline_city"]
    pipe_name = st.session_state["pipeline_city_name"]

    st.title(f"⚙️ Pipeline dla: {pipe_name}")

    total = len(PIPELINE_STEPS)

    # pasek postępu + aktualny krok
    progress_bar = st.progress(0.0, text="Przygotowanie…")
    status_text  = st.empty()

    # lista kroków — każdy ma swój placeholder wiersza
    st.markdown("---")
    placeholders: dict[str, st.empty] = {}
    for step in PIPELINE_STEPS:
        placeholders[step.name] = st.empty()
        placeholders[step.name].markdown(
            f"⬜ &nbsp; **{step.name}** — {step.description}"
        )
    st.markdown("---")

    # licznik kroków + flagi stanu — domknięcia bez zmiany API
    counter = [0]
    city_was_cached = [False]
    city_not_found = [False]

    def on_start(name: str) -> None:
        frac = counter[0] / total
        progress_bar.progress(frac, text=f"Krok {counter[0] + 1}/{total}: **{name}**…")
        status_text.markdown(f"🔄 &nbsp; Trwa: `{name}`")
        placeholders[name].markdown(f"🔄 &nbsp; **{name}** — uruchamianie…")

    def on_done(name: str) -> None:
        counter[0] += 1
        progress_bar.progress(counter[0] / total, text=f"Ukończono {counter[0]}/{total}: **{name}**")
        placeholders[name].markdown(f"✅ &nbsp; **{name}**")

    def on_error(name: str, err: str) -> None:
        progress_bar.progress(counter[0] / total, text=f"❌ Błąd w: {name}")
        status_text.error(f"Błąd w kroku **{name}**")
        placeholders[name].markdown(f"❌ &nbsp; **{name}** — `{err}`")

    def on_not_found(name: str, err: str) -> None:
        city_not_found[0] = True
        progress_bar.progress(0.0, text="❌ Miasto nieznane")
        status_text.empty()
        placeholders[name].markdown(
            f"❌ &nbsp; **{name}** — miasto nie znalezione w API"
        )
        for step in PIPELINE_STEPS:
            if step.name != name:
                placeholders[step.name].markdown(
                    f"⏭ &nbsp; **{step.name}** — pominięto"
                )

    def on_cached(name: str) -> None:
        """Wywoływane gdy dane dla miasta już istnieją — nie jest to błąd."""
        city_was_cached[0] = True
        placeholders[name].markdown(
            f"ℹ️ &nbsp; **{name}** — dane już istniały, pominięto"
        )
        # Oznacz pozostałe kroki jako pominięte
        skip = False
        for step in PIPELINE_STEPS:
            if step.name == name:
                skip = True
                continue
            if skip:
                placeholders[step.name].markdown(
                    f"⏭ &nbsp; **{step.name}** — pominięto (dane aktualne)"
                )
        progress_bar.progress(1.0, text="ℹ️ Dane dla tego miasta są już obliczone")
        status_text.empty()

    success = run_pipeline(
        pipe_slug, pipe_name,
        on_start, on_done, on_error, on_cached,
        on_city_not_found=on_not_found,
    )

    if city_not_found[0]:
        st.warning(
            f"### 🔍 Miasto nieznalezione\n\n"
            f"API InPost nie zwraca danych dla **{pipe_name}**.\n\n"
            "**Możliwe przyczyny:**\n"
            "- Literówka w nazwie — API wymaga polskiej pisowni (np. `Łódź`, nie `Lodz`)\n"
            "- Miasto poniżej progu — InPost może nie obsługiwać tej miejscowości\n"
            "- Nazwa niejednoznaczna — spróbuj dodać województwo (np. `Lublin, Lublin`)\n\n"
            "Popraw nazwę i uruchom pipeline ponownie."
        )
    elif city_was_cached[0]:
        st.info(
            f"Statystyki dla miasta **{pipe_name}** są już obliczone. "
            "Możesz je przeglądać w zakładkach po lewej stronie."
        )
    elif success:
        progress_bar.progress(1.0, text="✅ Wszystkie kroki zakończone!")
        status_text.empty()
        st.success(f"Pipeline dla **{pipe_name}** zakończony pomyślnie!")
    else:
        st.error(
            "Pipeline zatrzymał się na błędzie — sprawdź szczegóły powyżej."
        )

    if st.button("← Wróć"):
        st.session_state["pipeline_running"] = False
        st.rerun()

    st.stop()

# ── landing 

st.title("📦 Paczkomatoza")
st.markdown(
    "Interaktywna analiza rozmieszczenia paczkomatów InPost w polskich miastach. "
    "Wybierz miasto z panelu bocznego, a następnie przejdź do jednej z podstron."
)

st.markdown("---")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("### 🗺️ Mapa miasta")
    st.markdown("Pokrycie i dostępność paczkomatów na siatce heksagonów H3 res-9.")

with col2:
    st.markdown("### 📊 Statystyki")
    st.markdown("KPI, rozkłady, tabela heksagonów z filtrami i eksportem CSV.")

with col3:
    st.markdown("### 🔍 Białe plamy")
    st.markdown("Obszary nieobsłużone i rekomendacje modelu ML (XGBoost).")

if not data_ready:
    st.info(
        f"Brak danych analitycznych dla **{city_name}**. "
        "Wpisz nazwę miasta w sidebarze i uruchom pipeline."
    )
