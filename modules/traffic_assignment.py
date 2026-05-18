"""Alocacao simplificada de fluxos O-D na rede viaria.

Algoritmo: para cada par (origem, destino) da matriz O-D, encontra o
menor caminho na rede (ponderado por comprimento) e ACUMULA o fluxo
estimado em cada aresta percorrida. As arestas com maior carregamento
indicam os trechos mais sobrecarregados pelo padrao de viagens.

Esta abordagem 'all-or-nothing' e a forma mais simples de assignment
em transportes. Nao considera congestionamento, capacidade ou retorno
de equilibrio - eh exploratoria.
"""
from __future__ import annotations

from typing import Optional

import networkx as nx
import pandas as pd

try:
    import osmnx as ox
    OSMNX_AVAILABLE = True
except Exception:
    OSMNX_AVAILABLE = False

import geopandas as gpd
from shapely.geometry import LineString


def _find_nearest_osm_node(G_osm, lat: float, lon: float):
    if not OSMNX_AVAILABLE or G_osm is None:
        return None
    try:
        return ox.distance.nearest_nodes(G_osm, X=lon, Y=lat)
    except Exception:
        return None


def assign_od_to_network(
    od_matrix: pd.DataFrame,
    zone_centroids_df: pd.DataFrame,
    osm_graph,
) -> Optional[dict]:
    """Aloca os fluxos da matriz O-D nos caminhos minimos da rede OSM.

    Args:
        od_matrix: DataFrame quadrado com fluxos T_ij (index e columns =
            codigos de zona, ex: 'Z1','Z2',...).
        zone_centroids_df: DataFrame com colunas 'zona', 'lat', 'lon'.
        osm_graph: nx.MultiDiGraph baixado via OSMnx.

    Returns:
        dict com:
        - 'edge_loads': DataFrame por aresta com fluxo acumulado
        - 'paths': lista de tuplas (origem, destino, fluxo, lista_nodes)
        - 'unreachable': pares (o,d) sem caminho na rede
    """
    if not OSMNX_AVAILABLE or osm_graph is None:
        return None
    if od_matrix is None or od_matrix.empty:
        return None
    if zone_centroids_df is None or zone_centroids_df.empty:
        return None

    # Mapeia codigo de zona -> no OSM mais proximo
    zona_to_osm_node = {}
    for _, row in zone_centroids_df.iterrows():
        z = str(row.get("zona", "")).upper().strip()
        lat = float(row["lat"])
        lon = float(row["lon"])
        node = _find_nearest_osm_node(osm_graph, lat, lon)
        if node is not None:
            zona_to_osm_node[z] = node

    if not zona_to_osm_node:
        return None

    # Acumulador de fluxo por aresta
    edge_loads = {}  # (u, v) -> fluxo total
    edge_od_pairs = {}  # (u, v) -> lista de pares (o,d) que passam
    paths_info = []
    unreachable = []

    for o_zona in od_matrix.index:
        if o_zona not in zona_to_osm_node:
            continue
        u_source = zona_to_osm_node[o_zona]
        # Roda Dijkstra uma vez por origem (eficiente para varios destinos)
        try:
            lengths, paths = nx.single_source_dijkstra(
                osm_graph, u_source, weight="length"
            )
        except Exception:
            continue
        for d_zona in od_matrix.columns:
            if o_zona == d_zona:
                continue
            if d_zona not in zona_to_osm_node:
                continue
            fluxo = float(od_matrix.loc[o_zona, d_zona])
            if fluxo <= 0:
                continue
            v_target = zona_to_osm_node[d_zona]
            path = paths.get(v_target)
            if not path:
                unreachable.append((o_zona, d_zona))
                continue
            # acumula fluxo nas arestas do caminho
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                key = (u, v)
                edge_loads[key] = edge_loads.get(key, 0.0) + fluxo
                edge_od_pairs.setdefault(key, []).append(f"{o_zona}->{d_zona}")
            paths_info.append((o_zona, d_zona, fluxo, path))

    # Constroi DataFrame das arestas
    rows = []
    for (u, v), load in edge_loads.items():
        # tenta extrair geometria e atributos da aresta
        edge_data = osm_graph.get_edge_data(u, v) or osm_graph.get_edge_data(v, u)
        if isinstance(edge_data, dict):
            # MultiDiGraph: pode ter chaves 0, 1, ...
            first_key = next(iter(edge_data))
            attr = edge_data[first_key] if isinstance(edge_data.get(first_key), dict) else edge_data
        else:
            attr = {}
        nome_via = attr.get("name", "")
        if isinstance(nome_via, list):
            nome_via = nome_via[0] if nome_via else ""
        rows.append({
            "u": u,
            "v": v,
            "nome_via": str(nome_via),
            "highway": str(attr.get("highway", "")),
            "comprimento_m": round(float(attr.get("length", 0)), 1),
            "fluxo_acumulado": round(load, 2),
            "n_pares_od": len(edge_od_pairs[(u, v)]),
            "pares_od": ", ".join(edge_od_pairs[(u, v)][:5]) + (
                "..." if len(edge_od_pairs[(u, v)]) > 5 else ""
            ),
        })
    edges_df = pd.DataFrame(rows).sort_values("fluxo_acumulado", ascending=False)
    return {
        "edge_loads": edges_df,
        "paths": paths_info,
        "unreachable": unreachable,
        "zona_to_osm_node": zona_to_osm_node,
    }


def edges_to_geodataframe(edges_df: pd.DataFrame, osm_graph) -> Optional[gpd.GeoDataFrame]:
    """Converte o DataFrame de arestas para GeoDataFrame com geometrias."""
    if not OSMNX_AVAILABLE or osm_graph is None or edges_df is None or edges_df.empty:
        return None
    rows = []
    for _, r in edges_df.iterrows():
        u, v = r["u"], r["v"]
        edge_data = osm_graph.get_edge_data(u, v) or osm_graph.get_edge_data(v, u)
        geom = None
        if isinstance(edge_data, dict):
            first_key = next(iter(edge_data))
            attr = edge_data[first_key] if isinstance(edge_data.get(first_key), dict) else edge_data
            geom = attr.get("geometry")
        if geom is None:
            try:
                u_data = osm_graph.nodes[u]
                v_data = osm_graph.nodes[v]
                geom = LineString([(u_data["x"], u_data["y"]),
                                   (v_data["x"], v_data["y"])])
            except Exception:
                continue
        rows.append({
            "fluxo_acumulado": r["fluxo_acumulado"],
            "n_pares_od": r["n_pares_od"],
            "nome_via": r["nome_via"],
            "comprimento_m": r["comprimento_m"],
            "geometry": geom,
        })
    if not rows:
        return None
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def classify_load_levels(edges_df: pd.DataFrame, n_classes: int = 3) -> pd.DataFrame:
    """Adiciona coluna 'classe_carga' (1=baixo, 2=medio, 3=alto)."""
    if edges_df is None or edges_df.empty:
        return edges_df
    out = edges_df.copy()
    fluxos = out["fluxo_acumulado"].astype(float)
    if fluxos.max() <= 0:
        out["classe_carga"] = 1
        return out
    try:
        out["classe_carga"] = pd.qcut(
            fluxos.rank(method="first"),
            q=n_classes,
            labels=list(range(1, n_classes + 1)),
        ).astype(int)
    except Exception:
        # fallback: usa quantis simples
        q33 = fluxos.quantile(0.33)
        q66 = fluxos.quantile(0.66)
        def cl(x):
            if x <= q33: return 1
            if x <= q66: return 2
            return 3
        out["classe_carga"] = fluxos.apply(cl).astype(int)
    return out
