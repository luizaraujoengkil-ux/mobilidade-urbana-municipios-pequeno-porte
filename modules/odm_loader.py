"""Leitura e aplicacao de matriz Origem-Destino DETALHADA via CSV.

Diferente do CSV simples (zona, populacao), este formato traz:
- base_distance_km / base_travel_time_min: situacao atual entre o par
- road_crossings_count / rail_crossings_count: travessias no trajeto
- daily_blockage_minutes: total de minutos de interrupcao por dia
- delay_per_trip_min: atraso medio por viagem
- improved_distance_km / improved_travel_time_min: cenario com viaduto
- access_scenario: 'base' ou identificador do cenario (ex. 'viaduto_1')
- notes: descricao livre

Linhas com access_scenario != 'base' viram CENARIOS automaticos no
simulador (com a tupla improved_* aplicada como override de distancia
e tempo entre as zonas).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEMO_DIR = DATA_DIR / "demo_matias_barbosa"

OD_MATRIX_CSV_NAMES = [
    "od_matrix_template_matias_barbosa.csv",
    "od_matrix_atualizada.csv",
    "od_matrix.csv",
    "matriz_od.csv",
]


def find_od_matrix_csv() -> Optional[Path]:
    """Procura o CSV de matriz OD detalhada usando varios nomes possiveis."""
    for name in OD_MATRIX_CSV_NAMES:
        path = DEMO_DIR / name
        if path.exists():
            return path
    return None


def load_od_matrix_csv(csv_path: str | Path) -> tuple[Optional[pd.DataFrame], list]:
    """Le o CSV detalhado e normaliza colunas.

    Retorna (DataFrame normalizado, log_de_aviso).
    Retorna (None, log) se o arquivo nao existir ou nao tiver schema valido.
    """
    log = []
    p = Path(csv_path)
    if not p.exists():
        log.append(f"[ERRO] Arquivo nao encontrado: {p}")
        return None, log
    try:
        df = pd.read_csv(p, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(p, encoding="latin-1")
            log.append("[INFO] CSV lido com latin-1 (nao era UTF-8).")
        except Exception as exc:
            log.append(f"[ERRO] Falha ao ler CSV: {exc}")
            return None, log
    except Exception as exc:
        log.append(f"[ERRO] Falha ao ler CSV: {exc}")
        return None, log

    df.columns = [c.lower().strip() for c in df.columns]

    required = {"origin_zone", "destination_zone"}
    missing = required - set(df.columns)
    if missing:
        log.append(f"[ERRO] Faltam colunas obrigatorias: {missing}")
        return None, log

    # Normalizacao
    df["origin_zone"] = df["origin_zone"].astype(str).str.strip().str.upper()
    df["destination_zone"] = df["destination_zone"].astype(str).str.strip().str.upper()

    if "access_scenario" not in df.columns:
        df["access_scenario"] = "base"
    df["access_scenario"] = df["access_scenario"].fillna("base").astype(str).str.strip()
    df.loc[df["access_scenario"] == "", "access_scenario"] = "base"

    # Converte colunas numericas
    num_cols = [
        "base_distance_km", "base_travel_time_min",
        "road_crossings_count", "rail_crossings_count",
        "daily_blockage_minutes", "delay_per_trip_min",
        "improved_distance_km", "improved_travel_time_min",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = None

    log.append(f"[OK] {len(df)} linhas carregadas. "
               f"{df['access_scenario'].nunique()} cenario(s) detectado(s): "
               f"{sorted(df['access_scenario'].unique())}")
    return df, log


# ------------------------------------------------------------------
# Aplicacao no estado do simulador
# ------------------------------------------------------------------
def split_base_and_scenarios(odm_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Separa as linhas base das linhas de cenario.

    Retorna (df_base, {scenario_name: df_scenario})
    """
    if odm_df is None:
        return pd.DataFrame(), {}
    base_mask = odm_df["access_scenario"].str.lower().eq("base")
    df_base = odm_df[base_mask].copy()
    scenarios = {}
    for sc_name, group in odm_df[~base_mask].groupby("access_scenario"):
        scenarios[sc_name] = group.copy()
    return df_base, scenarios


def aggregate_indicators(df_pairs: pd.DataFrame) -> dict:
    """Calcula indicadores agregados de um conjunto de pares O-D."""
    if df_pairs is None or df_pairs.empty:
        return {}
    inter = df_pairs[df_pairs["origin_zone"] != df_pairs["destination_zone"]]
    if inter.empty:
        inter = df_pairs

    def _mean(col):
        if col not in inter.columns:
            return None
        s = pd.to_numeric(inter[col], errors="coerce").dropna()
        return float(s.mean()) if not s.empty else None

    def _sum(col):
        if col not in inter.columns:
            return None
        s = pd.to_numeric(inter[col], errors="coerce").dropna()
        return float(s.sum()) if not s.empty else None

    return {
        "n_pares": int(len(inter)),
        "dist_media_base_km":     _mean("base_distance_km"),
        "tempo_medio_base_min":   _mean("base_travel_time_min"),
        "dist_media_melhorado_km":   _mean("improved_distance_km"),
        "tempo_medio_melhorado_min": _mean("improved_travel_time_min"),
        "atraso_total_diario_min":   _sum("daily_blockage_minutes"),
        "atraso_medio_viagem_min":   _mean("delay_per_trip_min"),
        "travessias_rodov_total": _sum("road_crossings_count"),
        "travessias_ferrov_total": _sum("rail_crossings_count"),
    }


def compare_scenarios_csv(odm_df: pd.DataFrame) -> pd.DataFrame:
    """Tabela comparativa baseline vs cada cenario lido do CSV.

    Calcula reducao % de distancia e tempo + reducao do atraso.
    """
    if odm_df is None or odm_df.empty:
        return pd.DataFrame()

    df_base, sc_map = split_base_and_scenarios(odm_df)
    base_ind = aggregate_indicators(df_base) if not df_base.empty else {}

    rows = [{
        "cenario": "Base (atual)",
        "dist_media_km": base_ind.get("dist_media_base_km"),
        "tempo_medio_min": base_ind.get("tempo_medio_base_min"),
        "atraso_total_diario_min": base_ind.get("atraso_total_diario_min"),
        "reducao_distancia_pct": 0.0,
        "reducao_tempo_pct": 0.0,
        "n_pares": base_ind.get("n_pares"),
    }]

    for sc_name, df_sc in sc_map.items():
        ind = aggregate_indicators(df_sc)
        dist_melh = ind.get("dist_media_melhorado_km") or ind.get("dist_media_base_km")
        tempo_melh = ind.get("tempo_medio_melhorado_min") or ind.get("tempo_medio_base_min")
        red_dist = (
            ((base_ind.get("dist_media_base_km", 0) or 0) - (dist_melh or 0))
            / base_ind["dist_media_base_km"] * 100
            if base_ind.get("dist_media_base_km") else None
        )
        red_tempo = (
            ((base_ind.get("tempo_medio_base_min", 0) or 0) - (tempo_melh or 0))
            / base_ind["tempo_medio_base_min"] * 100
            if base_ind.get("tempo_medio_base_min") else None
        )
        rows.append({
            "cenario": sc_name,
            "dist_media_km": round(dist_melh, 3) if dist_melh else None,
            "tempo_medio_min": round(tempo_melh, 2) if tempo_melh else None,
            "atraso_total_diario_min": ind.get("atraso_total_diario_min"),
            "reducao_distancia_pct": round(red_dist, 2) if red_dist is not None else None,
            "reducao_tempo_pct": round(red_tempo, 2) if red_tempo is not None else None,
            "n_pares": ind.get("n_pares"),
        })
    return pd.DataFrame(rows)


def get_distance_matrix_from_csv(
    odm_df: pd.DataFrame,
    scenario: str = "base",
    column: str = "base_distance_km",
) -> pd.DataFrame:
    """Constroi matriz quadrada de distancias do CSV para o cenario indicado.

    Args:
        scenario: 'base' ou nome de access_scenario
        column: nome da coluna numerica a usar (default: base_distance_km;
            para cenarios use improved_distance_km)
    """
    if odm_df is None or odm_df.empty:
        return pd.DataFrame()
    df = odm_df[odm_df["access_scenario"].str.lower().eq(scenario.lower())].copy()
    if df.empty or column not in df.columns:
        return pd.DataFrame()
    pivot = df.pivot_table(
        index="origin_zone",
        columns="destination_zone",
        values=column,
        aggfunc="first",
    )
    return pivot


def build_delay_pair_table(odm_df: pd.DataFrame) -> pd.DataFrame:
    """Tabela formatada de atrasos por par O-D para o relatorio."""
    if odm_df is None or odm_df.empty:
        return pd.DataFrame()
    base = odm_df[odm_df["access_scenario"].str.lower().eq("base")].copy()
    base = base[base["origin_zone"] != base["destination_zone"]]
    keep_cols = [
        "origin_zone", "destination_zone",
        "base_travel_time_min", "improved_travel_time_min",
        "daily_blockage_minutes", "delay_per_trip_min",
        "road_crossings_count", "rail_crossings_count",
    ]
    keep_cols = [c for c in keep_cols if c in base.columns]
    return base[keep_cols].copy()
