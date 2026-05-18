"""Placeholders para integracao futura com ferramentas avancadas de
simulacao e alocacao de trafego.

Esta versao do prototipo NAO depende de SUMO nem AequilibraE - as
funcoes abaixo sao apenas stubs que documentam a interface esperada.

Quando o usuario quiser realmente integrar uma dessas ferramentas:
1. Adicionar a dependencia em requirements.txt (sumolib / aequilibrae)
2. Implementar a logica nesta funcao
3. Habilitar o botao correspondente na aba 'Atualizacao de Dados'

Referencias:
- SUMO       : https://www.eclipse.dev/sumo/ (microssimulacao de trafego)
- AequilibraE: https://www.aequilibrae.com/  (modelagem 4-step,
                                              equilibrio, distribuicao)
- OSMnx/NetworkX (ja usado): rede e caminhos minimos
"""
from __future__ import annotations

from typing import Optional


def export_to_sumo(network, od_matrix, output_dir: str) -> Optional[str]:
    """[PLACEHOLDER] Exportar rede + matriz O-D para arquivos SUMO.

    Implementacao futura:
    - Converter rede OSMnx -> .net.xml via netconvert
    - Gerar arquivos de demanda .rou.xml a partir da matriz O-D
    - Criar arquivo de configuracao .sumocfg

    Args:
        network: grafo NetworkX da rede viaria
        od_matrix: pd.DataFrame da matriz O-D
        output_dir: pasta de saida

    Returns:
        Caminho do .sumocfg gerado, ou None se nao implementado.
    """
    raise NotImplementedError(
        "Exportacao para SUMO ainda nao implementada. "
        "Esta funcao e um placeholder para integracao futura."
    )


def export_to_aequilibrae(network, od_matrix, output_dir: str) -> Optional[str]:
    """[PLACEHOLDER] Exportar rede + matriz O-D para AequilibraE.

    Implementacao futura:
    - Criar Project AequilibraE
    - Importar rede como arcs/nodes
    - Importar matriz como demanda
    - Configurar zonas e centroides

    Args:
        network: grafo NetworkX da rede viaria
        od_matrix: pd.DataFrame da matriz O-D
        output_dir: pasta de saida

    Returns:
        Caminho do projeto AequilibraE gerado, ou None se nao implementado.
    """
    raise NotImplementedError(
        "Exportacao para AequilibraE ainda nao implementada. "
        "Esta funcao e um placeholder para integracao futura."
    )


def run_advanced_assignment(
    network,
    od_matrix,
    method: str = "frank_wolfe",
    max_iter: int = 100,
) -> Optional[dict]:
    """[PLACEHOLDER] Executa alocacao de trafego avancada com equilibrio.

    Implementacao futura usaria algoritmos como:
    - Frank-Wolfe (equilibrio de usuario)
    - MSA - Method of Successive Averages
    - Bi-Conjugate Frank-Wolfe

    A versao atual (modules/traffic_assignment.py) faz 'all-or-nothing'
    sem considerar capacidade ou congestionamento.

    Args:
        network: grafo NetworkX da rede viaria com capacidade nas arestas
        od_matrix: pd.DataFrame da matriz O-D
        method: algoritmo de equilibrio
        max_iter: iteracoes maximas

    Returns:
        Dict com fluxos de equilibrio por aresta, ou None.
    """
    raise NotImplementedError(
        "Alocacao avancada com equilibrio ainda nao implementada. "
        "Use modules.traffic_assignment.assign_od_to_network para a "
        "versao simplificada (all-or-nothing)."
    )


# Lista usada na aba 'Evolucoes futuras' do app
FUTURE_INTEGRATIONS = [
    {
        "nome": "SUMO",
        "url": "https://www.eclipse.dev/sumo/",
        "descricao": "Simulacao microscopica de trafego veicular, "
                     "permitindo modelar semaforos, retornos, "
                     "comportamento individual de veiculos.",
        "complexidade": "Alta",
        "status_no_prototipo": "Placeholder (export_to_sumo)",
    },
    {
        "nome": "AequilibraE",
        "url": "https://www.aequilibrae.com/",
        "descricao": "Modelagem 4-step completa: geracao, distribuicao, "
                     "divisao modal e alocacao com equilibrio. "
                     "Permite tambem matrizes O-D sintetizadas.",
        "complexidade": "Media-Alta",
        "status_no_prototipo": "Placeholder (export_to_aequilibrae)",
    },
    {
        "nome": "OSMnx + NetworkX",
        "url": "https://osmnx.readthedocs.io/",
        "descricao": "Rede viaria real + caminhos minimos. Ja usado na "
                     "versao atual do prototipo para a alocacao "
                     "simplificada 'all-or-nothing'.",
        "complexidade": "Baixa-Media",
        "status_no_prototipo": "JA INTEGRADO",
    },
]
