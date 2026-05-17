"""Carregamento dos dados iniciais e dos arquivos enviados pelo usuario."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from . import kmz_utils

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEMO_DIR = DATA_DIR / "demo_matias_barbosa"
# alias antigo (compat)
SAMPLE_DIR = DEMO_DIR
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _safe_read(path: Path) -> Optional[gpd.GeoDataFrame]:
    if not path.exists():
        return None
    try:
        return gpd.read_file(path)
    except Exception as exc:  # pragma: no cover - fallback amigavel
        print(f"[data_loader] Falha lendo {path}: {exc}")
        return None


def _load_area_estudo() -> Optional[gpd.GeoDataFrame]:
    """Carrega a area de estudo. Prefere o KMZ real se existir, com fallback
    automatico para area_estudo.geojson.

    Procura por arquivos KMZ na pasta demo com prefixo 'area_de_estudo'
    (tolera 'area_de_estudo_matias_barbosa.kmz' ou variantes com extensao
    dupla como '.kmz.kmz').
    """
    geojson_path = DEMO_DIR / "area_estudo.geojson"
    kmz_path = kmz_utils.find_area_kmz(DEMO_DIR, prefix="area_de_estudo")

    if kmz_path is not None:
        gdf = kmz_utils.load_polygon_from_kmz(
            kmz_path,
            fallback_to_geojson=geojson_path if geojson_path.exists() else None,
            name="Area de Estudo",
        )
        if gdf is not None and not gdf.empty:
            return gdf
        # Se chegou aqui, KMZ existe mas leitura falhou - aviso discreto
        print(
            f"[data_loader] KMZ da area de estudo encontrado em {kmz_path} "
            f"mas nao pode ser lido. Usando GeoJSON padrao."
        )

    # Fallback: GeoJSON original (comportamento anterior)
    return _safe_read(geojson_path)


def _load_ferrovia() -> Optional[gpd.GeoDataFrame]:
    """Carrega a ferrovia. Prefere KMZ real se existir.

    Procura por arquivos KMZ na pasta demo com prefixos:
    'ferrovia', 'linha_do_trem', 'linha_ferrea', 'trem'.
    Fallback: data/demo_matias_barbosa/ferrovia.geojson.
    """
    geojson_path = DEMO_DIR / "ferrovia.geojson"
    kmz_path = kmz_utils.find_kmz_by_prefixes(
        DEMO_DIR,
        prefixes=["ferrovia", "linha_do_trem", "linha_ferrea", "linha-ferrea",
                  "linha_trem", "trem", "railway"],
    )
    if kmz_path is not None:
        gdf = kmz_utils.load_lines_from_kmz(
            kmz_path,
            fallback_to_geojson=geojson_path if geojson_path.exists() else None,
            default_name="Linha do Trem",
        )
        if gdf is not None and not gdf.empty:
            return gdf
        print(f"[data_loader] KMZ da ferrovia em {kmz_path} nao pode ser lido. Usando GeoJSON.")
    return _safe_read(geojson_path)


def _load_rodovias() -> Optional[gpd.GeoDataFrame]:
    """Carrega as rodovias (BR-040, MG-353, Uniao Industria...).

    Prefere KMZ real se existir. Procura por prefixos:
    'rodovias', 'rodovia', 'br_040', 'br040', 'br-040', 'mg_353', 'mg353',
    'uniao_industria', 'uniao-industria'.
    Fallback: data/demo_matias_barbosa/rodovias.geojson.
    """
    geojson_path = DEMO_DIR / "rodovias.geojson"
    kmz_path = kmz_utils.find_kmz_by_prefixes(
        DEMO_DIR,
        prefixes=["rodovias", "rodovia", "br_040", "br040", "br-040",
                  "mg_353", "mg353", "mg-353",
                  "uniao_industria", "uniao-industria", "uniaoindustria"],
    )
    if kmz_path is not None:
        gdf = kmz_utils.load_lines_from_kmz(
            kmz_path,
            fallback_to_geojson=geojson_path if geojson_path.exists() else None,
            default_name="Rodovia",
        )
        if gdf is not None and not gdf.empty:
            return gdf
        print(f"[data_loader] KMZ de rodovias em {kmz_path} nao pode ser lido. Usando GeoJSON.")
    return _safe_read(geojson_path)


def load_sample_layers() -> dict:
    """Carrega todas as camadas de exemplo de Matias Barbosa.

    Para cada camada, prefere KMZ real se existir na pasta demo;
    senao, cai automaticamente para o GeoJSON sintetico.
    """
    layers = {
        "area_estudo": _load_area_estudo(),
        "zonas": _safe_read(DEMO_DIR / "zonas.geojson"),
        "ferrovia": _load_ferrovia(),
        "rodovias": _load_rodovias(),
        "pontos_viaduto": _safe_read(DEMO_DIR / "pontos_viaduto.geojson"),
        "pontos_interesse": _safe_read(DEMO_DIR / "pontos_interesse.geojson"),
    }
    return layers


def load_geojson(path: str | os.PathLike) -> gpd.GeoDataFrame:
    return gpd.read_file(path)


def load_kml(path: str | os.PathLike) -> gpd.GeoDataFrame:
    """Le KML usando driver KML do fiona/geopandas."""
    return kmz_utils.read_kml(path)


def load_kmz(path: str | os.PathLike) -> gpd.GeoDataFrame:
    return kmz_utils.read_kmz(path)


def load_csv_points(path: str | os.PathLike) -> gpd.GeoDataFrame:
    """Carrega CSV com colunas nome/tipo/latitude/longitude/descricao."""
    df = pd.read_csv(path)
    cols = {c.lower(): c for c in df.columns}
    lat_col = next((cols[k] for k in ("latitude", "lat", "y") if k in cols), None)
    lon_col = next((cols[k] for k in ("longitude", "lon", "lng", "x") if k in cols), None)
    if not lat_col or not lon_col:
        raise ValueError("CSV deve ter colunas latitude/longitude (ou lat/lon).")
    df = df.dropna(subset=[lat_col, lon_col])
    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    return gdf


def load_uploaded_file(uploaded_file) -> gpd.GeoDataFrame:
    """Recebe um arquivo do streamlit (UploadedFile) e devolve um GeoDataFrame."""
    name = uploaded_file.name.lower()
    dest = UPLOAD_DIR / uploaded_file.name
    with open(dest, "wb") as fh:
        fh.write(uploaded_file.getbuffer())

    if name.endswith(".geojson") or name.endswith(".json"):
        return load_geojson(dest)
    if name.endswith(".kml"):
        return load_kml(dest)
    if name.endswith(".kmz"):
        return load_kmz(dest)
    if name.endswith(".csv"):
        return load_csv_points(dest)

    raise ValueError(f"Formato nao suportado: {uploaded_file.name}")
