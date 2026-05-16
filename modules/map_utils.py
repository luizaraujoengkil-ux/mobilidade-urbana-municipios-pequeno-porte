"""Funcoes auxiliares para montar o mapa Folium do prototipo."""
from __future__ import annotations

from typing import Optional

import folium
import geopandas as gpd
from folium.plugins import Draw, MeasureControl, MiniMap

from .config import COLORS, MATIAS_BARBOSA_CENTER, DEFAULT_ZOOM


def create_base_map(center=MATIAS_BARBOSA_CENTER, zoom=DEFAULT_ZOOM) -> folium.Map:
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles=None,
        control_scale=True,
    )

    folium.TileLayer(
        "OpenStreetMap",
        name="OpenStreetMap",
        attr="&copy; OpenStreetMap contributors",
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        name="Satelite (Esri)",
        attr="Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics",
        control=True,
    ).add_to(m)

    folium.TileLayer(
        "CartoDB positron",
        name="Mapa Claro",
        attr="&copy; OpenStreetMap contributors, &copy; CARTO",
        control=True,
    ).add_to(m)

    MiniMap(toggle_display=True, position="bottomleft").add_to(m)
    MeasureControl(primary_length_unit="meters", position="topleft").add_to(m)

    # Marcador da cidade
    folium.Marker(
        location=center,
        tooltip="Matias Barbosa / MG",
        popup="Centro aproximado de Matias Barbosa - MG",
        icon=folium.Icon(color="purple", icon="info-sign"),
    ).add_to(m)

    return m


def add_area_estudo(m: folium.Map, gdf: gpd.GeoDataFrame, show: bool = True) -> None:
    if gdf is None or gdf.empty:
        return
    fg = folium.FeatureGroup(name="Area de Estudo", show=show)
    folium.GeoJson(
        gdf.to_json(),
        style_function=lambda x: {
            "color": COLORS["area_estudo"],
            "weight": 3,
            "fillOpacity": 0.0,
            "dashArray": "8,6",
        },
        tooltip=folium.GeoJsonTooltip(fields=[c for c in gdf.columns if c != "geometry"][:3]),
    ).add_to(fg)
    fg.add_to(m)


def add_zonas(m: folium.Map, gdf: gpd.GeoDataFrame, show: bool = True) -> None:
    if gdf is None or gdf.empty:
        return
    fg = folium.FeatureGroup(name="Zonas Analiticas", show=show)
    for _, row in gdf.iterrows():
        zona = str(row.get("zona", "")).upper()
        color = COLORS.get(zona, "#7F7F7F")
        tooltip = f"<b>{row.get('zona','')}</b> - {row.get('nome','')}"
        popup_html = "<br>".join(
            [f"<b>{c}:</b> {row[c]}" for c in gdf.columns if c not in ("geometry",)]
        )
        folium.GeoJson(
            gpd.GeoSeries([row.geometry]).__geo_interface__,
            style_function=lambda x, color=color: {
                "color": color,
                "weight": 2,
                "fillColor": color,
                "fillOpacity": 0.35,
            },
            tooltip=tooltip,
            popup=folium.Popup(popup_html, max_width=350),
        ).add_to(fg)
    fg.add_to(m)


def add_ferrovia(m: folium.Map, gdf: gpd.GeoDataFrame, show: bool = True) -> None:
    if gdf is None or gdf.empty:
        return
    fg = folium.FeatureGroup(name="Linha do Trem", show=show)
    folium.GeoJson(
        gdf.to_json(),
        style_function=lambda x: {"color": COLORS["trem"], "weight": 4, "dashArray": "10,6"},
        tooltip=folium.GeoJsonTooltip(fields=[c for c in gdf.columns if c != "geometry"][:3]),
    ).add_to(fg)
    fg.add_to(m)


def add_rodovias(m: folium.Map, gdf: gpd.GeoDataFrame, show: bool = True) -> None:
    if gdf is None or gdf.empty:
        return
    color_map = {
        "br040": COLORS["br040"],
        "uniao_industria": COLORS["uniao_industria"],
        "mg353": COLORS["mg353"],
    }
    fg = folium.FeatureGroup(name="Rodovias (BR-040, MG-353, Uniao Industria)", show=show)
    for _, row in gdf.iterrows():
        cat = str(row.get("categoria", "")).lower()
        color = color_map.get(cat, "#555555")
        weight = 5 if cat == "br040" else 3
        folium.GeoJson(
            gpd.GeoSeries([row.geometry]).__geo_interface__,
            style_function=lambda x, color=color, weight=weight: {"color": color, "weight": weight},
            tooltip=f"<b>{row.get('nome','')}</b><br>{row.get('observacoes','')}",
        ).add_to(fg)
    fg.add_to(m)


def add_pontos_viaduto(m: folium.Map, gdf: gpd.GeoDataFrame, show: bool = True) -> None:
    if gdf is None or gdf.empty:
        return
    fg = folium.FeatureGroup(name="Pontos de Estudo de Viaduto", show=show)
    for _, row in gdf.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=8,
            color="#1B5E20",
            weight=2,
            fill=True,
            fill_color=COLORS["viaduto_estudo"],
            fill_opacity=0.9,
            tooltip=f"<b>{row.get('nome','')}</b><br>{row.get('descricao','')}",
        ).add_to(fg)
    fg.add_to(m)


def add_pontos_interesse(m: folium.Map, gdf: gpd.GeoDataFrame, show: bool = True) -> None:
    if gdf is None or gdf.empty:
        return
    icon_map = {
        "Escola": ("graduation-cap", "blue"),
        "Comercio": ("shopping-cart", "green"),
        "Industria": ("industry", "darkred"),
        "Terminal/Parada": ("bus", "orange"),
        "Estudo de viaduto": ("star", "green"),
        "Travessia critica": ("warning-sign", "red"),
        "Ponte proposta": ("road", "blue"),
        "Viaduto proposto": ("road", "darkblue"),
        "Outro": ("info-sign", "gray"),
    }
    fg = folium.FeatureGroup(name="Pontos de Interesse", show=show)
    for _, row in gdf.iterrows():
        cat = row.get("categoria", "Outro")
        icon_name, color = icon_map.get(cat, ("info-sign", "gray"))
        try:
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                tooltip=f"<b>{row.get('nome','')}</b> ({cat})",
                popup=row.get("descricao", ""),
                icon=folium.Icon(color=color, icon=icon_name, prefix="fa"),
            ).add_to(fg)
        except Exception:
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=6,
                color=color,
                fill=True,
            ).add_to(fg)
    fg.add_to(m)


def add_custom_layer(m: folium.Map, gdf: gpd.GeoDataFrame, name: str, color: str = "#1565C0") -> None:
    if gdf is None or gdf.empty:
        return
    fg = folium.FeatureGroup(name=name, show=True)
    geom_types = set(gdf.geometry.geom_type)
    if geom_types & {"Point"}:
        for _, row in gdf.iterrows():
            if row.geometry is None or row.geometry.is_empty:
                continue
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=6,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.85,
                tooltip=str(row.get("Name", row.get("nome", name))),
            ).add_to(fg)
    else:
        folium.GeoJson(
            gdf.to_json(),
            style_function=lambda x, color=color: {
                "color": color,
                "weight": 3,
                "fillColor": color,
                "fillOpacity": 0.25,
            },
        ).add_to(fg)
    fg.add_to(m)


def add_flow_lines(m: folium.Map, flow_records: list, show: bool = True) -> None:
    """Adiciona linhas de fluxo entre centroides das zonas."""
    if not flow_records:
        return
    fg = folium.FeatureGroup(name="Linhas de Fluxo O-D", show=show)
    max_flow = max(r["flow"] for r in flow_records) or 1
    for r in flow_records:
        weight = 1 + 8 * (r["flow"] / max_flow)
        folium.PolyLine(
            locations=[[r["from_lat"], r["from_lon"]], [r["to_lat"], r["to_lon"]]],
            color=COLORS["fluxo"],
            weight=weight,
            opacity=0.7,
            tooltip=f"{r['from']} -> {r['to']}: {r['flow']:.1f} viagens",
        ).add_to(fg)
    fg.add_to(m)


def add_draw_control(m: folium.Map) -> None:
    Draw(
        export=True,
        position="topleft",
        draw_options={
            "polyline": True,
            "polygon": False,
            "circle": False,
            "rectangle": False,
            "marker": True,
            "circlemarker": False,
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(m)


def add_layer_control(m: folium.Map) -> None:
    folium.LayerControl(collapsed=False, position="topright").add_to(m)
