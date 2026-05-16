"""Geocodificacao de municipios usando OSMnx (preferencial) ou Nominatim."""
from __future__ import annotations

from typing import Optional, Tuple

try:
    import osmnx as ox  # type: ignore
    HAS_OSMNX = True
except Exception:
    HAS_OSMNX = False

try:
    import requests  # type: ignore
    HAS_REQUESTS = True
except Exception:
    HAS_REQUESTS = False


def _via_osmnx(query: str) -> Optional[Tuple[float, float]]:
    if not HAS_OSMNX:
        return None
    try:
        result = ox.geocode(query)
        if result is not None:
            return float(result[0]), float(result[1])
    except Exception:
        return None
    return None


def _via_nominatim(query: str) -> Optional[Tuple[float, float]]:
    if not HAS_REQUESTS:
        return None
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "mobilidade-urbana-prototipo/1.0"},
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception:
        return None
    return None


def geocode_municipio(nome: str, uf: str = "") -> Optional[Tuple[float, float]]:
    """Retorna (lat, lon) do municipio. None se nao encontrar."""
    if not nome or not nome.strip():
        return None
    query = f"{nome.strip()}, {uf.strip()}, Brasil" if uf else f"{nome.strip()}, Brasil"
    result = _via_osmnx(query)
    if result is not None:
        return result
    return _via_nominatim(query)
