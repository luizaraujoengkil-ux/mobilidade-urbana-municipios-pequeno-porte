"""Geracao de relatorio textual (markdown / texto / html)."""
from __future__ import annotations

from datetime import datetime
from io import StringIO

import pandas as pd

from .config import DISCLAIMER


def _df_to_md(df: pd.DataFrame) -> str:
    if df is None or df.empty:
        return "_(sem dados)_"
    try:
        return df.to_markdown(index=True)
    except Exception:
        return "```\n" + df.to_string() + "\n```"


def build_markdown_report(
    area_nome: str,
    zonas_df: pd.DataFrame,
    pontos_df: pd.DataFrame,
    od_matrix: pd.DataFrame,
    od_summary_df: pd.DataFrame,
    scenarios_compare: pd.DataFrame,
    best_scenario_row,
) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    out = StringIO()
    w = out.write

    w(f"# Relatorio - Mobilidade Urbana\n\n")
    w(f"**Area de estudo:** {area_nome}\n\n")
    w(f"**Gerado em:** {now}\n\n")
    w("---\n\n")

    w("## 1. Descricao da area de estudo\n\n")
    w("Estudo de mobilidade urbana em municipio de pequeno porte, com analise do efeito ")
    w("barreira gerado por ferrovia e rodovias federais/estaduais sobre a malha viaria local. ")
    w(f"Area analisada: **{area_nome}**.\n\n")

    w("## 2. Zonas analiticas consideradas\n\n")
    w(_df_to_md(zonas_df))
    w("\n\n")

    w("## 3. Pontos criticos / de interesse\n\n")
    if pontos_df is not None and not pontos_df.empty:
        w(_df_to_md(pontos_df))
    else:
        w("_Nenhum ponto cadastrado durante a sessao._")
    w("\n\n")

    w("## 4. Matriz Origem-Destino (modelo gravitacional simplificado)\n\n")
    w("Modelo utilizado: $T_{ij} = (G_i \\cdot A_j) / d_{ij}^{\\beta}$ com $\\beta=2$ e ")
    w("normalizacao percentual.\n\n")
    w(_df_to_md(od_matrix))
    w("\n\n### Resumo de viagens por zona\n\n")
    w(_df_to_md(od_summary_df))
    w("\n\n")

    w("## 5. Comparacao de cenarios\n\n")
    if scenarios_compare is not None and not scenarios_compare.empty:
        w(_df_to_md(scenarios_compare))
    else:
        w("_Nenhum cenario adicional simulado._")
    w("\n\n")

    w("## 6. Cenario mais vantajoso\n\n")
    if best_scenario_row is not None:
        w(f"- **Cenario:** {best_scenario_row['cenario']}\n")
        w(f"- **Tipo:** {best_scenario_row['tipo']}\n")
        w(f"- **Distancia media (km):** {best_scenario_row['distancia_media_km']}\n")
        w(f"- **Tempo medio (min):** {best_scenario_row['tempo_medio_min']}\n")
        w(f"- **Reducao percentual de percurso:** {best_scenario_row['reducao_percurso_pct']}%\n")
        w(f"- **Observacao:** {best_scenario_row['observacao']}\n\n")
    else:
        w("_Sem cenarios alternativos para comparar._\n\n")

    w("## 7. Limitacoes do modelo\n\n")
    w("- O modelo gravitacional utilizado e simplificado e usa distancia euclidiana ")
    w("(haversine) entre centroides de zona, nao representando capacidade viaria nem ")
    w("congestionamentos.\n")
    w("- As intervencoes sao representadas por reducao/aumento do custo de uma aresta ")
    w("no grafo, sem calibracao por contagem de trafego.\n")
    w("- Os dados geograficos iniciais sao aproximados; arquivos reais devem ser ")
    w("substituidos para uso analitico.\n")
    w("- O sistema nao realiza alocacao de viagens em rede nem analise de servico de ")
    w("transporte coletivo.\n\n")

    w("---\n\n")
    w(f"> {DISCLAIMER}\n")
    return out.getvalue()


def build_html_report(md_text: str, title: str = "Relatorio - Mobilidade Urbana") -> str:
    """Conversao simples de markdown para HTML (sem dependencias extras)."""
    # Conversao basica: paragrafos, headings, tabelas markdown
    try:
        import markdown  # type: ignore
        body = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    except Exception:
        body = "<pre>" + md_text.replace("<", "&lt;") + "</pre>"

    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8" />
<title>{title}</title>
<style>
 body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 960px; margin: 2em auto; padding: 0 1em; color: #222; }}
 h1, h2, h3 {{ color: #4A148C; }}
 table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
 th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; }}
 th {{ background: #F3E5F5; }}
 blockquote {{ border-left: 4px solid #B83DBA; padding: .5em 1em; background: #FAF4FB; color: #444; }}
 code, pre {{ background: #F4F4F4; padding: 2px 4px; border-radius: 4px; }}
</style>
</head>
<body>
{body}
</body>
</html>"""
    return html
