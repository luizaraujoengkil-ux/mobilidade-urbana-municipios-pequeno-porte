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
