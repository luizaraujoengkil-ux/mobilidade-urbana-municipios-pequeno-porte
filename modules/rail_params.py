"""Parametros ferroviarios editaveis e calculos de bloqueio / custo social.

Os parametros sao salvos em JSON na pasta data/demo_matias_barbosa/
para permitir atualizacao periodica sem alterar codigo.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEMO_DIR = DATA_DIR / "demo_matias_barbosa"
RAIL_PARAMS_PATH = DEMO_DIR / "rail_parameters.json"


DEFAULT_RAIL_PARAMS = {
    "velocidade_media_kmh": 55.0,
    "fator_operacional_bloqueio": 2.0,
    "passagens_por_dia": 8.0,
    "valor_tempo_pessoa_hora": 25.0,   # R$/hora - aproximacao social
    "fluxo_afetado_por_bloqueio": 80,  # veiculos por bloqueio
    "ocupacao_media_veiculo": 1.5,     # passageiros / veiculo
    "dias_por_ano": 365,
    "trens": [
        {
            "tipo": "Trem de minerio",
            "vagoes": 272,
            "comprimento_km": 3.0,
            "observacoes": "Trens longos com alto impacto operacional",
        },
        {
            "tipo": "Trem de carga geral",
            "vagoes": 70,
            "comprimento_km": 1.4,
            "observacoes": "Trens curtos, ocupam menos tempo",
        },
    ],
}


def load_rail_params() -> dict:
    if not RAIL_PARAMS_PATH.exists():
        save_rail_params(DEFAULT_RAIL_PARAMS)
        return DEFAULT_RAIL_PARAMS
    try:
        with open(RAIL_PARAMS_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # mescla com defaults se faltar algum campo (compat retro)
        for k, v in DEFAULT_RAIL_PARAMS.items():
            data.setdefault(k, v)
        return data
    except Exception as exc:
        print(f"[rail_params] erro lendo {RAIL_PARAMS_PATH}: {exc}")
        return DEFAULT_RAIL_PARAMS.copy()


def save_rail_params(data: dict) -> None:
    RAIL_PARAMS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RAIL_PARAMS_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def reset_to_default() -> dict:
    save_rail_params(DEFAULT_RAIL_PARAMS.copy())
    return DEFAULT_RAIL_PARAMS.copy()


# --- Calculos derivados --------------------------------------------------
def tempo_passagem_min(comprimento_km: float, velocidade_kmh: float) -> float:
    """Tempo fisico de passagem do trem (minutos)."""
    if velocidade_kmh <= 0:
        return 0.0
    return (comprimento_km / velocidade_kmh) * 60.0


def tempo_bloqueio_min(comprimento_km: float, velocidade_kmh: float,
                       fator_operacional: float) -> float:
    """Tempo total estimado de bloqueio = tempo fisico * fator operacional."""
    return tempo_passagem_min(comprimento_km, velocidade_kmh) * fator_operacional


def compute_blocking_table(params: dict) -> list:
    """Devolve lista de dicts com calculos de bloqueio por tipo de trem."""
    rows = []
    v = params.get("velocidade_media_kmh", 55.0)
    f = params.get("fator_operacional_bloqueio", 2.0)
    for trem in params.get("trens", []):
        comp = trem.get("comprimento_km", 0.0)
        t_fisico = tempo_passagem_min(comp, v)
        t_bloq = tempo_bloqueio_min(comp, v, f)
        rows.append({
            "tipo": trem.get("tipo", ""),
            "vagoes": trem.get("vagoes", 0),
            "comprimento_km": comp,
            "velocidade_kmh": v,
            "tempo_fisico_min": round(t_fisico, 2),
            "tempo_bloqueio_min": round(t_bloq, 2),
            "observacoes": trem.get("observacoes", ""),
        })
    return rows


def compute_social_cost_per_scenario(params: dict, odm_df=None) -> list:
    """Calcula custo social do bloqueio ferroviario POR CENARIO.

    Se odm_df (matriz O-D detalhada) estiver presente:
    - Usa daily_blockage_minutes do CENARIO BASE como referencia
    - Para cada access_scenario != 'base', estima o custo apos a intervencao
    - Calcula economia vs base em R$ e %

    Se odm_df for None: retorna apenas o cenario base com os parametros
    atuais (igual a compute_social_cost).

    Logica para cenarios com intervencao:
    - Se o CSV tem daily_blockage_minutes para o cenario, usa ele
    - Senao, ASSUME que o viaduto elimina o bloqueio (bloqueio_cenario=0)
      Isso da o cenario otimista (limite superior de economia)
    """
    try:
        import pandas as pd
    except ImportError:
        return []

    valor_h = float(params.get("valor_tempo_pessoa_hora", 0))
    ocup = float(params.get("ocupacao_media_veiculo", 1.0))
    dias = float(params.get("dias_por_ano", 365))
    fluxo = float(params.get("fluxo_afetado_por_bloqueio", 0))
    pessoas = fluxo * ocup

    # Caso 1: sem matriz OD detalhada - so cenario base
    if odm_df is None or (hasattr(odm_df, "empty") and odm_df.empty):
        base_cost = compute_social_cost(params)
        return [{
            "cenario": "Base (hoje)",
            "tempo_bloqueio_diario_min": base_cost["atraso_diario_min"],
            "pessoas_afetadas": base_cost["pessoas_afetadas_por_bloqueio"],
            "horas_perdidas_dia": round(
                base_cost["pessoas_afetadas_por_bloqueio"]
                * base_cost["tempo_bloqueio_referencia_min"] / 60.0
                * float(params.get("passagens_por_dia", 1)), 2
            ),
            "custo_diario_R$": base_cost["custo_diario_R$"],
            "custo_anual_R$": base_cost["custo_anual_R$"],
            "economia_vs_base_R$": 0.0,
            "economia_pct": 0.0,
        }]

    # Caso 2: com matriz OD detalhada
    rows = []
    base_pairs = odm_df[odm_df["access_scenario"].str.lower().eq("base")]
    base_inter = base_pairs[base_pairs["origin_zone"] != base_pairs["destination_zone"]]
    base_block_total = pd.to_numeric(
        base_inter.get("daily_blockage_minutes"), errors="coerce"
    ).dropna().sum() if "daily_blockage_minutes" in base_inter.columns else 0.0

    # Se nao houver bloqueio no CSV, cai no calculo padrao do compute_social_cost
    if base_block_total <= 0:
        base_cost = compute_social_cost(params)
        base_block_total = base_cost["atraso_diario_min"]

    horas_perdidas_base = pessoas * (base_block_total / 60.0)
    custo_diario_base = horas_perdidas_base * valor_h
    custo_anual_base = custo_diario_base * dias

    rows.append({
        "cenario": "Base (hoje - sem intervencao)",
        "tempo_bloqueio_diario_min": round(base_block_total, 1),
        "pessoas_afetadas": round(pessoas, 1),
        "horas_perdidas_dia": round(horas_perdidas_base, 2),
        "custo_diario_R$": round(custo_diario_base, 2),
        "custo_anual_R$": round(custo_anual_base, 2),
        "economia_vs_base_R$": 0.0,
        "economia_pct": 0.0,
    })

    # Cenarios de intervencao
    scenarios = odm_df[~odm_df["access_scenario"].str.lower().eq("base")]
    for sc_name in sorted(scenarios["access_scenario"].unique()):
        sc_df = scenarios[scenarios["access_scenario"] == sc_name]
        sc_inter = sc_df[sc_df["origin_zone"] != sc_df["destination_zone"]]

        # Estrategia 1: usa daily_blockage_minutes do proprio cenario (se preenchido)
        sc_block = pd.to_numeric(
            sc_inter.get("daily_blockage_minutes"), errors="coerce"
        ).dropna().sum() if "daily_blockage_minutes" in sc_inter.columns else 0.0

        # Estrategia 2: se for 0, infere a partir da reducao de tempo
        # bloqueio_cenario = bloqueio_base * (improved_time / base_time)
        if sc_block <= 0:
            ratio_total = 0.0
            ratio_count = 0
            for (orig, dest), row_sc in sc_inter.set_index(
                ["origin_zone", "destination_zone"]
            ).iterrows():
                base_row = base_inter[
                    (base_inter["origin_zone"] == orig) &
                    (base_inter["destination_zone"] == dest)
                ]
                if base_row.empty:
                    continue
                base_t = pd.to_numeric(base_row["base_travel_time_min"], errors="coerce").iloc[0]
                imp_t = pd.to_numeric(row_sc.get("improved_travel_time_min"), errors="coerce")
                if pd.notna(base_t) and pd.notna(imp_t) and base_t > 0:
                    ratio_total += (imp_t / base_t)
                    ratio_count += 1
            if ratio_count > 0:
                ratio = ratio_total / ratio_count
                sc_block = base_block_total * ratio
            else:
                # Sem dado especifico: viaduto elimina bloqueio
                sc_block = 0.0

        horas_perdidas_sc = pessoas * (sc_block / 60.0)
        custo_diario_sc = horas_perdidas_sc * valor_h
        custo_anual_sc = custo_diario_sc * dias
        economia = custo_anual_base - custo_anual_sc
        pct = (economia / custo_anual_base * 100) if custo_anual_base > 0 else 0.0

        rows.append({
            "cenario": f"Cenario: {sc_name}",
            "tempo_bloqueio_diario_min": round(sc_block, 1),
            "pessoas_afetadas": round(pessoas, 1),
            "horas_perdidas_dia": round(horas_perdidas_sc, 2),
            "custo_diario_R$": round(custo_diario_sc, 2),
            "custo_anual_R$": round(custo_anual_sc, 2),
            "economia_vs_base_R$": round(economia, 2),
            "economia_pct": round(pct, 1),
        })

    return rows


def compute_social_cost(params: dict, tempo_bloqueio_min_total: Optional[float] = None) -> dict:
    """Estima custo social a partir dos parametros.

    pessoas_afetadas = fluxo_afetado * ocupacao_media
    horas_perdidas_por_bloqueio = pessoas * (tempo_bloqueio_min / 60)
    custo_por_bloqueio = horas * valor_tempo_hora
    custo_anual = custo_por_bloqueio * passagens_por_dia * dias_por_ano
    """
    if tempo_bloqueio_min_total is None:
        # usa o trem de carga geral como referencia (impacto medio)
        rows = compute_blocking_table(params)
        if rows:
            # media dos tempos de bloqueio
            tempo_bloqueio_min_total = sum(r["tempo_bloqueio_min"] for r in rows) / len(rows)
        else:
            tempo_bloqueio_min_total = 0.0

    fluxo = float(params.get("fluxo_afetado_por_bloqueio", 0))
    ocup = float(params.get("ocupacao_media_veiculo", 1.0))
    valor_h = float(params.get("valor_tempo_pessoa_hora", 0))
    passagens_dia = float(params.get("passagens_por_dia", 0))
    dias_ano = float(params.get("dias_por_ano", 365))

    pessoas_afetadas = fluxo * ocup
    horas_perdidas = pessoas_afetadas * (tempo_bloqueio_min_total / 60.0)
    custo_por_bloqueio = horas_perdidas * valor_h
    custo_diario = custo_por_bloqueio * passagens_dia
    custo_anual = custo_diario * dias_ano
    atraso_diario_min = tempo_bloqueio_min_total * passagens_dia
    atraso_anual_min = atraso_diario_min * dias_ano

    return {
        "tempo_bloqueio_referencia_min": round(tempo_bloqueio_min_total, 2),
        "pessoas_afetadas_por_bloqueio": round(pessoas_afetadas, 1),
        "horas_perdidas_por_bloqueio": round(horas_perdidas, 2),
        "custo_por_bloqueio_R$": round(custo_por_bloqueio, 2),
        "custo_diario_R$": round(custo_diario, 2),
        "custo_anual_R$": round(custo_anual, 2),
        "atraso_diario_min": round(atraso_diario_min, 1),
        "atraso_anual_horas": round(atraso_anual_min / 60.0, 1),
    }
