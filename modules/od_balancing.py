"""Leitura de planilhas de producao/atracao e balanceamento da matriz OD.

Implementa as 4 primeiras etapas do modelo classico de transportes:
1) Geracao: producoes (P) e atracoes (A) por zona, lidas das planilhas
2) Balanceamento: ∑P = ∑A via fator multiplicativo no vetor menor
3) Distribuicao: aplicada externamente via modelo gravitacional
4) Repartição modal: simplificada (100% modo individual)

Formatos aceitos:
- Excel (.xlsx) - requer openpyxl
- CSV (.csv) - sempre suportado

Esquemas de coluna aceitos (case-insensitive):
- Zona:  'zona', 'zona_id', 'microzona', 'zone', 'zone_id', 'codigo', 'id'
- Valor: 'valor', 'viagens', 'producao', 'atracao', 'production',
        'attraction', 'trips', 'total', 'value', ou primeira col numerica
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEMO_DIR = DATA_DIR / "demo_matias_barbosa"

# Nomes aceitos para as planilhas (em ordem de preferencia)
PRODUCTION_FILE_NAMES = [
    "Matriz Destino (Vetor Origem).xlsx",
    "Matriz Destino (Vetor Origem).csv",
    "matriz_origem.xlsx",
    "matriz_origem.csv",
    "vetor_producao.xlsx",
    "vetor_producao.csv",
    "production_vector.xlsx",
    "production_vector.csv",
]
ATTRACTION_FILE_NAMES = [
    "Matriz de Atração (Vetor de Destino).xlsx",
    "Matriz de Atração (Vetor de Destino).csv",
    "Matriz de Atracao (Vetor de Destino).xlsx",
    "Matriz de Atracao (Vetor de Destino).csv",
    "matriz_destino.xlsx",
    "matriz_destino.csv",
    "vetor_atracao.xlsx",
    "vetor_atracao.csv",
    "attraction_vector.xlsx",
    "attraction_vector.csv",
]


def find_production_file() -> Optional[Path]:
    for name in PRODUCTION_FILE_NAMES:
        p = DEMO_DIR / name
        if p.exists():
            return p
    return None


def find_attraction_file() -> Optional[Path]:
    for name in ATTRACTION_FILE_NAMES:
        p = DEMO_DIR / name
        if p.exists():
            return p
    return None


def _load_vector_file(path: Path) -> tuple[Optional[pd.DataFrame], list]:
    """Le arquivo Excel ou CSV de vetor e normaliza para (zona, valor).

    Retorna (DataFrame, log) ou (None, log) se falhar.
    """
    log = []
    if not path.exists():
        log.append(f"[ERRO] Arquivo nao encontrado: {path}")
        return None, log

    suffix = path.suffix.lower()
    try:
        if suffix == ".xlsx":
            try:
                df = pd.read_excel(path)
            except ImportError as exc:
                log.append(f"[ERRO] openpyxl nao disponivel para Excel: {exc}")
                return None, log
            except Exception as exc:
                log.append(f"[ERRO] Falha ao ler Excel: {exc}")
                return None, log
        elif suffix == ".csv":
            try:
                df = pd.read_csv(path, encoding="utf-8")
            except UnicodeDecodeError:
                df = pd.read_csv(path, encoding="latin-1")
                log.append(f"[INFO] CSV lido com latin-1 (nao era UTF-8)")
        else:
            log.append(f"[ERRO] Formato nao suportado: {suffix}")
            return None, log
    except Exception as exc:
        log.append(f"[ERRO] Falha ao ler {path.name}: {exc}")
        return None, log

    # Normaliza nomes de colunas
    df.columns = [str(c).lower().strip() for c in df.columns]

    # Identifica coluna de zona
    zone_col = None
    for cand in ("zona", "zona_id", "microzona", "zone", "zone_id",
                 "codigo", "id", "zone_name"):
        if cand in df.columns:
            zone_col = cand
            break
    if zone_col is None and len(df.columns) > 0:
        zone_col = df.columns[0]
        log.append(f"[AVISO] Coluna de zona nao identificada. Usando primeira coluna: '{zone_col}'")

    # Identifica coluna de valor numerico
    value_col = None
    for cand in ("valor", "viagens", "producao", "producao_diaria",
                 "atracao", "atracao_diaria", "production", "attraction",
                 "trips", "total", "value", "qtd", "quantidade"):
        if cand in df.columns:
            value_col = cand
            break
    if value_col is None:
        # tenta primeira coluna numerica diferente da zona
        numeric_cols = [c for c in df.columns if c != zone_col
                        and pd.api.types.is_numeric_dtype(
                            pd.to_numeric(df[c], errors="coerce")
                        )]
        if numeric_cols:
            value_col = numeric_cols[0]
            log.append(f"[AVISO] Coluna de valor nao identificada. Usando '{value_col}' (primeira numerica)")
        else:
            log.append(f"[ERRO] Nenhuma coluna numerica encontrada em {path.name}")
            return None, log

    out = pd.DataFrame({
        "zona": df[zone_col].astype(str).str.strip().str.upper(),
        "valor": pd.to_numeric(df[value_col], errors="coerce"),
    })
    # Trata valores ausentes
    n_nan = out["valor"].isna().sum()
    if n_nan > 0:
        log.append(f"[AVISO] {n_nan} valor(es) nao numerico(s) substituido(s) por 0")
        out["valor"] = out["valor"].fillna(0)
    # Remove linhas sem zona
    out = out[out["zona"].str.len() > 0]
    out = out[~out["zona"].isin(("NAN", "NONE", ""))]

    log.append(f"[OK] {len(out)} linhas lidas de {path.name}")
    log.append(f"     Colunas usadas: zona='{zone_col}', valor='{value_col}'")
    log.append(f"     Soma total: {out['valor'].sum():.2f}")
    return out, log


def load_production_vector(path: Path) -> tuple[Optional[pd.DataFrame], list]:
    """Carrega o vetor de producao (origens) - 'Matriz Destino (Vetor Origem)'."""
    return _load_vector_file(path)


def load_attraction_vector(path: Path) -> tuple[Optional[pd.DataFrame], list]:
    """Carrega o vetor de atracao (destinos) - 'Matriz de Atracao (Vetor de Destino)'."""
    return _load_vector_file(path)


def balance_vectors(prod_df: pd.DataFrame, attr_df: pd.DataFrame) -> dict:
    """Balanceia os vetores P (producao) e A (atracao) para que ∑P = ∑A.

    Estrategia: ajusta o vetor MENOR multiplicando por (∑maior / ∑menor).
    Convencao em transportes: a producao geralmente eh mantida e a atracao
    eh balanceada; aqui detectamos automaticamente qual ajustar.

    Retorna dict com:
    - production_balanced, attraction_balanced (DataFrames)
    - factor: fator multiplicativo aplicado
    - adjusted: 'production', 'attraction' ou None (ja balanceado)
    - sum_prod_original, sum_attr_original
    - sum_prod_balanced, sum_attr_balanced
    - log: lista de mensagens descritivas
    """
    log = []
    sum_p = float(prod_df["valor"].sum())
    sum_a = float(attr_df["valor"].sum())

    log.append(f"Soma original de producao  ∑P = {sum_p:,.2f}")
    log.append(f"Soma original de atracao   ∑A = {sum_a:,.2f}")
    log.append(f"Diferenca |∑P - ∑A| = {abs(sum_p - sum_a):,.2f}")

    prod_balanced = prod_df.copy()
    attr_balanced = attr_df.copy()

    if abs(sum_p - sum_a) < 1e-9:
        log.append("✅ Vetores ja estao balanceados (∑P = ∑A). Nenhum ajuste aplicado.")
        return {
            "production_balanced": prod_balanced,
            "attraction_balanced": attr_balanced,
            "factor": 1.0,
            "adjusted": None,
            "sum_prod_original": sum_p,
            "sum_attr_original": sum_a,
            "sum_prod_balanced": sum_p,
            "sum_attr_balanced": sum_a,
            "log": log,
        }

    if sum_p > sum_a:
        if sum_a <= 0:
            log.append("[ERRO] ∑A = 0 - impossivel balancear pela atracao.")
            return {
                "production_balanced": prod_balanced,
                "attraction_balanced": attr_balanced,
                "factor": 1.0, "adjusted": None,
                "sum_prod_original": sum_p, "sum_attr_original": sum_a,
                "sum_prod_balanced": sum_p, "sum_attr_balanced": sum_a,
                "log": log,
            }
        factor = sum_p / sum_a
        attr_balanced["valor"] = attr_balanced["valor"] * factor
        log.append(f"📐 Vetor de ATRACAO ajustado: cada valor × {factor:.4f}")
        adjusted = "attraction"
    else:
        if sum_p <= 0:
            log.append("[ERRO] ∑P = 0 - impossivel balancear pela producao.")
            return {
                "production_balanced": prod_balanced,
                "attraction_balanced": attr_balanced,
                "factor": 1.0, "adjusted": None,
                "sum_prod_original": sum_p, "sum_attr_original": sum_a,
                "sum_prod_balanced": sum_p, "sum_attr_balanced": sum_a,
                "log": log,
            }
        factor = sum_a / sum_p
        prod_balanced["valor"] = prod_balanced["valor"] * factor
        log.append(f"📐 Vetor de PRODUCAO ajustado: cada valor × {factor:.4f}")
        adjusted = "production"

    sum_p_new = float(prod_balanced["valor"].sum())
    sum_a_new = float(attr_balanced["valor"].sum())
    log.append(f"Pos-balanceamento: ∑P = {sum_p_new:,.2f}, ∑A = {sum_a_new:,.2f}")
    log.append(f"✅ Balanceamento concluido (∑P = ∑A = {sum_p_new:,.2f})")

    return {
        "production_balanced": prod_balanced,
        "attraction_balanced": attr_balanced,
        "factor": factor,
        "adjusted": adjusted,
        "sum_prod_original": sum_p,
        "sum_attr_original": sum_a,
        "sum_prod_balanced": sum_p_new,
        "sum_attr_balanced": sum_a_new,
        "log": log,
    }


def apply_to_zones(
    zonas_df: pd.DataFrame,
    prod_balanced: pd.DataFrame,
    attr_balanced: pd.DataFrame,
) -> tuple[pd.DataFrame, list]:
    """Atualiza geracao/atracao das zonas usando os vetores balanceados.

    Zonas presentes no vetor mas ausentes no zonas_df sao IGNORADAS
    (com aviso no log) - util quando as planilhas usam microzonas (Z3a,
    Z3b) e o estudo atual ainda esta agregado em Z3.

    Zonas presentes no zonas_df mas ausentes nas planilhas mantem seus
    valores anteriores.
    """
    log = []
    out = zonas_df.copy()

    prod_map = dict(zip(
        prod_balanced["zona"].astype(str).str.upper(),
        prod_balanced["valor"],
    ))
    attr_map = dict(zip(
        attr_balanced["zona"].astype(str).str.upper(),
        attr_balanced["valor"],
    ))

    novas_gera = []
    novas_atra = []
    n_updated = 0
    zonas_missing = []
    zonas_pre_existentes = set(out["zona"].astype(str).str.upper())

    for idx, row in out.iterrows():
        z = str(row.get("zona", "")).upper().strip()
        old_g = float(row.get("geracao", 50.0))
        old_a = float(row.get("atracao", 50.0))
        new_g = float(prod_map[z]) if z in prod_map else old_g
        new_a = float(attr_map[z]) if z in attr_map else old_a
        novas_gera.append(new_g)
        novas_atra.append(new_a)
        if z in prod_map or z in attr_map:
            n_updated += 1
            log.append(
                f"  {z}: geracao {old_g:.2f} → {new_g:.2f}, "
                f"atracao {old_a:.2f} → {new_a:.2f}"
            )
        else:
            zonas_missing.append(z)

    out["geracao"] = novas_gera
    out["atracao"] = novas_atra

    log.insert(0, f"✅ {n_updated} zona(s) atualizada(s) com vetores balanceados.")

    if zonas_missing:
        log.append(
            f"⚠️ Zonas SEM dados nas planilhas (mantidos valores anteriores): "
            f"{', '.join(zonas_missing)}"
        )

    # Zonas das planilhas que nao existem no estudo
    todas_zonas_planilhas = set(prod_map.keys()) | set(attr_map.keys())
    nao_aplicadas = todas_zonas_planilhas - zonas_pre_existentes
    if nao_aplicadas:
        log.append(
            f"ℹ️ Zonas das planilhas NAO existentes no estudo atual "
            f"(pendentes ate importar microzonas): {', '.join(sorted(nao_aplicadas))}"
        )

    return out, log


def run_full_balancing_pipeline(
    zonas_df: pd.DataFrame,
    prod_path: Path,
    attr_path: Path,
) -> dict:
    """Pipeline completo: le, balanceia e aplica. Util para uso na UI.

    Retorna dict com:
    - zonas_df_atualizado, balance_info (factor/adjusted/somas),
    - log_consolidado, sucesso (bool)
    """
    log = []
    log.append("=" * 60)
    log.append("MODELO DE 4 ETAPAS - Etapa 1+2 (Geracao + Balanceamento)")
    log.append("=" * 60)

    # 1. Carrega producao
    log.append(f"\n📂 Lendo PRODUCAO de: {prod_path.name}")
    prod_df, prod_log = load_production_vector(prod_path)
    log.extend(prod_log)
    if prod_df is None:
        return {"sucesso": False, "log_consolidado": log,
                "zonas_df_atualizado": zonas_df, "balance_info": None}

    # 2. Carrega atracao
    log.append(f"\n📂 Lendo ATRACAO de: {attr_path.name}")
    attr_df, attr_log = load_attraction_vector(attr_path)
    log.extend(attr_log)
    if attr_df is None:
        return {"sucesso": False, "log_consolidado": log,
                "zonas_df_atualizado": zonas_df, "balance_info": None}

    # 3. Balanceamento
    log.append(f"\n⚖️ BALANCEAMENTO ∑P = ∑A")
    bal = balance_vectors(prod_df, attr_df)
    log.extend(bal["log"])

    # 4. Aplica nas zonas
    log.append(f"\n🎯 Aplicando aos zonas analiticas do estudo:")
    zonas_new, apply_log = apply_to_zones(
        zonas_df, bal["production_balanced"], bal["attraction_balanced"]
    )
    log.extend(apply_log)

    return {
        "sucesso": True,
        "log_consolidado": log,
        "zonas_df_atualizado": zonas_new,
        "balance_info": bal,
        "production_df": prod_df,
        "attraction_df": attr_df,
    }
