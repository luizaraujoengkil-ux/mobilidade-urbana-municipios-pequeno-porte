"""Gerenciamento de metadados das bases de dados do estudo.

Mantem um JSON com informacoes sobre cada base usada no simulador,
permitindo rastrear data de importacao, fonte, status (atualizado /
pendente / desatualizado) e responsavel pela atualizacao.
"""
from __future__ import annotations

import json
from datetime import datetime, date
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEMO_DIR = DATA_DIR / "demo_matias_barbosa"
METADATA_PATH = DEMO_DIR / "metadata.json"

STATUS_LABELS = {
    "atualizado":     "✅ Atualizado",
    "pendente":       "⏳ Pendente",
    "desatualizado":  "⚠️ Desatualizado",
    "ausente":        "❌ Ausente",
}


DEFAULT_METADATA = {
    "schema_version": 1,
    "ultima_revisao": None,
    "bases": [
        {
            "id": "populacao_ipea_2010",
            "nome": "Populacao IPEA 2010",
            "fonte": "IPEA - Instituto de Pesquisa Economica Aplicada",
            "ano": 2010,
            "data_importacao": None,
            "data_ultima_atualizacao": None,
            "validade_anos": 12,
            "responsavel": "",
            "observacoes": "Base historica de calibracao - referencia 2010",
            "status": "pendente",
            "arquivo": "",
        },
        {
            "id": "populacao_ibge_2022",
            "nome": "Populacao IBGE 2022",
            "fonte": "IBGE - Censo Demografico 2022",
            "ano": 2022,
            "data_importacao": None,
            "data_ultima_atualizacao": None,
            "validade_anos": 10,
            "responsavel": "",
            "observacoes": "Base mais recente para calibracao da geracao",
            "status": "pendente",
            "arquivo": "",
        },
        {
            "id": "malha_viaria_osm",
            "nome": "Malha viaria OpenStreetMap",
            "fonte": "OpenStreetMap contributors",
            "ano": None,
            "data_importacao": None,
            "data_ultima_atualizacao": None,
            "validade_anos": 1,
            "responsavel": "",
            "observacoes": "Baixada sob demanda via OSMnx (sidebar)",
            "status": "atualizado",
            "arquivo": "",
        },
        {
            "id": "pois_osm",
            "nome": "Pontos de interesse OSM",
            "fonte": "OpenStreetMap (Overpass)",
            "ano": None,
            "data_importacao": None,
            "data_ultima_atualizacao": None,
            "validade_anos": 1,
            "responsavel": "",
            "observacoes": "Buscados sob demanda na etapa 6 do Assistente",
            "status": "atualizado",
            "arquivo": "",
        },
        {
            "id": "zonas_analiticas",
            "nome": "Zonas analiticas Z1-Z4",
            "fonte": "Levantamento proprio (Google Earth Pro)",
            "ano": 2026,
            "data_importacao": None,
            "data_ultima_atualizacao": None,
            "validade_anos": 5,
            "responsavel": "Luiz Araujo de Souza Junior",
            "observacoes": "Geometria real exportada do Google Earth Pro como KMZ",
            "status": "atualizado",
            "arquivo": "z1.kmz, z2.kmz, z3*.kmz, z4.kmz",
        },
        {
            "id": "area_estudo",
            "nome": "Area de estudo",
            "fonte": "Levantamento proprio (Google Earth Pro)",
            "ano": 2026,
            "data_importacao": None,
            "data_ultima_atualizacao": None,
            "validade_anos": 5,
            "responsavel": "Luiz Araujo de Souza Junior",
            "observacoes": "Perimetro analitico do municipio",
            "status": "atualizado",
            "arquivo": "area_de_estudo_matias_barbosa.kmz",
        },
        {
            "id": "linha_ferrea",
            "nome": "Linha ferrea",
            "fonte": "Levantamento proprio + OSM",
            "ano": 2026,
            "data_importacao": None,
            "data_ultima_atualizacao": None,
            "validade_anos": 10,
            "responsavel": "",
            "observacoes": "Tracado da ferrovia em Matias Barbosa",
            "status": "atualizado",
            "arquivo": "Linha do trem.kmz",
        },
        {
            "id": "rodovias",
            "nome": "Rodovias/eixos viarios",
            "fonte": "Levantamento proprio + DNIT/DER-MG",
            "ano": 2026,
            "data_importacao": None,
            "data_ultima_atualizacao": None,
            "validade_anos": 5,
            "responsavel": "",
            "observacoes": "BR-040, MG-353, Uniao Industria e ligacoes",
            "status": "atualizado",
            "arquivo": "Rodovias*.kmz, Ligacao*.kmz",
        },
        {
            "id": "dados_ferroviarios",
            "nome": "Parametros ferroviarios",
            "fonte": "Operadora ferroviaria / referencias setoriais",
            "ano": 2026,
            "data_importacao": None,
            "data_ultima_atualizacao": None,
            "validade_anos": 3,
            "responsavel": "",
            "observacoes": "Velocidade, comprimento dos trens, fator de bloqueio",
            "status": "atualizado",
            "arquivo": "rail_parameters.json",
        },
        {
            "id": "parametros_tempo_custo",
            "nome": "Parametros tempo x custo",
            "fonte": "ANTP / DNIT / Estudos setoriais",
            "ano": 2026,
            "data_importacao": None,
            "data_ultima_atualizacao": None,
            "validade_anos": 3,
            "responsavel": "",
            "observacoes": "Valor do tempo, ocupacao media, fluxo afetado",
            "status": "pendente",
            "arquivo": "rail_parameters.json",
        },
    ],
}


def _today_iso() -> str:
    return date.today().isoformat()


def load_metadata() -> dict:
    """Carrega metadata.json. Cria com defaults se nao existir."""
    if not METADATA_PATH.exists():
        save_metadata(DEFAULT_METADATA)
        return DEFAULT_METADATA
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        # Se o schema mudou, mescla os defaults para nao perder bases novas
        if data.get("schema_version", 0) < DEFAULT_METADATA["schema_version"]:
            existing_ids = {b["id"] for b in data.get("bases", [])}
            for default_base in DEFAULT_METADATA["bases"]:
                if default_base["id"] not in existing_ids:
                    data.setdefault("bases", []).append(default_base)
            data["schema_version"] = DEFAULT_METADATA["schema_version"]
            save_metadata(data)
        return data
    except Exception as exc:
        print(f"[metadata_manager] erro lendo {METADATA_PATH}: {exc}")
        return DEFAULT_METADATA


def save_metadata(data: dict) -> None:
    """Salva metadata.json (cria diretorio se necessario)."""
    METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    data["ultima_revisao"] = datetime.now().isoformat()
    with open(METADATA_PATH, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def update_base_status(base_id: str, **fields) -> dict:
    """Atualiza uma base especifica. Aceita qualquer campo da estrutura.

    Sempre que chama, atualiza data_ultima_atualizacao para hoje.
    """
    data = load_metadata()
    bases = data.get("bases", [])
    for b in bases:
        if b.get("id") == base_id:
            for k, v in fields.items():
                b[k] = v
            b["data_ultima_atualizacao"] = _today_iso()
            if not b.get("data_importacao"):
                b["data_importacao"] = _today_iso()
            break
    save_metadata(data)
    return data


def mark_as_updated(base_id: str, responsavel: str = "") -> dict:
    """Atalho para marcar uma base como atualizada hoje."""
    return update_base_status(
        base_id,
        status="atualizado",
        responsavel=responsavel,
    )


def base_by_id(metadata: dict, base_id: str) -> Optional[dict]:
    for b in metadata.get("bases", []):
        if b.get("id") == base_id:
            return b
    return None


def evaluate_freshness(base: dict) -> str:
    """Decide o status real baseado na data e validade configurada."""
    last = base.get("data_ultima_atualizacao")
    if not last:
        return "pendente"
    try:
        last_date = date.fromisoformat(last)
    except Exception:
        return "pendente"
    validade = base.get("validade_anos", 0) or 0
    if validade <= 0:
        return base.get("status", "atualizado")
    age_days = (date.today() - last_date).days
    limit_days = validade * 365
    if age_days > limit_days:
        return "desatualizado"
    return "atualizado"
