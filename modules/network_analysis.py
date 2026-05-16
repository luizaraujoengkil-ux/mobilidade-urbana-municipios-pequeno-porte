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


def load_osm_network(
    lat: float,
    lon: float,
    radius_m: int = 1500,
    network_type: str = "drive",
) -> Optional[nx.MultiDiGraph]:
    """Baixa a malha viaria do OSM em um circulo ao redor de (lat, lon)."""
    if not OSMNX_AVAILABLE:
        return None
    try:
        G = ox.graph_from_point(
            (lat, lon),
            dist=radius_m,
            network_type=network_type,
            simplify=True,
        )
        return G
    except Exception:
        return None


def find_nearest_osm_node(G_osm: nx.MultiDiGraph, lat: float, lon: float):
    """Retorna o id do no OSM mais proximo de (lat, lon). None se indisponivel."""
    if not OSMNX_AVAILABLE or G_osm is None:
        return None
    try:
        return ox.distance.nearest_nodes(G_osm, X=lon, Y=lat)
    except Exception:
        return None


def graph_to_geodataframes(G: nx.MultiDiGraph) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]:
    if G is None or not OSMNX_AVAILABLE:
        return gpd.GeoDataFrame(), gpd.GeoDataFrame()
    nodes, edges = ox.graph_to_gdfs(G)
    return nodes, edges


def osm_edges_gdf(G_osm: nx.MultiDiGraph) -> Optional[gpd.GeoDataFrame]:
    """GeoDataFrame com as arestas do grafo OSM (para plotar no mapa)."""
    if G_osm is None or not OSMNX_AVAILABLE:
        return None
    try:
        _, edges = ox.graph_to_gdfs(G_osm, nodes=False, edges=True)
        return edges
    except Exception:
        return None


def build_analysis_graph(
    zonas_gdf: gpd.GeoDataFrame,
    pontos_viaduto: Optional[gpd.GeoDataFrame] = None,
    osm_graph: Optional[nx.MultiDiGraph] = None,
    user_points_df: Optional[pd.DataFrame] = None,
    infra_categories: Optional[set] = None,
) -> nx.Graph:
    """Constroi grafo combinando OSM (se disponivel) + nos analiticos.

    - Se OSM disponivel: usa a malha viaria real como base. Cada zona / ponto
      de viaduto e conectado ao no OSM mais proximo por um 'connector'.
      Distancias entre zonas passam a refletir o trajeto pelas ruas.
    - Se OSM indisponivel: cai no comportamento sintetico (mesh haversine).
    """
    G = nx.Graph()

    # --- 1. Importa nos e arestas do OSM (se disponivel) ----------------
    has_osm = osm_graph is not None and OSMNX_AVAILABLE
    if has_osm:
        for n, data in osm_graph.nodes(data=True):
            G.add_node(
                f"OSM:{n}",
                lat=data.get("y"),
                lon=data.get("x"),
                tipo="osm",
            )
        for u, v, data in osm_graph.edges(data=True):
            length_m = data.get("length", 0)
            length_km = length_m / 1000.0 if length_m else haversine_km(
                osm_graph.nodes[u]["y"], osm_graph.nodes[u]["x"],
                osm_graph.nodes[v]["y"], osm_graph.nodes[v]["x"],
            )
            u_id, v_id = f"OSM:{u}", f"OSM:{v}"
            # mantem so a aresta mais curta entre o par (Graph nao-direcionado)
            if G.has_edge(u_id, v_id):
                if length_km < G[u_id][v_id]["weight"]:
                    G[u_id][v_id]["weight"] = length_km
                    G[u_id][v_id]["length_km"] = length_km
            else:
                G.add_edge(u_id, v_id, weight=length_km, length_km=length_km, tipo="osm")

    # --- 2. Adiciona nos analiticos (zonas) -----------------------------
    analysis_nodes = []
    if zonas_gdf is not None and not zonas_gdf.empty:
        g = zonas_gdf.to_crs("EPSG:4326").copy()
        g["centroid"] = g.geometry.centroid
        for _, row in g.iterrows():
            node_id = f"Z:{row['zona']}"
            lat, lon = float(row.centroid.y), float(row.centroid.x)
            G.add_node(node_id, lat=lat, lon=lon, tipo="zona",
                       nome=row.get("nome", row["zona"]))
            analysis_nodes.append(node_id)
            if has_osm:
                osm_id = find_nearest_osm_node(osm_graph, lat, lon)
                if osm_id is not None and f"OSM:{osm_id}" in G:
                    onode = osm_graph.nodes[osm_id]
                    dist = haversine_km(lat, lon, onode["y"], onode["x"])
                    G.add_edge(node_id, f"OSM:{osm_id}",
                               weight=dist, length_km=dist, tipo="connector")

    # --- 3. Adiciona pontos de viaduto (dataset de demonstracao) -------
    if pontos_viaduto is not None and not pontos_viaduto.empty:
        for idx, row in pontos_viaduto.iterrows():
            node_id = f"V:{row.get('nome', idx)}"
            lat, lon = float(row.geometry.y), float(row.geometry.x)
            G.add_node(node_id, lat=lat, lon=lon, tipo="viaduto",
                       nome=row.get("nome", str(idx)))
            analysis_nodes.append(node_id)
            if has_osm:
                osm_id = find_nearest_osm_node(osm_graph, lat, lon)
                if osm_id is not None and f"OSM:{osm_id}" in G:
                    onode = osm_graph.nodes[osm_id]
                    dist = haversine_km(lat, lon, onode["y"], onode["x"])
                    G.add_edge(node_id, f"OSM:{osm_id}",
                               weight=dist, length_km=dist, tipo="connector")

    # --- 3b. Adiciona pontos cadastrados pelo usuario com categoria
    #        de infraestrutura (viaduto / ponte / passagem / nova ligacao)
    if user_points_df is not None and not user_points_df.empty:
        infra = infra_categories if infra_categories is not None else set()
        for _, row in user_points_df.iterrows():
            cat = str(row.get("categoria", ""))
            if infra and cat not in infra:
                continue
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
            except Exception:
                continue
            nome = str(row.get("nome", "ponto")).strip() or "ponto"
            node_id = f"U:{nome}"
            # evita duplicacao se o usuario adicionou pontos com nomes iguais
            suffix = 1
            base_id = node_id
            while node_id in G.nodes:
                suffix += 1
                node_id = f"{base_id}#{suffix}"
            G.add_node(node_id, lat=lat, lon=lon, tipo="usuario",
                       nome=nome, categoria=cat)
            analysis_nodes.append(node_id)
            if has_osm:
                osm_id = find_nearest_osm_node(osm_graph, lat, lon)
                if osm_id is not None and f"OSM:{osm_id}" in G:
                    onode = osm_graph.nodes[osm_id]
                    dist = haversine_km(lat, lon, onode["y"], onode["x"])
                    G.add_edge(node_id, f"OSM:{osm_id}",
                               weight=dist, length_km=dist, tipo="connector")

    # --- 4. Fallback sem OSM: mesh haversine entre nos analiticos ------
    if not has_osm and analysis_nodes:
        for i, a in enumerate(analysis_nodes):
            for b in analysis_nodes[i + 1:]:
                dist = haversine_km(
                    G.nodes[a]["lat"], G.nodes[a]["lon"],
                    G.nodes[b]["lat"], G.nodes[b]["lon"],
                )
                G.add_edge(a, b, weight=dist, length_km=dist, tipo="base")

    return G


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
    """Matriz de menor caminho entre nos de zona, computada eficientemente.

    Faz Dijkstra apenas a partir dos nos de zona (em vez de todos os nos do
    grafo), o que e essencial quando o grafo contem milhares de nos OSM.
    """
    zona_nodes = [n for n, d in G.nodes(data=True) if d.get("tipo") == "zona"]
    if not zona_nodes:
        return pd.DataFrame()
    df = pd.DataFrame(index=zona_nodes, columns=zona_nodes, dtype=float)
    for n in zona_nodes:
        try:
            lengths = nx.single_source_dijkstra_path_length(G, n, weight="weight")
        except Exception:
            lengths = {}
        for m in zona_nodes:
            df.loc[n, m] = lengths.get(m, float("inf"))
    return df


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
