"""Budowniczowie map Folium dla wizualizacji heksagonalnych."""
from __future__ import annotations

import folium
import pandas as pd
from shapely import wkb
from shapely.geometry import mapping

from paczkomatoza.viz.color_scales import (
    ACCESSIBILITY_COLORS,
    ACCESSIBILITY_LABELS,
    COVERAGE_COLORS,
    COVERAGE_LABELS,
    DENSITY_COLORS,
    HEX_OPACITY,
    HEX_WEIGHT,
    MACHINE_TYPE_COLORS,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _center(df: pd.DataFrame) -> tuple[float, float]:
    return float(df["center_lat"].mean()), float(df["center_lng"].mean())


def _decode_geometry(geom_bytes: bytes) -> dict:
    """WKB bytes → GeoJSON-compatible dict."""
    return mapping(wkb.loads(geom_bytes))


def _hex_geojson(df: pd.DataFrame) -> dict:
    features = []
    for _, row in df.iterrows():
        try:
            geom = _decode_geometry(row["geometry"])
        except Exception:
            continue
        props = {k: (None if pd.isna(v) else v) for k, v in row.drop("geometry").items()}
        features.append({"type": "Feature", "geometry": geom, "properties": props})
    return {"type": "FeatureCollection", "features": features}


def _base_map(df: pd.DataFrame, zoom: int = 11) -> folium.Map:
    lat, lng = _center(df)
    return folium.Map(location=[lat, lng], zoom_start=zoom, tiles="CartoDB positron")


def _add_machine_markers(m: folium.Map, df_machines: pd.DataFrame) -> None:
    group = folium.FeatureGroup(name="Paczkomaty (lokalizacje)", show=True)
    for _, row in df_machines.iterrows():
        lat, lng = row.get("latitude"), row.get("longitude")
        if pd.isna(lat) or pd.isna(lng):
            continue
        loc_type = str(row.get("location_type", "Outdoor"))
        color = MACHINE_TYPE_COLORS.get(loc_type, "#555555")
        tooltip = f"{row.get('name', '')} · {loc_type} · {row.get('status', '')}"
        folium.CircleMarker(
            location=[lat, lng],
            radius=4,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.85,
            weight=1,
            tooltip=tooltip,
        ).add_to(group)
    group.add_to(m)


def _add_legend(m: folium.Map, title: str, colors: dict, labels: dict) -> None:
    items = "".join(
        f'<li><span style="background:{colors[k]};width:14px;height:14px;'
        f'display:inline-block;margin-right:6px;border:1px solid #999"></span>{labels.get(k, k)}</li>'
        for k in colors
    )
    html = (
        f'<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;'
        f'padding:10px 14px;border-radius:6px;border:1px solid #ccc;font-size:13px;">'
        f'<b>{title}</b><ul style="list-style:none;margin:6px 0 0;padding:0">{items}</ul></div>'
    )
    m.get_root().html.add_child(folium.Element(html))


# ── mapy publiczne ────────────────────────────────────────────────────────────

def coverage_map(df: pd.DataFrame) -> folium.Map:
    """Heksagony kolorowane wg coverage_class."""
    m = _base_map(df)
    folium.GeoJson(
        _hex_geojson(df),
        style_function=lambda f: {
            "fillColor": COVERAGE_COLORS.get(
                f["properties"].get("coverage_class") or "none", "#cccccc"
            ),
            "color": "#555555", "weight": HEX_WEIGHT, "fillOpacity": HEX_OPACITY,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["h3_index", "coverage_class", "n_machines", "population"],
            aliases=["H3", "Pokrycie", "Paczkomaty", "Populacja"],
            localize=True,
        ),
        name="Pokrycie (coverage_class)",
    ).add_to(m)
    _add_legend(m, "Pokrycie", COVERAGE_COLORS, COVERAGE_LABELS)
    folium.LayerControl().add_to(m)
    return m


def accessibility_map(df: pd.DataFrame) -> folium.Map:
    """Heksagony kolorowane wg accessibility_class (odległość do paczkomatu)."""
    m = _base_map(df)
    folium.GeoJson(
        _hex_geojson(df),
        style_function=lambda f: {
            "fillColor": ACCESSIBILITY_COLORS.get(
                f["properties"].get("accessibility_class") or "poor", "#cccccc"
            ),
            "color": "#555555", "weight": HEX_WEIGHT, "fillOpacity": HEX_OPACITY,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["h3_index", "accessibility_class", "dist_to_nearest_m", "n_machines"],
            aliases=["H3", "Dostępność", "Odl. do najbliższego [m]", "Paczkomaty"],
            localize=True,
        ),
        name="Dostępność (accessibility_class)",
    ).add_to(m)
    _add_legend(m, "Dostępność", ACCESSIBILITY_COLORS, ACCESSIBILITY_LABELS)
    folium.LayerControl().add_to(m)
    return m


def unserved_map(
    df: pd.DataFrame,
    df_machines: pd.DataFrame | None = None,
) -> folium.Map:
    """Nieobsłużone heksagony na tle gęstości zaludnienia."""
    m = _base_map(df)

    folium.GeoJson(
        _hex_geojson(df),
        style_function=lambda f: {
            "fillColor": DENSITY_COLORS.get(
                f["properties"].get("population_density_class") or "low", "#ffffcc"
            ),
            "color": "#aaaaaa", "weight": HEX_WEIGHT, "fillOpacity": 0.35,
        },
        name="Gęstość zaludnienia",
    ).add_to(m)

    unserved = df[df["is_unserved"]].copy()
    if not unserved.empty:
        folium.GeoJson(
            _hex_geojson(unserved),
            style_function=lambda _: {
                "fillColor": "#d7191c", "color": "#8b0000",
                "weight": 0.8, "fillOpacity": 0.75,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["h3_index", "population", "dist_to_nearest_m", "unserved_population"],
                aliases=["H3", "Populacja", "Odl. do paczkomatu [m]", "Nieobsłużona pop."],
                localize=True,
            ),
            name="Obszary nieobsłużone",
        ).add_to(m)

    if df_machines is not None and not df_machines.empty:
        _add_machine_markers(m, df_machines)

    folium.LayerControl().add_to(m)
    return m


def recommendations_map(
    df_rec: pd.DataFrame,
    df_machines: pd.DataFrame | None = None,
) -> folium.Map:
    """Kandydaci na nowe lokalizacje paczkomatów — residual ML."""
    df_plot = df_rec[df_rec["residual"] > 1.0].copy()
    m = _base_map(df_plot, zoom=11)

    def _rec_style(feature: dict) -> dict:
        residual = feature["properties"].get("residual") or 0
        intensity = min(residual / 3.0, 1.0)
        r = int(255 * intensity)
        g = int(100 * (1 - intensity))
        return {
            "fillColor": f"#{r:02x}{g:02x}40",
            "color": "#333333", "weight": 0.6, "fillOpacity": 0.75,
        }

    folium.GeoJson(
        _hex_geojson(df_plot),
        style_function=_rec_style,
        tooltip=folium.GeoJsonTooltip(
            fields=["h3_index", "residual", "prediction", "n_machines", "population", "n_shops"],
            aliases=["H3", "Residual ML", "Predykcja", "Obecne paczkomaty", "Populacja", "Sklepy"],
            localize=True,
        ),
        name="Rekomendacje ML",
    ).add_to(m)

    if df_machines is not None and not df_machines.empty:
        _add_machine_markers(m, df_machines)

    folium.LayerControl().add_to(m)
    return m
