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
    metadata_bases: dict = None,        # opcional
    calibration_source: str = None,     # opcional
    rail_params_data: dict = None,      # opcional
    rail_blocking_table: list = None,   # opcional
    social_cost: dict = None,           # opcional
    assignment_edges_df=None,           # opcional
    odm_detailed_df=None,               # opcional - matriz OD via CSV detalhado
    odm_scenarios_compare=None,         # opcional - comparativo base vs cenarios CSV
    social_cost_per_scenario=None,      # opcional - lista de custos por cenario
    balancing_info: dict = None,        # opcional - resultado do balanceamento P/A
    production_df=None,                 # opcional - vetor de producao balanceado
    attraction_df=None,                 # opcional - vetor de atracao balanceado
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

    # ----- Secao Modelo 4 Etapas (se balanceamento foi aplicado) -----
    if balancing_info is not None:
        w("## 3.5. Balanceamento da matriz OD (Modelo de 4 Etapas)\n\n")
        w("Foi aplicado o procedimento classico de balanceamento da matriz OD "
          "previsto na **Etapa 2 do modelo de 4 etapas** (Geracao → "
          "Balanceamento → Distribuicao → Alocacao):\n\n")
        w(f"- **Soma original de producao (∑P):** {balancing_info.get('sum_prod_original', 0):,.2f}\n")
        w(f"- **Soma original de atracao  (∑A):** {balancing_info.get('sum_attr_original', 0):,.2f}\n")
        if balancing_info.get("adjusted"):
            w(f"- **Vetor ajustado:** {balancing_info['adjusted']} "
              f"(multiplicado por **× {balancing_info['factor']:.4f}**)\n")
        else:
            w(f"- **Vetor ajustado:** nenhum (∑P ja era igual a ∑A)\n")
        w(f"- **∑P balanceado = ∑A balanceado = {balancing_info.get('sum_prod_balanced', 0):,.2f}**\n\n")
        if production_df is not None and not production_df.empty:
            w("### Vetor de PRODUCAO (origens) - balanceado\n\n")
            w(_df_to_md(production_df))
            w("\n\n")
        if attraction_df is not None and not attraction_df.empty:
            w("### Vetor de ATRACAO (destinos) - balanceado\n\n")
            w(_df_to_md(attraction_df))
            w("\n\n")
        w("> **Repartição modal:** assumida 100% modo individual (veiculos "
          "particulares) por simplificacao. A inclusao de transporte coletivo "
          "e modos ativos exige pesquisa de mobilidade local.\n\n")

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

    # ----- Novas secoes opcionais (apenas se houver dados) -----
    if metadata_bases:
        w("## 7. Status das bases de dados\n\n")
        rows_meta = []
        for b in metadata_bases.get("bases", []):
            rows_meta.append({
                "Base": b.get("nome", b.get("id", "")),
                "Fonte": b.get("fonte", ""),
                "Ano": b.get("ano", "") or "",
                "Ultima atualizacao": b.get("data_ultima_atualizacao", "") or "—",
                "Status": b.get("status", ""),
            })
        if rows_meta:
            df_m = pd.DataFrame(rows_meta)
            w(_df_to_md(df_m))
            w("\n\n")
        if calibration_source:
            w(f"**Calibracao da geracao de viagens:** {calibration_source}\n\n")

    if rail_params_data is not None:
        w("## 8. Parametros ferroviarios\n\n")
        w(f"- **Velocidade media:** {rail_params_data.get('velocidade_media_kmh', '—')} km/h  \n")
        w(f"- **Fator operacional de bloqueio:** {rail_params_data.get('fator_operacional_bloqueio', '—')}  \n")
        w(f"- **Passagens por dia:** {rail_params_data.get('passagens_por_dia', '—')}  \n")
        if rail_blocking_table:
            w("\n### Calculo de tempo de bloqueio por tipo de trem\n\n")
            w(_df_to_md(pd.DataFrame(rail_blocking_table)))
            w("\n\n")

    if social_cost:
        w("## 9. Custo social do bloqueio ferroviario\n\n")
        w(f"- Pessoas afetadas por bloqueio: **{social_cost.get('pessoas_afetadas_por_bloqueio', '—')}**  \n")
        w(f"- Horas perdidas por bloqueio: **{social_cost.get('horas_perdidas_por_bloqueio', '—')}**  \n")
        w(f"- Custo por bloqueio: **R$ {social_cost.get('custo_por_bloqueio_R$', '—')}**  \n")
        w(f"- Custo diario estimado: **R$ {social_cost.get('custo_diario_R$', '—')}**  \n")
        w(f"- **Custo anual estimado: R$ {social_cost.get('custo_anual_R$', '—')}**  \n")
        w(f"- Atraso anual estimado: **{social_cost.get('atraso_anual_horas', '—')} horas**  \n\n")
        w("> Valores exploratorios - dependem de calibracao com dados locais.\n\n")

    if social_cost_per_scenario:
        w("### Comparativo de custo social por cenario\n\n")
        df_sc_cost = pd.DataFrame(social_cost_per_scenario)
        # formata colunas R$
        df_disp = df_sc_cost.copy()
        for col in ("custo_diario_R$", "custo_anual_R$", "economia_vs_base_R$"):
            if col in df_disp.columns:
                df_disp[col] = df_disp[col].apply(
                    lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(
                        ".", ",").replace("X", ".")
                    if isinstance(v, (int, float)) else v
                )
        if "economia_pct" in df_disp.columns:
            df_disp["economia_pct"] = df_disp["economia_pct"].apply(
                lambda v: f"{v:.1f}%" if isinstance(v, (int, float)) else v
            )
        w(_df_to_md(df_disp))
        w("\n\n")
        # Identifica o melhor cenario
        non_base = [r for r in social_cost_per_scenario
                    if not str(r.get("cenario", "")).lower().startswith("base")]
        if non_base:
            best_cost = max(non_base, key=lambda r: r.get("economia_vs_base_R$", 0))
            if best_cost.get("economia_vs_base_R$", 0) > 0:
                eco = best_cost["economia_vs_base_R$"]
                pct = best_cost.get("economia_pct", 0)
                w(f"- **Cenario com maior economia social:** "
                  f"**{best_cost['cenario']}**  \n")
                w(f"- **Economia anual estimada:** "
                  f"R$ {eco:,.2f}".replace(",", "X").replace(
                      ".", ",").replace("X", ".") +
                  f" ({pct:.1f}% de reducao do custo social)\n\n")

    if odm_detailed_df is not None and not odm_detailed_df.empty:
        w("## 10. Matriz OD detalhada com atrasos e bloqueios\n\n")
        w("Dados importados do CSV de matriz O-D detalhada (`origin_zone`, "
          "`destination_zone`, distancias base/melhorada, travessias, "
          "bloqueios diarios e atraso por viagem).\n\n")
        # Tabela resumida dos pares base
        base_pairs = odm_detailed_df[
            odm_detailed_df["access_scenario"].str.lower().eq("base")
        ]
        if not base_pairs.empty:
            cols_show = [c for c in [
                "origin_zone", "destination_zone",
                "base_distance_km", "base_travel_time_min",
                "daily_blockage_minutes", "delay_per_trip_min",
                "road_crossings_count", "rail_crossings_count",
            ] if c in base_pairs.columns]
            inter = base_pairs[base_pairs["origin_zone"] != base_pairs["destination_zone"]]
            w("### Pares O-D base (com travessias/bloqueios)\n\n")
            w(_df_to_md(inter[cols_show] if cols_show else inter))
            w("\n\n")

            # Estatistica de atraso total
            total_blockage = pd.to_numeric(
                inter.get("daily_blockage_minutes"), errors="coerce"
            ).dropna().sum() if "daily_blockage_minutes" in inter.columns else 0
            mean_delay = pd.to_numeric(
                inter.get("delay_per_trip_min"), errors="coerce"
            ).dropna().mean() if "delay_per_trip_min" in inter.columns else 0
            if total_blockage > 0 or mean_delay > 0:
                w(f"- **Tempo total de bloqueio diario somado:** "
                  f"{total_blockage:.0f} min ({total_blockage/60:.1f} h)  \n")
                w(f"- **Atraso medio por viagem:** {mean_delay:.2f} min\n\n")

        if odm_scenarios_compare is not None and not odm_scenarios_compare.empty:
            w("### Comparativo base vs cenarios (do CSV)\n\n")
            w(_df_to_md(odm_scenarios_compare))
            w("\n\n")
            # Identifica cenario com maior economia
            sc_with_red = odm_scenarios_compare[
                pd.to_numeric(odm_scenarios_compare.get("reducao_tempo_pct"),
                              errors="coerce").fillna(0) > 0
            ]
            if not sc_with_red.empty:
                best = sc_with_red.loc[
                    pd.to_numeric(sc_with_red["reducao_tempo_pct"],
                                  errors="coerce").idxmax()
                ]
                w(f"- **Cenario com maior reducao de tempo:** "
                  f"**{best['cenario']}** "
                  f"({best['reducao_tempo_pct']:.1f}% de reducao no tempo "
                  f"medio entre zonas)\n\n")

    if assignment_edges_df is not None and not assignment_edges_df.empty:
        w("## 11. Alocacao simplificada na rede (top 10 trechos)\n\n")
        cols = [c for c in ["nome_via", "highway", "comprimento_m",
                            "fluxo_acumulado", "n_pares_od"]
                if c in assignment_edges_df.columns]
        w(_df_to_md(assignment_edges_df.head(10)[cols] if cols
                    else assignment_edges_df.head(10)))
        w("\n\n")
        w("> Alocacao all-or-nothing - exploratoria. Nao substitui modelo de "
          "trafego calibrado, contagens volumetricas ou simulacao microscopica.\n\n")

    w("## 12. Limitacoes do modelo\n\n")
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
