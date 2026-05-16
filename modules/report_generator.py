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


def build_pdf_report(
    area_nome: str,
    zonas_df,
    pontos_df,
    od_matrix,
    od_summary_df,
    scenarios_compare,
    best_scenario_row,
) -> bytes | None:
    """Gera relatorio em PDF usando reportlab. None se reportlab indisponivel."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib import colors
        from reportlab.lib.units import cm
    except Exception:
        return None

    from io import BytesIO
    import pandas as pd

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Relatorio - Mobilidade Urbana",
    )
    styles = getSampleStyleSheet()
    h_style = ParagraphStyle(
        "Heading1Custom", parent=styles["Heading1"],
        textColor=colors.HexColor("#4A148C"),
    )
    h2_style = ParagraphStyle(
        "Heading2Custom", parent=styles["Heading2"],
        textColor=colors.HexColor("#6A1B9A"),
    )
    body = styles["BodyText"]
    body.alignment = TA_LEFT

    def df_to_table(df: pd.DataFrame, max_rows: int = 12) -> Table:
        if df is None or df.empty:
            return Paragraph("<i>(sem dados)</i>", body)
        df_disp = df.head(max_rows).copy()
        if hasattr(df_disp.index, "name") and df_disp.index.name is not None:
            df_disp = df_disp.reset_index()
        elif not df_disp.index.equals(pd.RangeIndex(len(df_disp))):
            df_disp = df_disp.reset_index()
        data = [list(df_disp.columns)] + df_disp.astype(str).values.tolist()
        # trunca strings longas
        data = [[str(c)[:35] for c in row] for row in data]
        tbl = Table(data, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, 0), colors.HexColor("#F3E5F5")),
            ("TEXTCOLOR",    (0, 0), (-1, 0), colors.HexColor("#4A148C")),
            ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",     (0, 0), (-1, -1), 8),
            ("GRID",         (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
            ("ALIGN",        (0, 0), (-1, -1), "LEFT"),
            ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return tbl

    story = []
    story.append(Paragraph("Relatorio - Mobilidade Urbana", h_style))
    story.append(Paragraph(f"<b>Area de estudo:</b> {area_nome}", body))
    story.append(Paragraph(f"<b>Gerado em:</b> {datetime.now().strftime('%d/%m/%Y %H:%M')}", body))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("1. Descricao da area de estudo", h2_style))
    story.append(Paragraph(
        "Estudo de mobilidade urbana em municipio de pequeno porte, com analise do efeito "
        "barreira gerado por ferrovia e rodovias federais/estaduais sobre a malha viaria local. "
        f"Area analisada: <b>{area_nome}</b>.", body,
    ))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("2. Zonas analiticas", h2_style))
    story.append(df_to_table(zonas_df))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("3. Pontos de interesse", h2_style))
    if pontos_df is not None and not pontos_df.empty:
        story.append(df_to_table(pontos_df, max_rows=20))
    else:
        story.append(Paragraph("<i>Nenhum ponto cadastrado durante a sessao.</i>", body))
    story.append(Spacer(1, 0.4 * cm))

    story.append(PageBreak())

    story.append(Paragraph("4. Matriz Origem-Destino", h2_style))
    story.append(Paragraph(
        "Modelo gravitacional simplificado: T_ij = (G_i &middot; A_j) / d_ij^&beta;, "
        "com &beta;=2 e normalizacao percentual.", body,
    ))
    story.append(df_to_table(od_matrix))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Resumo de viagens por zona:", body))
    story.append(df_to_table(od_summary_df))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("5. Comparacao de cenarios", h2_style))
    if scenarios_compare is not None and not scenarios_compare.empty:
        story.append(df_to_table(scenarios_compare))
    else:
        story.append(Paragraph("<i>Nenhum cenario adicional simulado.</i>", body))
    story.append(Spacer(1, 0.3 * cm))

    if best_scenario_row is not None:
        story.append(Paragraph("Cenario mais vantajoso:", h2_style))
        bs = [
            f"<b>Cenario:</b> {best_scenario_row['cenario']}",
            f"<b>Tipo:</b> {best_scenario_row['tipo']}",
            f"<b>Distancia media (km):</b> {best_scenario_row['distancia_media_km']}",
            f"<b>Tempo medio (min):</b> {best_scenario_row['tempo_medio_min']}",
            f"<b>Reducao de percurso:</b> {best_scenario_row['reducao_percurso_pct']}%",
            f"<b>Observacao:</b> {best_scenario_row['observacao']}",
        ]
        for line in bs:
            story.append(Paragraph(line, body))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("6. Limitacoes do modelo", h2_style))
    limits = [
        "Modelo gravitacional simplificado, com distancia haversine ou de rede entre centroides;",
        "Sem calibracao com contagens de trafego reais;",
        "Intervencoes representadas como alteracoes do custo de arestas no grafo;",
        "Dados iniciais aproximados - recomenda-se substituir por arquivos reais.",
    ]
    for line in limits:
        story.append(Paragraph(f"&bull; {line}", body))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph(
        f"<i>{DISCLAIMER}</i>",
        ParagraphStyle("Disclaimer", parent=body, textColor=colors.HexColor("#5D4037"),
                        fontSize=8, leftIndent=10),
    ))

    doc.build(story)
    return buf.getvalue()


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
