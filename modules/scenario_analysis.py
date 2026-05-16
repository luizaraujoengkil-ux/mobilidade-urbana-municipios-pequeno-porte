"""Criacao e comparacao de cenarios de intervencao."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx
import pandas as pd

from . import network_analysis as net


SCENARIO_TYPES = [
    "Cenario atual",
    "Cenario com viaduto",
    "Cenario com ponte",
    "Cenario com nova ligacao viaria",
    "Cenario com bloqueio/restricao",
]


@dataclass
class Scenario:
    nome: str
    tipo: str
    descricao: str = ""
    intervencoes: list = field(default_factory=list)  # cada item: dict(from, to, factor, tipo)
    bloqueios: list = field(default_factory=list)     # cada item: dict(from, to)

    def apply(self, base_graph: nx.Graph) -> nx.Graph:
        G = copy.deepcopy(base_graph)
        for inter in self.intervencoes:
            try:
                net.add_intervention_edge(
                    G,
                    inter["from"],
                    inter["to"],
                    factor=inter.get("factor", 0.5),
                    tipo=inter.get("tipo", self.tipo),
                )
            except Exception:
                continue
        for b in self.bloqueios:
            net.block_edge(G, b["from"], b["to"])
        return G


def scenario_indicators(scenario: Scenario, base_graph: nx.Graph) -> dict:
    G = scenario.apply(base_graph)
    dist_mean = net.average_zone_distance(G)
    time_mean = net.estimated_average_time(dist_mean)
    zonas = [n for n, d in G.nodes(data=True) if d.get("tipo") == "zona"]
    return {
        "cenario": scenario.nome,
        "tipo": scenario.tipo,
        "distancia_media_km": round(dist_mean, 3),
        "tempo_medio_min": round(time_mean, 2),
        "n_zonas": len(zonas),
        "componentes_conectados": net.connected_zone_count(G),
        "intervencoes": len(scenario.intervencoes),
        "bloqueios": len(scenario.bloqueios),
    }


def compare_scenarios(scenarios: list, base_graph: nx.Graph) -> pd.DataFrame:
    rows = [scenario_indicators(s, base_graph) for s in scenarios]
    df = pd.DataFrame(rows)
    if df.empty:
        return df

    base_dist = df["distancia_media_km"].iloc[0] if not df.empty else None
    if base_dist:
        df["reducao_percurso_pct"] = ((base_dist - df["distancia_media_km"]) / base_dist * 100).round(2)
    else:
        df["reducao_percurso_pct"] = 0.0
    df["observacao"] = df.apply(_interp_row, axis=1)
    return df


def _interp_row(row: pd.Series) -> str:
    red = row.get("reducao_percurso_pct", 0)
    tipo = row.get("tipo", "")
    if red > 1.0:
        return (
            f"Reducao de {red:.1f}% na distancia media entre zonas - intervencao "
            f"do tipo '{tipo}' melhora a conectividade urbana e reduz efeito barreira."
        )
    elif red < -1.0:
        return (
            f"Aumento de {abs(red):.1f}% na distancia media - bloqueio/restricao "
            f"impacta negativamente a mobilidade entre zonas."
        )
    return "Pouca variacao em relacao ao cenario atual."


def best_scenario(df_compare: pd.DataFrame) -> Optional[pd.Series]:
    if df_compare is None or df_compare.empty:
        return None
    return df_compare.sort_values("reducao_percurso_pct", ascending=False).iloc[0]
