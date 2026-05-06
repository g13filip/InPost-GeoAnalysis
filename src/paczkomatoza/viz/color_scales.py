"""Palety kolorów i helpery klasyfikacyjne dla wizualizacji."""
from __future__ import annotations

# ── palety klas ───────────────────────────────────────────────────────────────

COVERAGE_COLORS: dict[str, str] = {
    "none":     "#e0e0e0",
    "sparse":   "#fdae61",
    "moderate": "#abd9e9",
    "dense":    "#2c7bb6",
}

COVERAGE_LABELS: dict[str, str] = {
    "none":     "Brak",
    "sparse":   "Rzadkie",
    "moderate": "Umiarkowane",
    "dense":    "Gęste",
}

ACCESSIBILITY_COLORS: dict[str, str] = {
    "excellent": "#1a9641",
    "good":      "#a6d96a",
    "fair":      "#fdae61",
    "poor":      "#d7191c",
}

ACCESSIBILITY_LABELS: dict[str, str] = {
    "excellent": "Doskonała (< 200 m)",
    "good":      "Dobra (< 500 m)",
    "fair":      "Przeciętna (< 1 km)",
    "poor":      "Słaba (> 1 km)",
}

DENSITY_COLORS: dict[str, str] = {
    "low":       "#ffffcc",
    "medium":    "#fd8d3c",
    "high":      "#bd0026",
    "very_high": "#67000d",
}

MACHINE_TYPE_COLORS: dict[str, str] = {
    "Outdoor": "#1d6fa4",
    "Indoor":  "#e07b00",
    "POP":     "#6a0dad",
}

# ── parametry warstwy hex ─────────────────────────────────────────────────────

HEX_OPACITY: float = 0.65
HEX_WEIGHT: float = 0.4
