"""Carregamento de bases populacionais IPEA 2010 e IBGE 2022.

Aceita arquivos CSV simples com colunas:
- zona: codigo (Z1, Z2, Z3, Z4...)
- populacao: numero de habitantes
- (opcional) nome, observacoes

Os arquivos podem ser carregados via upload no app (UploadedFile) ou
copiados manualmente para data/demo_matias_barbosa/populacao_*.csv.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DEMO_DIR = DATA_DIR / "demo_matias_barbosa"


def population_file_path(year: int) -> Path:
    """Convencao: data/demo_matias_barbosa/populacao_<ano>.csv."""
    return DEMO_DIR / f"populacao_{year}.csv"


def load_population_csv(path: str | Path) -> Optional[pd.DataFrame]:
    """Le CSV de populacao. Espera colunas: zona, populacao.

    Retorna DataFrame com colunas 'zona' (str) e 'populacao' (int).
    Retorna None se nao encontrar o arquivo.
    """
    p = Path(path)
    if not p.exists():
        return None
    try:
        df = pd.read_csv(p)
    except Exception as exc:
        print(f"[population_loader] erro lendo {p}: {exc}")
        return None
    # Normaliza nomes de colunas
    df.columns = [c.lower().strip() for c in df.columns]
    if "zona" not in df.columns:
        return None
    pop_col = None
    for cand in ("populacao", "pop", "habitantes", "total"):
        if cand in df.columns:
            pop_col = cand
            break
    if pop_col is None:
        return None
    out = df[["zona", pop_col]].copy()
    out["zona"] = out["zona"].astype(str).str.upper().str.strip()
    out["populacao"] = pd.to_numeric(out[pop_col], errors="coerce").fillna(0).astype(int)
    out = out[["zona", "populacao"]]
    return out


def load_population_demo(year: int) -> Optional[pd.DataFrame]:
    """Carrega CSV padrao da pasta demo para o ano indicado."""
    return load_population_csv(population_file_path(year))


def save_population_csv(df: pd.DataFrame, year: int) -> Path:
    """Salva DataFrame no formato padrao em data/demo_matias_barbosa/."""
    dest = population_file_path(year)
    dest.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(dest, index=False, encoding="utf-8")
    return dest


def compare_populations(df2010: pd.DataFrame, df2022: pd.DataFrame) -> pd.DataFrame:
    """Tabela comparativa 2010 vs 2022 por zona.

    Calcula variacao absoluta e percentual + peso de geracao sugerido
    (proporcional a populacao 2022 quando disponivel; senao 2010).
    """
    d10 = df2010.set_index("zona")["populacao"] if df2010 is not None else None
    d22 = df2022.set_index("zona")["populacao"] if df2022 is not None else None
    all_zonas = sorted(set((d10.index.tolist() if d10 is not None else []) +
                            (d22.index.tolist() if d22 is not None else [])))
    rows = []
    for z in all_zonas:
        p10 = int(d10[z]) if d10 is not None and z in d10.index else None
        p22 = int(d22[z]) if d22 is not None and z in d22.index else None
        if p10 and p22:
            delta = p22 - p10
            pct = (delta / p10) * 100 if p10 else 0
        else:
            delta = None
            pct = None
        rows.append({
            "zona": z,
            "populacao_2010": p10,
            "populacao_2022": p22,
            "variacao_absoluta": delta,
            "variacao_percentual": round(pct, 1) if pct is not None else None,
        })
    df = pd.DataFrame(rows)
    # Peso de geracao sugerido: proporcional ao maximo populacional
    base_pop = df["populacao_2022"].fillna(df["populacao_2010"])
    if base_pop.notna().any() and base_pop.max() > 0:
        df["peso_geracao_sugerido"] = (base_pop / base_pop.max() * 100).round(1)
    else:
        df["peso_geracao_sugerido"] = None
    return df


def calibrate_weights_from_population(
    zonas_df: pd.DataFrame,
    pop_df: pd.DataFrame,
    scale: float = 100.0,
) -> pd.DataFrame:
    """Recalibra geracao/atracao das zonas em funcao da populacao.

    Estrategia simples:
    - geracao_i = (pop_i / max(pop)) * scale
    - atracao_i = mantem como esta (atracao depende de POIs, nao populacao)

    Retorna copia do zonas_df com colunas atualizadas.
    """
    if zonas_df is None or zonas_df.empty:
        return zonas_df
    if pop_df is None or pop_df.empty:
        return zonas_df.copy()
    out = zonas_df.copy()
    pop_map = pop_df.set_index("zona")["populacao"].to_dict()
    max_pop = max(pop_map.values()) if pop_map else 1
    if max_pop <= 0:
        max_pop = 1
    novas_geracoes = []
    for _, row in out.iterrows():
        z = str(row.get("zona", "")).upper().strip()
        pop = pop_map.get(z)
        if pop is None:
            novas_geracoes.append(row.get("geracao", 50.0))
        else:
            novas_geracoes.append(round((pop / max_pop) * scale, 1))
    out["geracao"] = novas_geracoes
    return out
