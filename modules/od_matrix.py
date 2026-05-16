"""Matriz Origem-Destino simplificada (modelo gravitacional)."""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia haversine em km entre dois pontos lat/lon."""
    R = 6371.0
    lat1r, lon1r, lat2r, lon2r = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = sin(dlat / 2) ** 2 + cos(lat1r) * cos(lat2r) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c


def zone_centroids(zonas_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Retorna DataFrame com zona/lat/lon dos centroides em EPSG:4326."""
    if zonas_gdf is None or zonas_gdf.empty:
        return pd.DataFrame(columns=["zona", "lat", "lon"])
    g = zonas_gdf.copy()
    if g.crs is None:
        g = g.set_crs("EPSG:4326")
    g = g.to_crs("EPSG:4326")
    centroids = g.geometry.centroid
    return pd.DataFrame({
        "zona": g["zona"].astype(str),
        "nome": g.get("nome", g["zona"]).astype(str),
        "lat": centroids.y.values,
        "lon": centroids.x.values,
    })


def build_distance_matrix(zonas_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Matriz de distancia euclidiana (haversine) entre centroides das zonas (km)."""
    cents = zone_centroids(zonas_gdf)
    zonas = cents["zona"].tolist()
    n = len(zonas)
    mat = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i == j:
                mat[i, j] = 0.0
            else:
                mat[i, j] = haversine_km(
                    cents.iloc[i]["lat"], cents.iloc[i]["lon"],
                    cents.iloc[j]["lat"], cents.iloc[j]["lon"],
                )
    df = pd.DataFrame(mat, index=zonas, columns=zonas)
    return df


def gravity_od(
    zonas_df: pd.DataFrame,
    distancias: pd.DataFrame,
    beta: float = 2.0,
    normalize: bool = True,
) -> pd.DataFrame:
    """Modelo gravitacional: Tij = (Gi * Aj) / dij^beta.

    Espera DataFrame com colunas: zona, geracao, atracao.
    """
    zonas_all = zonas_df["zona"].astype(str).tolist()
    # Apenas zonas que existem na matriz de distancias (calculadas a partir do GeoDataFrame)
    zonas = [z for z in zonas_all if z in distancias.index]
    G = zonas_df.set_index("zona")["geracao"].astype(float)
    A = zonas_df.set_index("zona")["atracao"].astype(float)
    od = pd.DataFrame(0.0, index=zonas, columns=zonas)
    for i in zonas:
        for j in zonas:
            if i == j:
                od.loc[i, j] = 0.0
                continue
            d = float(distancias.loc[i, j])
            if d <= 0:
                d = 0.1
            od.loc[i, j] = (G[i] * A[j]) / (d ** beta)
    if normalize:
        total = od.values.sum()
        if total > 0:
            od = od / total * 100.0  # percentual relativo do total de viagens
    return od.round(3)


def od_summary(od: pd.DataFrame) -> pd.DataFrame:
    """Resumo: viagens geradas e atraidas por zona."""
    gerada = od.sum(axis=1)
    atraida = od.sum(axis=0)
    df = pd.DataFrame({"viagens_geradas": gerada, "viagens_atraidas": atraida})
    df["saldo"] = df["viagens_atraidas"] - df["viagens_geradas"]
    return df.round(3)


def od_flow_records(od: pd.DataFrame, zonas_gdf: gpd.GeoDataFrame, threshold: float = 0.0) -> list:
    """Converte matriz O-D em lista de registros para desenhar linhas no mapa."""
    cents = zone_centroids(zonas_gdf).set_index("zona")
    records = []
    for i in od.index:
        for j in od.columns:
            if i == j:
                continue
            flow = float(od.loc[i, j])
            if flow <= threshold:
                continue
            if i not in cents.index or j not in cents.index:
                continue
            records.append({
                "from": i,
                "to": j,
                "flow": flow,
                "from_lat": cents.loc[i, "lat"],
                "from_lon": cents.loc[i, "lon"],
                "to_lat": cents.loc[j, "lat"],
                "to_lon": cents.loc[j, "lon"],
            })
    return records


def default_zonas_dataframe(zonas_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Constroi DataFrame editavel a partir do GeoDataFrame de zonas."""
    if zonas_gdf is None or zonas_gdf.empty:
        return pd.DataFrame(columns=["zona", "nome", "tipo", "geracao", "atracao", "populacao", "observacoes"])
    df = pd.DataFrame({
        "zona": zonas_gdf.get("zona", "").astype(str),
        "nome": zonas_gdf.get("nome", "").astype(str),
        "tipo": zonas_gdf.get("tipo", "").astype(str),
        "geracao": zonas_gdf.get("geracao", 1).astype(float),
        "atracao": zonas_gdf.get("atracao", 1).astype(float),
        "populacao": zonas_gdf.get("populacao", 0).astype(float),
        "observacoes": zonas_gdf.get("observacoes", "").astype(str),
    })
    return df
