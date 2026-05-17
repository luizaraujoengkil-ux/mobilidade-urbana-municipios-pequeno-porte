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


def _load_zonas() -> Optional[gpd.GeoDataFrame]:
    """Carrega as zonas analiticas. Prefere KMZ real (com polygons z1, z2,
    z3, z4) e cai para o GeoJSON.

    Aceita TANTO:
    - 1 KMZ master 'zonas.kmz' com varios polygons dentro
    - VARIOS KMZ um por zona ('z1.kmz', 'z2.kmz', 'z2a.kmz', 'z3.kmz', ...)
      todos sao lidos e combinados.

    Estrategia para o KMZ real:
    - Le todos os Polygons preservando nome (placemark)
    - Normaliza o codigo da zona: 'z1' -> 'Z1', 'Z3' -> 'Z3', etc.
    - Multiplos polygons com mesmo codigo viram MultiPolygon (uniao geometrica)
    - Adiciona propriedades padrao (tipo/geracao/atracao/populacao) que o
      usuario pode editar na aba Matriz O-D depois.
    """
    geojson_path = DEMO_DIR / "zonas.geojson"
    kmz_paths = kmz_utils.find_all_kmzs_by_prefixes(
        DEMO_DIR,
        prefixes=[
            "zonas", "zonas_analiticas", "zoneamento", "zonas_matias",
            # cada zona como arquivo individual
            "z1", "z2", "z3", "z4", "z5", "z6", "z_",
        ],
    )
    if kmz_paths:
        # Le todos os KMZ encontrados e empilha em um unico GeoDataFrame
        frames = []
        for kmz_path in kmz_paths:
            gdf_part = kmz_utils.load_polygons_from_kmz(kmz_path)
            if gdf_part is not None and not gdf_part.empty:
                frames.append(gdf_part)
        if frames:
            gdf = gpd.GeoDataFrame(
                pd.concat(frames, ignore_index=True),
                crs=frames[0].crs or "EPSG:4326",
            )
        else:
            gdf = None
        if gdf is not None and not gdf.empty:
            # 1) Normaliza codigo de zona a partir do nome (z1, Z1, z 1 -> Z1)
            zona_codes = (
                gdf["nome"].astype(str).str.strip().str.upper()
                                       .str.replace(r"\s+", "", regex=True)
            )
            gdf = gdf.assign(zona=zona_codes)

            # 2) Mantem so codigos que parecem zonas (Z1, Z2, ..., ou Z10 etc.)
            mask_zona = gdf["zona"].str.match(r"^Z\d+[A-Z]?$")
            if mask_zona.any():
                gdf = gdf[mask_zona].copy()

            # 3) Junta multiplos polygons do mesmo codigo em MultiPolygon
            try:
                dissolved = gdf.dissolve(by="zona", aggfunc="first").reset_index()
            except Exception as exc:
                print(f"[data_loader] dissolve falhou: {exc} - usando polygons separados")
                dissolved = gdf

            # 4) Adiciona campos padrao para o modelo O-D
            cor_default = {
                "Z1": "#B83DBA", "Z2": "#F4A261", "Z3": "#F2D544", "Z4": "#E63946",
            }
            for col, default in [
                ("tipo", "Misto"),
                ("geracao", 50.0),
                ("atracao", 50.0),
                ("populacao", 1000.0),
                ("empregos", 0.0),
                ("funcao_od", "origem e destino"),
                ("observacoes", "Geometria real do KMZ - editar pesos na aba Matriz O-D"),
            ]:
                if col not in dissolved.columns:
                    dissolved[col] = default
            if "cor" not in dissolved.columns:
                dissolved["cor"] = dissolved["zona"].map(cor_default).fillna("#9E9E9E")
            return dissolved
        print(f"[data_loader] KMZ(s) de zonas em {kmz_paths} nao pode(m) ser lido(s). Usando GeoJSON.")
    return _safe_read(geojson_path)


def _load_pontos_viaduto() -> Optional[gpd.GeoDataFrame]:
    """Carrega os pontos de estudo de viaduto. Prefere KMZ(s) real(is).

    Aceita TANTO:
    - 1 KMZ master 'pontos_viaduto.kmz' com varios pontos dentro
    - VARIOS KMZ um por ponto ('ponto de estudo 1 de viaduto.kmz', etc.)

    Tambem aceita Placemarks com LineString (em vez de Point): converte
    automaticamente para Point no centroide da linha. Util quando o
    usuario desenhou linhas no Google Earth para representar viadutos.
    """
    geojson_path = DEMO_DIR / "pontos_viaduto.geojson"
    kmz_paths = kmz_utils.find_all_kmzs_by_prefixes(
        DEMO_DIR,
        prefixes=[
            "pontos_viaduto", "pontos_de_viaduto", "viaduto", "viadutos",
            "estudo_viaduto", "estudo_de_viaduto", "pontos_de_estudo",
            "ponto_de_estudo", "pontos_estudo", "ponto_viaduto",
        ],
    )
    if kmz_paths:
        frames = []
        for kp in kmz_paths:
            part = kmz_utils.load_points_from_kmz(kp, accept_lines_as_points=True)
            if part is not None and not part.empty:
                frames.append(part)
        if frames:
            gdf = gpd.GeoDataFrame(
                pd.concat(frames, ignore_index=True),
                crs=frames[0].crs or "EPSG:4326",
            )
            if "categoria" not in gdf.columns:
                gdf["categoria"] = "Estudo de viaduto"
            return gdf
        print(f"[data_loader] KMZ(s) de viaduto em {kmz_paths} nao pode(m) ser lido(s). Usando GeoJSON.")
    return _safe_read(geojson_path)


def _load_pontos_interesse() -> Optional[gpd.GeoDataFrame]:
    """Carrega os pontos de interesse. Prefere KMZ real."""
    geojson_path = DEMO_DIR / "pontos_interesse.geojson"
    kmz_path = kmz_utils.find_kmz_by_prefixes(
        DEMO_DIR,
        prefixes=[
            "pontos_interesse", "pontos_de_interesse", "poi", "pois",
            "interesse", "pontos_relevantes",
        ],
    )
    if kmz_path is not None:
        gdf = kmz_utils.load_points_from_kmz(
            kmz_path,
            fallback_to_geojson=geojson_path if geojson_path.exists() else None,
        )
        if gdf is not None and not gdf.empty:
            if "categoria" not in gdf.columns:
                gdf["categoria"] = "Outro"
            return gdf
        print(f"[data_loader] KMZ de POIs em {kmz_path} nao pode ser lido. Usando GeoJSON.")
    return _safe_read(geojson_path)


def load_sample_layers() -> dict:
    """Carrega todas as camadas de exemplo de Matias Barbosa.

    Para cada camada, prefere KMZ real se existir na pasta demo;
    senao, cai automaticamente para o GeoJSON sintetico. Permite ao
    usuario substituir qualquer camada pelo seu KMZ original do Google
    Earth/QGIS sem editar nenhum codigo.
    """
    layers = {
        "area_estudo":     _load_area_estudo(),
        "zonas":           _load_zonas(),
        "ferrovia":        _load_ferrovia(),
        "rodovias":        _load_rodovias(),
        "pontos_viaduto":  _load_pontos_viaduto(),
        "pontos_interesse": _load_pontos_interesse(),
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
