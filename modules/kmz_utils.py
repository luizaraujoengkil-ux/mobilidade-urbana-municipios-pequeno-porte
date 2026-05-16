"""Leitura de arquivos KML e KMZ."""
from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path

import fiona
import geopandas as gpd
import pandas as pd


def _enable_kml_driver() -> None:
    """Habilita driver KML do fiona/GDAL (algumas instalacoes vem desabilitadas)."""
    try:
        fiona.drvsupport.supported_drivers["KML"] = "rw"
        fiona.drvsupport.supported_drivers["LIBKML"] = "rw"
    except Exception:
        pass


def read_kml(path: str | os.PathLike) -> gpd.GeoDataFrame:
    _enable_kml_driver()
    path = str(path)
    # Tenta ler todas as camadas e empilhar
    layers = []
    try:
        layer_names = fiona.listlayers(path)
    except Exception:
        layer_names = [None]
    frames = []
    for ln in layer_names:
        try:
            if ln is None:
                gdf = gpd.read_file(path, driver="KML")
            else:
                gdf = gpd.read_file(path, driver="KML", layer=ln)
            if not gdf.empty:
                gdf["__layer__"] = ln if ln else "kml"
                frames.append(gdf)
        except Exception:
            continue
    if not frames:
        # Fallback final
        return gpd.read_file(path)
    return gpd.GeoDataFrame(
        pd.concat(frames, ignore_index=True), crs=frames[0].crs
    )


def read_kmz(path: str | os.PathLike) -> gpd.GeoDataFrame:
    """Extrai um KMZ e le o KML interno."""
    path = Path(path)
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(path, "r") as zf:
            zf.extractall(tmp)
        # procura KML extraido (geralmente doc.kml)
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
