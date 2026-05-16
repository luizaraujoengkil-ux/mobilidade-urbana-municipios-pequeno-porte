"""Funcoes auxiliares para montar o mapa Folium do prototipo."""
from __future__ import annotations

from typing import Optional

import folium
import geopandas as gpd
from folium.plugins import Draw, MeasureControl, MiniMap

from .config import CATEGORY_STYLE, COLORS, MATIAS_BARBOSA_CENTER, DEFAULT_ZOOM


def create_base_map(center=MATIAS_BARBOSA_CENTER, zoom=DEFAULT_ZOOM, label: str = "Matias Barbosa / MG") -> folium.Map:
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

    # Marcador da cidade (label dinamico)
    folium.Marker(
        location=center,
        tooltip=label,
        popup=f"Centro aproximado de {label}",
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
        # cor: prioridade 1) coluna 'cor' (definida no assistente) 2) palette por codigo de zona
        color = row.get("cor") if "cor" in gdf.columns and row.get("cor") else COLORS.get(zona, "#7F7F7F")
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


def add_pontos_viaduto(m: folium.Map, gdf: gpd.GeoDataFrame, show: bool = True,
                        active_indices=None) -> None:
    """Renderiza os pontos de estudo de viaduto como camadas individuais.

    Cada ponto vira um FeatureGroup separado no controle de camadas do mapa,
    o que permite ao usuario marcar/desmarcar cada um individualmente.

    Args:
        gdf: GeoDataFrame com os pontos
        show: visibilidade padrao quando active_indices nao e fornecido
        active_indices: conjunto de indices (0-based) que devem comecar visiveis.
            Se fornecido, sobrescreve 'show' por ponto.
    """
    if gdf is None or gdf.empty:
        return
    for idx, (_, row) in enumerate(gdf.iterrows()):
        nome = row.get("nome", f"Ponto {idx+1}")
        descricao = row.get("descricao", "")
        if active_indices is not None:
            is_visible = idx in active_indices
        else:
            is_visible = show
        fg = folium.FeatureGroup(name=f"🟢 {nome}", show=is_visible)
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=8,
            color="#1B5E20",
            weight=2,
            fill=True,
            fill_color=COLORS["viaduto_estudo"],
            fill_opacity=0.9,
            tooltip=f"<b>{nome}</b><br>{descricao}",
        ).add_to(fg)
        fg.add_to(m)


def add_pontos_interesse(m: folium.Map, gdf: gpd.GeoDataFrame, show: bool = True,
                          layer_name: str = "Pontos de Interesse") -> None:
    if gdf is None or gdf.empty:
        return
    fg = folium.FeatureGroup(name=layer_name, show=show)
    for _, row in gdf.iterrows():
        cat = row.get("categoria", "Outro")
        style = CATEGORY_STYLE.get(cat, CATEGORY_STYLE["Outro"])
        try:
            folium.Marker(
                location=[row.geometry.y, row.geometry.x],
                tooltip=f"<b>{row.get('nome','')}</b> ({cat})",
                popup=str(row.get("descricao", "")),
                icon=folium.Icon(color=style["color"], icon=style["icon"], prefix="fa"),
            ).add_to(fg)
        except Exception:
            folium.CircleMarker(
                location=[row.geometry.y, row.geometry.x],
                radius=6,
                color=style.get("marker", "#666"),
                fill=True,
            ).add_to(fg)
    fg.add_to(m)


def add_osm_network(m: folium.Map, edges_gdf: gpd.GeoDataFrame, show: bool = True) -> None:
    """Renderiza a malha viaria do OpenStreetMap em tons de azul (hierarquia viaria)."""
    if edges_gdf is None or len(edges_gdf) == 0:
        return
    fg = folium.FeatureGroup(name="Malha viaria (OSM)", show=show)
    # estilo por tipo de via, se a propriedade 'highway' estiver disponivel
    def style_fn(feat):
        props = feat.get("properties", {})
        hw = props.get("highway") if props else None
        if isinstance(hw, list):
            hw = hw[0] if hw else None
        if hw in ("motorway", "trunk", "primary"):
            return {"color": "#0D47A1", "weight": 4.0, "opacity": 0.95}   # azul escuro
        if hw in ("secondary", "tertiary"):
            return {"color": "#1976D2", "weight": 2.6, "opacity": 0.85}   # azul medio
        return {"color": "#64B5F6", "weight": 1.6, "opacity": 0.75}        # azul claro

    keep_cols = [c for c in ["highway", "name", "length"] if c in edges_gdf.columns]
    try:
        gj = edges_gdf[keep_cols + ["geometry"]].to_json() if keep_cols else edges_gdf[["geometry"]].to_json()
    except Exception:
        gj = edges_gdf.to_json()
    folium.GeoJson(
        gj,
        style_function=style_fn,
        name="Malha viaria (OSM)",
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
