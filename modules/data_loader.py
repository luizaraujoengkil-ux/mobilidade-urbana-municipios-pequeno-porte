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


def load_sample_layers() -> dict:
    """Carrega todas as camadas de exemplo de Matias Barbosa."""
    layers = {
        "area_estudo": _safe_read(DEMO_DIR / "area_estudo.geojson"),
        "zonas": _safe_read(DEMO_DIR / "zonas.geojson"),
        "ferrovia": _safe_read(DEMO_DIR / "ferrovia.geojson"),
        "rodovias": _safe_read(DEMO_DIR / "rodovias.geojson"),
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
