"""Construcao e analise do grafo viario via OSMnx/NetworkX."""
from __future__ import annotations

from typing import Optional

import geopandas as gpd
import networkx as nx
import pandas as pd
from shapely.geometry import LineString, Point

from .od_matrix import haversine_km

# OSMnx eh opcional: se nao estiver instalado / sem internet,
# o sistema cai num grafo sintetico simples ligando centroides das zonas
# e pontos de viaduto, para que o prototipo continue funcionando offline.
try:
    import osmnx as ox
    OSMNX_AVAILABLE = True
except Exception:  # pragma: no cover
    OSMNX_AVAILABLE = False


def download_osm_graph(
    place: str = "Matias Barbosa, Minas Gerais, Brazil",
    network_type: str = "drive",
) -> Optional[nx.MultiDiGraph]:
    """Baixa o grafo viario do OSM via OSMnx (requer internet)."""
    if not OSMNX_AVAILABLE:
        return None
    try:
        G = ox.graph_from_place(place, network_type=network_type)
        return G
    except Exception:
        try:
            # fallback: bbox aproximada de Matias Barbosa
            G = ox.graph_from_bbox(
                north=-21.85, south=-21.90, east=-43.28, west=-43.34,
                network_type=network_type,
            )
            return G
        except Exception:
            return None


def graph_to_geodataframes(G: nx.MultiDiGraph) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    if G is None or not OSMNX_AVAILABLE:
        return gpd.GeoDataFrame(), gpd.GeoDataFrame()
    nodes, edges = ox.graph_to_gdfs(G)
    return nodes, edges


def build_synthetic_graph(
    zonas_gdf: gpd.GeoDataFrame,
    pontos_viaduto: Optional[gpd.GeoDataFrame] = None,
) -> nx.Graph:
    """Constroi grafo simples ligando centroides das zonas + pontos chave.

    Util quando OSMnx nao esta disponivel ou nao se quer carregar a malha completa.
    """
    G = nx.Graph()
    if zonas_gdf is None or zonas_gdf.empty:
        return G

    g = zonas_gdf.to_crs("EPSG:4326").copy()
    g["centroid"] = g.geometry.centroid
    nodes = []
    for _, row in g.iterrows():
        node_id = f"Z:{row['zona']}"
        G.add_node(node_id, lat=row.centroid.y, lon=row.centroid.x, tipo="zona", nome=row.get("nome", row["zona"]))
        nodes.append(node_id)

    if pontos_viaduto is not None and not pontos_viaduto.empty:
        for idx, row in pontos_viaduto.iterrows():
            node_id = f"V:{row.get('nome', idx)}"
            G.add_node(node_id, lat=row.geometry.y, lon=row.geometry.x, tipo="viaduto", nome=row.get("nome", str(idx)))
            nodes.append(node_id)

    # Conexao "full mesh" ponderada por distancia haversine (rede teorica base)
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            dist = haversine_km(G.nodes[a]["lat"], G.nodes[a]["lon"], G.nodes[b]["lat"], G.nodes[b]["lon"])
            G.add_edge(a, b, weight=dist, length_km=dist, tipo="base")
    return G


def add_intervention_edge(
    G: nx.Graph,
    from_node: str,
    to_node: str,
    factor: float = 0.5,
    tipo: str = "viaduto",
) -> nx.Graph:
    """Adiciona/atualiza aresta representando uma intervencao.

    factor < 1 reduz o custo (atalho fisico, ex: viaduto que elimina barreira);
    factor > 1 representa restricao/bloqueio.
    """
    if from_node not in G.nodes or to_node not in G.nodes:
        raise ValueError("Nos nao encontrados no grafo.")
    a = G.nodes[from_node]
    b = G.nodes[to_node]
    base = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
    weight = base * factor
    G.add_edge(from_node, to_node, weight=weight, length_km=base, tipo=tipo, factor=factor)
    return G


def block_edge(G: nx.Graph, from_node: str, to_node: str) -> nx.Graph:
    """Remove uma aresta (representa bloqueio)."""
    if G.has_edge(from_node, to_node):
        G.remove_edge(from_node, to_node)
    return G


def shortest_path_matrix(G: nx.Graph) -> pd.DataFrame:
    """Matriz de menor caminho ponderado entre todos os nos do grafo."""
    nodes = list(G.nodes)
    df = pd.DataFrame(index=nodes, columns=nodes, dtype=float)
    for n in nodes:
        try:
            lengths = nx.single_source_dijkstra_path_length(G, n, weight="weight")
        except Exception:
            lengths = {}
        for m in nodes:
            df.loc[n, m] = lengths.get(m, float("inf"))
    return df


def zone_distance_matrix(G: nx.Graph) -> pd.DataFrame:
    """Filtra a matriz de menor caminho apenas entre nos do tipo zona."""
    full = shortest_path_matrix(G)
    zona_nodes = [n for n, d in G.nodes(data=True) if d.get("tipo") == "zona"]
    return full.loc[zona_nodes, zona_nodes]


def average_zone_distance(G: nx.Graph) -> float:
    df = zone_distance_matrix(G)
    if df.empty:
        return 0.0
    vals = df.values
    mask = ~(vals == 0)
    finite_mask = mask & ~pd.isna(vals) & (vals != float("inf"))
    if finite_mask.sum() == 0:
        return 0.0
    return float(vals[finite_mask].mean())


def estimated_average_time(distance_km: float, speed_kmh: float = 30.0) -> float:
    """Tempo medio estimado em minutos para uma distancia media (km)."""
    if speed_kmh <= 0:
        return 0.0
    return distance_km / speed_kmh * 60.0


def connected_zone_count(G: nx.Graph) -> int:
    zona_nodes = [n for n, d in G.nodes(data=True) if d.get("tipo") == "zona"]
    if not zona_nodes:
        return 0
    sub = G.subgraph(zona_nodes)
    return nx.number_connected_components(sub) if len(zona_nodes) > 0 else 0


def list_graph_nodes(G: nx.Graph) -> list:
    return [(n, d.get("tipo", ""), d.get("nome", n)) for n, d in G.nodes(data=True)]
