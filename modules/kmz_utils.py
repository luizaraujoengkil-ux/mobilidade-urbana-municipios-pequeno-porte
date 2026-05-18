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
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Optional

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, MultiLineString, Point, Polygon, MultiPolygon

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


def _find_first_line_in_kml(kml_text: str) -> list:
    """Retorna lista de (nome, descricao, LineString/MultiLineString) do KML.

    Suporta tags <LineString> e <MultiGeometry>/<LineString> (KML padrao).
    """
    try:
        root = ET.fromstring(kml_text)
    except ET.ParseError:
        return []

    out = []
    # Itera Placemarks para preservar nome/descricao
    placemarks = root.findall(f".//{_KML_NS}Placemark")
    if len(placemarks) == 0:
        placemarks = root.findall(".//Placemark")
    for pm in placemarks:
        nome_el = pm.find(f"{_KML_NS}name")
        if nome_el is None:
            nome_el = pm.find("name")
        nome = nome_el.text.strip() if (nome_el is not None and nome_el.text) else "(sem nome)"
        desc_el = pm.find(f"{_KML_NS}description")
        if desc_el is None:
            desc_el = pm.find("description")
        descricao = desc_el.text.strip() if (desc_el is not None and desc_el.text) else ""

        # Procura LineStrings (diretamente ou dentro de MultiGeometry)
        line_coords_elems = pm.findall(f".//{_KML_NS}LineString/{_KML_NS}coordinates")
        if len(line_coords_elems) == 0:
            line_coords_elems = pm.findall(".//LineString/coordinates")
        lines = []
        for elem in line_coords_elems:
            if elem.text is None:
                continue
            pts = _parse_coordinates_text(elem.text)
            if len(pts) >= 2:
                lines.append(LineString(pts))
        if not lines:
            continue
        geom = lines[0] if len(lines) == 1 else MultiLineString(lines)
        out.append((nome, descricao, geom))
    return out


def _find_points_in_kml(kml_text: str) -> list:
    """Retorna lista de (nome, descricao, Point) do KML."""
    try:
        root = ET.fromstring(kml_text)
    except ET.ParseError:
        return []
    out = []
    placemarks = root.findall(f".//{_KML_NS}Placemark")
    if len(placemarks) == 0:
        placemarks = root.findall(".//Placemark")
    for pm in placemarks:
        # IMPORTANTE: usar 'is None' em vez de 'or' - ET.Element sem filhos
        # eh considerado falsy mesmo tendo texto, o que fazia o 'or' cair
        # no fallback e retornar None (perdia o nome com namespace).
        nome_el = pm.find(f"{_KML_NS}name")
        if nome_el is None:
            nome_el = pm.find("name")
        nome = nome_el.text.strip() if (nome_el is not None and nome_el.text) else "(sem nome)"
        desc_el = pm.find(f"{_KML_NS}description")
        if desc_el is None:
            desc_el = pm.find("description")
        descricao = desc_el.text.strip() if (desc_el is not None and desc_el.text) else ""

        coord_el = pm.find(f"{_KML_NS}Point/{_KML_NS}coordinates")
        if coord_el is None:
            coord_el = pm.find("Point/coordinates")
        if coord_el is None or coord_el.text is None:
            continue
        pts = _parse_coordinates_text(coord_el.text)
        if not pts:
            continue
        out.append((nome, descricao, Point(pts[0])))
    return out


def load_lines_from_kmz(
    kmz_path: str | os.PathLike,
    fallback_to_geojson: Optional[str | os.PathLike] = None,
    default_name: str = "Linha",
    keep_geojson_properties: bool = True,
) -> Optional[gpd.GeoDataFrame]:
    """Le todas as LineStrings de um KMZ e retorna como GeoDataFrame EPSG:4326.

    Preserva nome/descricao de cada Placemark do KML.

    Args:
        kmz_path: caminho do .kmz
        fallback_to_geojson: caminho do .geojson alternativo caso o KMZ falhe
        default_name: nome a usar para Placemarks sem <name>
        keep_geojson_properties: se True e usar fallback GeoJSON, mantem todas
            as propriedades originais (incluindo 'categoria' das rodovias).
    """
    p = Path(kmz_path)
    found_lines: list = []

    if p.exists():
        try:
            with zipfile.ZipFile(p, "r") as zf:
                kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
                for kml_name in kml_names:
                    try:
                        with zf.open(kml_name) as fh:
                            kml_text = fh.read().decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    found_lines.extend(_find_first_line_in_kml(kml_text))
        except Exception as exc:
            print(f"[kmz_utils] Falha ao abrir {p}: {exc}")
    else:
        print(f"[kmz_utils] KMZ nao encontrado em {p}")

    if found_lines:
        rows = []
        for nome, descricao, geom in found_lines:
            rows.append({
                "nome": nome or default_name,
                "descricao": descricao,
                "tipo": "linha",
                "source": "KMZ real",
                "geometry": geom,
            })
        return gpd.GeoDataFrame(rows, crs="EPSG:4326")

    # Fallback: GeoJSON
    if fallback_to_geojson is not None:
        fp = Path(fallback_to_geojson)
        if fp.exists():
            try:
                return gpd.read_file(fp)
            except Exception as exc:
                print(f"[kmz_utils] Fallback GeoJSON falhou em {fp}: {exc}")
    return None


def _normalize_filename(s: str) -> str:
    """Normaliza string para comparacao: remove acentos, lowercase,
    substitui espacos/tracos/parenteses por '_'.
    """
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    for ch in (" ", "-", "(", ")", "[", "]"):
        s = s.replace(ch, "_")
    while "__" in s:
        s = s.replace("__", "_")
    return s


def find_all_kmzs_by_prefixes(folder: str | os.PathLike, prefixes: list) -> list:
    """Procura na pasta TODOS os arquivos .kmz cujo nome NORMALIZADO comeca
    com qualquer um dos prefixes da lista. Retorna lista de Paths ordenada.

    Util quando o usuario exporta cada feicao do Google Earth como KMZ
    separado (ex: z1.kmz, z2.kmz, z3.kmz, z3a.kmz, z4.kmz ...).
    """
    folder_path = Path(folder)
    if not folder_path.is_dir():
        return []
    normalized_prefixes = [_normalize_filename(p) for p in prefixes]
    result = []
    for entry in sorted(folder_path.iterdir()):
        if not entry.is_file():
            continue
        if not entry.name.lower().endswith(".kmz"):
            continue
        nname = _normalize_filename(entry.name)
        for pref in normalized_prefixes:
            if nname.startswith(pref):
                result.append(entry)
                break
    return result


def find_kmz_by_prefixes(folder: str | os.PathLike, prefixes: list) -> Optional[Path]:
    """Versao 'single' de find_all_kmzs_by_prefixes - retorna o primeiro."""
    matches = find_all_kmzs_by_prefixes(folder, prefixes)
    return matches[0] if matches else None


def _find_all_polygons_in_kml(kml_text: str) -> list:
    """Retorna lista de (nome, descricao, Polygon) - TODOS os polygons do KML.

    Cada Placemark com Polygon vira um item da lista.
    """
    try:
        root = ET.fromstring(kml_text)
    except ET.ParseError:
        return []
    out = []
    placemarks = root.findall(f".//{_KML_NS}Placemark")
    if len(placemarks) == 0:
        placemarks = root.findall(".//Placemark")
    for pm in placemarks:
        nome_el = pm.find(f"{_KML_NS}name")
        if nome_el is None:
            nome_el = pm.find("name")
        nome = nome_el.text.strip() if (nome_el is not None and nome_el.text) else "(sem nome)"
        desc_el = pm.find(f"{_KML_NS}description")
        if desc_el is None:
            desc_el = pm.find("description")
        descricao = desc_el.text.strip() if (desc_el is not None and desc_el.text) else ""

        # Pode haver mais de um Polygon dentro de um Placemark (MultiGeometry)
        poly_elems = pm.findall(f".//{_KML_NS}Polygon")
        if len(poly_elems) == 0:
            poly_elems = pm.findall(".//Polygon")
        for poly in poly_elems:
            outer = poly.find(f"{_KML_NS}outerBoundaryIs/{_KML_NS}LinearRing/{_KML_NS}coordinates")
            if outer is None:
                outer = poly.find("outerBoundaryIs/LinearRing/coordinates")
            if outer is None or outer.text is None:
                continue
            outer_coords = _parse_coordinates_text(outer.text)
            if len(outer_coords) < 3:
                continue
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
                out.append((nome, descricao, Polygon(outer_coords, inner_rings)))
            except Exception:
                continue
    return out


def load_polygons_from_kmz(
    kmz_path: str | os.PathLike,
    fallback_to_geojson: Optional[str | os.PathLike] = None,
) -> Optional[gpd.GeoDataFrame]:
    """Le TODOS os Polygons de um KMZ. Cada Placemark vira uma feicao
    preservando nome e descricao. Retorna GeoDataFrame EPSG:4326.
    """
    p = Path(kmz_path)
    found = []
    if p.exists():
        try:
            with zipfile.ZipFile(p, "r") as zf:
                kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
                for kml_name in kml_names:
                    try:
                        with zf.open(kml_name) as fh:
                            kml_text = fh.read().decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    found.extend(_find_all_polygons_in_kml(kml_text))
        except Exception as exc:
            print(f"[kmz_utils] Falha ao abrir {p}: {exc}")
    else:
        print(f"[kmz_utils] KMZ nao encontrado em {p}")

    if found:
        rows = []
        for nome, descricao, geom in found:
            rows.append({
                "nome": nome,
                "descricao": descricao,
                "source": "KMZ real",
                "geometry": geom,
            })
        return gpd.GeoDataFrame(rows, crs="EPSG:4326")

    if fallback_to_geojson is not None:
        fp = Path(fallback_to_geojson)
        if fp.exists():
            try:
                return gpd.read_file(fp)
            except Exception as exc:
                print(f"[kmz_utils] Fallback GeoJSON falhou em {fp}: {exc}")
    return None


def load_points_from_kmz(
    kmz_path: str | os.PathLike,
    fallback_to_geojson: Optional[str | os.PathLike] = None,
    accept_lines_as_points: bool = True,
) -> Optional[gpd.GeoDataFrame]:
    """Le todos os Points de um KMZ. Cada Placemark Point vira uma feicao.

    Args:
        accept_lines_as_points: se True (default), tambem aceita Placemarks
            com LineString e converte cada um para um Point no centroide da
            linha. Util quando o usuario desenhou linhas no Google Earth
            para representar pontos de viaduto.
    """
    p = Path(kmz_path)
    found = []
    if p.exists():
        try:
            with zipfile.ZipFile(p, "r") as zf:
                kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
                for kml_name in kml_names:
                    try:
                        with zf.open(kml_name) as fh:
                            kml_text = fh.read().decode("utf-8", errors="replace")
                    except Exception:
                        continue
                    found.extend(_find_points_in_kml(kml_text))
                    # se nao achou pontos e o caller permite, tenta extrair
                    # linhas e converte para centroide (Point)
                    if accept_lines_as_points and len(found) == 0:
                        for nome, descricao, geom in _find_first_line_in_kml(kml_text):
                            try:
                                centroid = geom.centroid
                                found.append((nome, descricao, Point(centroid.x, centroid.y)))
                            except Exception:
                                continue
        except Exception as exc:
            print(f"[kmz_utils] Falha ao abrir {p}: {exc}")
    else:
        print(f"[kmz_utils] KMZ nao encontrado em {p}")

    if found:
        rows = []
        for nome, descricao, geom in found:
            rows.append({
                "nome": nome,
                "descricao": descricao,
                "source": "KMZ real",
                "geometry": geom,
            })
        return gpd.GeoDataFrame(rows, crs="EPSG:4326")

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
