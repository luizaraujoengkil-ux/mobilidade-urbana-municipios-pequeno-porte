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


ZONAS_CONSOLIDATED_CSV = DEMO_DIR / "zonas_atualizadas.csv"
# Nomes alternativos aceitos (preserva compatibilidade entre versoes do template)
ZONAS_CSV_NAMES = [
    "zonas_atualizadas.csv",
    "zonas_template_matias_barbosa.csv",
    "zonas_template.csv",
    "zonas.csv",
]


def find_zones_csv() -> Optional[Path]:
    """Procura o CSV consolidado de zonas usando varios nomes possiveis."""
    for name in ZONAS_CSV_NAMES:
        path = DEMO_DIR / name
        if path.exists():
            return path
    return None


def update_zones_from_csv(
    zonas_df: pd.DataFrame,
    csv_path: str | Path = ZONAS_CONSOLIDATED_CSV,
) -> tuple[pd.DataFrame, list]:
    """Atualiza atributos das zonas a partir de CSV consolidado.

    Schema esperado:
    - zone_name (Z1, Z2, ...)
    - population_2010, population_2022
    - weight_generation, weight_attraction
    - primary_use, notes (opcionais)

    Campos vazios sao MANTIDOS com o valor anterior. Cada modificacao
    e registrada no log retornado.

    Retorna (zonas_df_atualizado, log_de_mudancas).
    """
    log = []
    csv_path = Path(csv_path)
    if not csv_path.exists():
        log.append(f"[ERRO] Arquivo nao encontrado: {csv_path}")
        return zonas_df, log
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(csv_path, encoding="latin-1")
            log.append("[INFO] CSV lido com encoding latin-1 (nao era UTF-8).")
        except Exception as exc:
            log.append(f"[ERRO] Falha ao ler CSV: {exc}")
            return zonas_df, log
    except Exception as exc:
        log.append(f"[ERRO] Falha ao ler CSV: {exc}")
        return zonas_df, log

    df.columns = [c.lower().strip() for c in df.columns]
    log.append(f"[INFO] Colunas detectadas: {list(df.columns)}")

    # mapeamento das colunas externas (CSV) -> internas (zonas_df)
    col_zone = next((c for c in ("zone_name", "zona", "code") if c in df.columns), None)
    if col_zone is None:
        log.append("[ERRO] CSV sem coluna 'zone_name' (ou 'zona'/'code'). Abortando.")
        return zonas_df, log

    # se zonas_df nao tem colunas para pop 2010/2022, cria
    out = zonas_df.copy()
    for col in ("populacao_2010", "populacao_2022"):
        if col not in out.columns:
            out[col] = None

    n_atualizadas = 0
    for _, csv_row in df.iterrows():
        zname = str(csv_row.get(col_zone, "")).strip().upper()
        if not zname:
            continue
        zone_codes = out["zona"].astype(str).str.upper().str.strip()
        mask = zone_codes == zname
        if not mask.any():
            log.append(f"[AVISO] Zona {zname} do CSV nao existe no estudo - ignorada.")
            continue
        idx = out.index[mask][0]

        zone_log = []
        def _apply(internal_col, csv_col, label, cast=float):
            if csv_col not in df.columns:
                return
            val = csv_row.get(csv_col)
            if pd.isna(val) or val == "" or val is None:
                zone_log.append(f"{label} mantido (CSV vazio)")
                return
            try:
                new_val = cast(val)
            except (ValueError, TypeError):
                zone_log.append(f"{label} invalido ({val!r}) - mantido")
                return
            old_val = out.loc[idx, internal_col] if internal_col in out.columns else None
            out.loc[idx, internal_col] = new_val
            zone_log.append(f"{label}: {old_val} -> {new_val}")

        _apply("populacao_2010", "population_2010", "pop2010")
        _apply("populacao_2022", "population_2022", "pop2022")
        # populacao 'corrente' segue 2022 se existir, senao 2010
        p22 = csv_row.get("population_2022")
        p10 = csv_row.get("population_2010")
        if not (pd.isna(p22) or p22 in (None, "")):
            try:
                out.loc[idx, "populacao"] = float(p22)
            except Exception:
                pass
        elif not (pd.isna(p10) or p10 in (None, "")):
            try:
                out.loc[idx, "populacao"] = float(p10)
            except Exception:
                pass
        _apply("geracao", "weight_generation", "geracao")
        _apply("atracao", "weight_attraction", "atracao")

        # campos texto opcionais
        if "primary_use" in df.columns:
            tipo = csv_row.get("primary_use")
            if not (pd.isna(tipo) or tipo in (None, "")):
                out.loc[idx, "tipo"] = str(tipo)
                zone_log.append(f"tipo atualizado")
        if "notes" in df.columns:
            obs = csv_row.get("notes")
            if not (pd.isna(obs) or obs in (None, "")):
                out.loc[idx, "observacoes"] = str(obs)
                zone_log.append(f"observacoes atualizadas")

        if zone_log:
            log.append(f"[{zname}] " + " | ".join(zone_log))
            n_atualizadas += 1

    log.append(f"[OK] {n_atualizadas} zona(s) atualizada(s) a partir do CSV.")
    return out, log


def export_population_from_zones(zonas_df: pd.DataFrame) -> None:
    """Extrai colunas populacao_2010 / populacao_2022 do zonas_df e salva
    nos CSVs do population_loader (compatibilidade com calibracao).
    """
    if zonas_df is None or zonas_df.empty:
        return
    if "populacao_2010" in zonas_df.columns:
        df10 = zonas_df[["zona", "populacao_2010"]].dropna()
        if not df10.empty:
            df10 = df10.rename(columns={"populacao_2010": "populacao"})
            save_population_csv(df10, 2010)
    if "populacao_2022" in zonas_df.columns:
        df22 = zonas_df[["zona", "populacao_2022"]].dropna()
        if not df22.empty:
            df22 = df22.rename(columns={"populacao_2022": "populacao"})
            save_population_csv(df22, 2022)


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
