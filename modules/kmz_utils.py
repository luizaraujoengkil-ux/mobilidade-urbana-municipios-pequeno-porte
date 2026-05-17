"""Leitura de arquivos KML e KMZ.

Tenta usar pyogrio (default no geopandas 1.0+) ou fiona. Em ambientes que
nao tenham nenhum dos dois com suporte a KML, cai num fallback que apenas
delega para geopandas.read_file.

Tambem oferece um leitor minimo (bibliotecas padrao) que extrai apenas
poligonos do KML/KMZ sem depender de driver GDAL - util quando o ambiente
do Streamlit Cloud nao tem suporte completo a KML.
"""
from __future__ import annotations

import os
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon, MultiPolygon

try:
    import fiona  # type: ignore
    HAS_FIONA = True
except Exception:
    HAS_FIONA = False

try:
    import pyogrio  # type: ignore
    HAS_PYOGRIO = True
except Exception:
    HAS_PYOGRIO = False


def _enable_kml_driver() -> None:
    """Habilita driver KML no fiona, se disponivel."""
    if not HAS_FIONA:
        return
    try:
        fiona.drvsupport.supported_drivers["KML"] = "rw"
        fiona.drvsupport.supported_drivers["LIBKML"] = "rw"
    except Exception:
        pass


def _list_layers(path: str) -> list:
    if HAS_PYOGRIO:
        try:
            info = pyogrio.list_layers(path)
            return [row[0] for row in info]
        except Exception:
            pass
    if HAS_FIONA:
        try:
            return fiona.listlayers(path)
        except Exception:
            pass
    return [None]


def read_kml(path: str | os.PathLike) -> gpd.GeoDataFrame:
    _enable_kml_driver()
    path = str(path)

    layer_names = _list_layers(path)
    frames = []
    for ln in layer_names:
        try:
            if ln is None:
                gdf = gpd.read_file(path)
            else:
                gdf = gpd.read_file(path, layer=ln)
            if not gdf.empty:
                gdf["__layer__"] = ln if ln else "kml"
                frames.append(gdf)
        except Exception:
            continue
    if not frames:
        return gpd.read_file(path)
    return gpd.GeoDataFrame(
        pd.concat(frames, ignore_index=True), crs=frames[0].crs
    )


# ---------------------------------------------------------------------------
# Leitor MINIMO de poligonos KML/KMZ usando apenas stdlib (zipfile + xml).
# Util como fallback quando driver KML do GDAL nao esta disponivel.
# ---------------------------------------------------------------------------
_KML_NS = "{http://www.opengis.net/kml/2.2}"


def _parse_coordinates_text(text: str) -> list:
    """Converte o texto <coordinates> KML em lista de (lon, lat).

    KML aceita formato 'lon,lat[,alt]' separado por espacos/quebras de linha.
    """
    pts = []
    if not text:
        return pts
    for token in text.replace("\n", " ").split():
        token = token.strip().strip(",")
        if not token:
            continue
        parts = token.split(",")
        if len(parts) < 2:
            continue
        try:
            lon = float(parts[0])
            lat = float(parts[1])
        except ValueError:
            continue
        pts.append((lon, lat))
    return pts


def _find_first_polygon_in_kml(kml_text: str) -> Optional[Polygon]:
    """Faz parse XML do KML e devolve o primeiro Polygon encontrado."""
    try:
        root = ET.fromstring(kml_text)
    except ET.ParseError:
        return None

    # Tenta com namespace KML 2.2; se nao achar, tenta sem namespace.
    polys = root.findall(f".//{_KML_NS}Polygon")
    if len(polys) == 0:
        polys = root.findall(".//Polygon")
    for poly in polys:
        # IMPORTANTE: usar 'is None' em vez de 'or' porque um Element XML
        # sem subelementos (so com .text) eh considerado falsy pelo Python.
        outer = poly.find(f"{_KML_NS}outerBoundaryIs/{_KML_NS}LinearRing/{_KML_NS}coordinates")
        if outer is None:
            outer = poly.find("outerBoundaryIs/LinearRing/coordinates")
        if outer is None or outer.text is None:
            continue
        outer_coords = _parse_coordinates_text(outer.text)
        if len(outer_coords) < 3:
            continue
        # Procura aneis internos (holes)
        inner_rings = []
        inner_elems = poly.findall(
            f"{_KML_NS}innerBoundaryIs/{_KML_NS}LinearRing/{_KML_NS}coordinates"
        )
        if len(inner_elems) == 0:
            inner_elems = poly.findall("innerBoundaryIs/LinearRing/coordinates")
        for inner in inner_elems:
            if inner.text is None:
                continue
            ring = _parse_coordinates_text(inner.text)
            if len(ring) >= 3:
                inner_rings.append(ring)
        try:
            return Polygon(outer_coords, inner_rings)
        except Exception:
            continue
    return None


def load_polygon_from_kmz(kmz_path: str | os.PathLike,
                          fallback_to_geojson: Optional[str | os.PathLike] = None,
                          name: str = "Area de Estudo") -> Optional[gpd.GeoDataFrame]:
    """Le o primeiro Polygon de um KMZ e retorna como GeoDataFrame (EPSG:4326).

    Args:
        kmz_path: caminho do .kmz
        fallback_to_geojson: caminho de um .geojson alternativo se o KMZ
            falhar. Se None, retorna None.
        name: rotulo do Polygon no GeoDataFrame.

    Returns:
        GeoDataFrame com 1 feicao Polygon, ou None se nada conseguir ler.
    """
    p = Path(kmz_path)
    poly: Optional[Polygon] = None

    if p.exists():
        try:
            with zipfile.ZipFile(p, "r") as zf:
                # KML padrao se chama doc.kml mas aceitamos qualquer .kml
                kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
                for kml_name in kml_names:
                    try:
                        with zf.open(kml_name) as fh:
                            kml_text = fh.read().decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    poly = _find_first_polygon_in_kml(kml_text)
                    if poly is not None:
                        break
        except Exception as exc:
            print(f"[kmz_utils] Falha ao abrir {p}: {exc}")
            poly = None
    else:
        print(f"[kmz_utils] KMZ nao encontrado em {p}")

    if poly is not None:
        gdf = gpd.GeoDataFrame(
            {
                "nome": [name],
                "descricao": ["Area de estudo - geometria real importada do KMZ"],
                "source": ["KMZ real"],
            },
            geometry=[poly],
            crs="EPSG:4326",
        )
        return gdf

    # Fallback para o GeoJSON existente, se fornecido
    if fallback_to_geojson is not None:
        fp = Path(fallback_to_geojson)
        if fp.exists():
            try:
                return gpd.read_file(fp)
            except Exception as exc:
                print(f"[kmz_utils] Fallback GeoJSON falhou em {fp}: {exc}")
    return None


def find_area_kmz(folder: str | os.PathLike, prefix: str = "area_de_estudo") -> Optional[Path]:
    """Procura na pasta o primeiro arquivo .kmz cujo nome comeca com 'prefix'.

    Tolera nomenclatura variavel (ex: 'area_de_estudo_matias_barbosa.kmz' ou
    'area_de_estudo_matias_barbosa.kmz.kmz' - extensao dupla acidental).
    """
    folder_path = Path(folder)
    if not folder_path.is_dir():
        return None
    candidates = sorted(folder_path.glob(f"{prefix}*"))
    for c in candidates:
        if c.name.lower().endswith(".kmz") and c.is_file():
            return c
    return None


def read_kmz(path: str | os.PathLike) -> gpd.GeoDataFrame:
    """Extrai um KMZ e le o(s) KML interno(s)."""
    path = Path(path)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(path, "r") as zf:
            zf.extractall(tmp)
        kml_files = list(Path(tmp).rglob("*.kml"))
        if not kml_files:
            raise ValueError("KMZ nao contem arquivo .kml interno.")
        frames = []
        for kml in kml_files:
            try:
                gdf = read_kml(kml)
                if not gdf.empty:
                    frames.append(gdf)
            except Exception:
                continue
        if not frames:
            raise ValueError("Nao foi possivel ler nenhum KML dentro do KMZ.")
        if len(frames) == 1:
            return frames[0]
        return gpd.GeoDataFrame(
            pd.concat(frames, ignore_index=True), crs=frames[0].crs
        )
