"""Busca de POIs sugeridos no OpenStreetMap dentro de uma area de estudo."""
from __future__ import annotations

from typing import Optional

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, Point

try:
    import osmnx as ox  # type: ignore
    HAS_OSMNX = True
except Exception:
    HAS_OSMNX = False


# Tags OSM que vamos consultar
DEFAULT_TAGS = {
    "amenity": [
        "school", "kindergarten", "college", "university",
        "hospital", "clinic", "pharmacy", "doctors",
        "townhall", "police", "fire_station", "post_office",
        "bus_station", "place_of_worship",
    ],
    "shop": True,
    "industrial": True,
    "landuse": ["industrial", "commercial"],
    "railway": ["station", "halt", "level_crossing"],
    "public_transport": ["station", "platform"],
    "highway": ["bus_stop", "motorway_junction"],
    "man_made": ["bridge"],
}


def _classify(row: pd.Series) -> str:
    """Mapeia tags OSM -> categoria interna."""
    amenity = row.get("amenity")
    if amenity in ("school", "kindergarten", "college", "university"):
        return "Escola"
    if amenity in ("hospital", "clinic", "doctors"):
        return "Hospital"
    if amenity == "pharmacy":
        return "Posto de saude"
    if amenity == "townhall":
        return "Prefeitura"
    if amenity == "police":
        return "Outro"
    if amenity == "fire_station":
        return "Outro"
    if amenity == "post_office":
        return "Outro"
    if amenity == "place_of_worship":
        return "Outro"
    if amenity == "bus_station":
        return "Terminal/Parada"

    if row.get("railway") in ("station", "halt"):
        return "Estacao ferroviaria"
    if row.get("railway") == "level_crossing":
        return "Passagem em nivel"
    if row.get("public_transport") in ("station", "platform"):
        return "Terminal/Parada"
    if row.get("highway") == "bus_stop":
        return "Terminal/Parada"
    if row.get("highway") == "motorway_junction":
        return "Acesso a rodovia"
    if row.get("man_made") == "bridge":
        return "Ponte proposta"

    if row.get("shop"):
        return "Comercio"
    if row.get("industrial") or row.get("landuse") == "industrial":
        return "Industria"
    if row.get("landuse") == "commercial":
        return "Comercio"

    return "Outro"


def fetch_pois_in_polygon(polygon: Polygon) -> Optional[gpd.GeoDataFrame]:
    """Consulta features do OSM dentro do poligono e classifica em categorias internas.

    Retorna GeoDataFrame com colunas: nome, categoria, descricao, geometry
    (geometria reduzida a Point quando o feature original e poligono).
    """
    if not HAS_OSMNX:
        return None
    if polygon is None or polygon.is_empty:
        return None

    try:
        gdf = ox.features.features_from_polygon(polygon, tags=DEFAULT_TAGS)
    except AttributeError:
        # versoes antigas: ox.geometries_from_polygon
        try:
            gdf = ox.geometries_from_polygon(polygon, tags=DEFAULT_TAGS)  # type: ignore
        except Exception:
            return None
    except Exception:
        return None

    if gdf is None or gdf.empty:
        return None

    # Reduz para pontos (centroides quando necessario)
    pts = []
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            continue
        try:
            point = geom if geom.geom_type == "Point" else geom.centroid
        except Exception:
            continue
        nome = (
            row.get("name")
            or row.get("operator")
            or row.get("brand")
            or "(sem nome)"
        )
        categoria = _classify(row)
        descricao_parts = []
        for k in ("amenity", "shop", "railway", "highway", "public_transport", "industrial", "landuse"):
            v = row.get(k)
            if v and not isinstance(v, list):
                descricao_parts.append(f"{k}={v}")
        descricao = "; ".join(descricao_parts)
        pts.append({
            "nome": str(nome),
            "categoria": categoria,
            "descricao": descricao,
            "latitude": float(point.y),
            "longitude": float(point.x),
            "geometry": Point(point.x, point.y),
        })

    if not pts:
        return None
    return gpd.GeoDataFrame(pts, crs="EPSG:4326")
