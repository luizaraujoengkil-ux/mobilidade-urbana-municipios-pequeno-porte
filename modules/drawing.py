"""Captura de geometrias desenhadas pelo usuario no folium via streamlit_folium."""
from __future__ import annotations

from typing import Iterable, Optional

import geopandas as gpd
from shapely.geometry import shape


def extract_drawings(
    map_state: Optional[dict],
    allowed_types: Optional[Iterable[str]] = None,
) -> gpd.GeoDataFrame:
    """Le 'all_drawings' do retorno de st_folium e devolve um GeoDataFrame.

    allowed_types: filtra por tipo de geometria (ex. {'Polygon'} ou {'LineString'}).
    Sempre devolve um GeoDataFrame valido em EPSG:4326 (vazio se nada foi desenhado).
    """
    empty = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    if not map_state:
        return empty
    drawings = map_state.get("all_drawings") or []
    if not drawings:
        return empty

    rows = []
    for d in drawings:
        if not d or "geometry" not in d:
            continue
        try:
            geom = shape(d["geometry"])
        except Exception:
            continue
        if allowed_types and geom.geom_type not in allowed_types:
            continue
        props = d.get("properties") or {}
        # streamlit_folium aninha em 'properties' as info de estilo do leaflet;
        # ignoramos esse ruido e mantemos so a geometria + props do usuario (se houver)
        rows.append({"geometry": geom})
    if not rows:
        return empty
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")
