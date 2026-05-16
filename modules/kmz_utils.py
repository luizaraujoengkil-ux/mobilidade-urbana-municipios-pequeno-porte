"""Leitura de arquivos KML e KMZ.

Tenta usar pyogrio (default no geopandas 1.0+) ou fiona. Em ambientes que
nao tenham nenhum dos dois com suporte a KML, cai num fallback que apenas
delega para geopandas.read_file.
"""
from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

import geopandas as gpd
import pandas as pd

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
