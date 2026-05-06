"""Konfiguracja projektu: miasta, rozdzielczości H3, progi analizy.

Sekrety czytane z os.getenv — działają wszędzie:
  - lokalnie: ustaw zmienną środowiskową lub wpisz do .streamlit/secrets.toml
  - Streamlit Cloud: top-level klucze z Secrets są automatycznie eksponowane
    jako env vars (dostępne przez os.getenv)
"""
from __future__ import annotations

import os
from pathlib import Path

# ── parametry API ─────────────────────────────────────────────────────────────

PER_PAGE = 100
MAX_RETRIES = 5

API_BASE: str = os.getenv("INPOST_API_BASE", "")

# ── ścieżki ──────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_ROOT = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_ROOT / "processed"

# ── miasta ────────────────────────────────────────────────────────────────────

CITIES: dict[str, str] = {
    "gdansk": "Gdańsk",
    "krakow": "Kraków",
    "poznan": "Poznań",
    "warszawa": "Warszawa",
    "wroclaw": "Wrocław",
}

# ── siatka H3 ─────────────────────────────────────────────────────────────────

H3_RESOLUTION = 9          # ~174 m krawędź — podstawowa rozdzielczość analizy
H3_RESOLUTION_COARSE = 8   # ~462 m — widok dzielnicowy

# ── progi analizy ─────────────────────────────────────────────────────────────

SERVED_RADIUS_M = 500      # poniżej tej odległości hex jest "obsłużony"
MIN_POPULATION = 50        # minimalna populacja żeby liczyć hex jako zamieszkały
