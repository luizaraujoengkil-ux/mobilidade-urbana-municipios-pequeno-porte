"""
Prototipo Web - Mobilidade Urbana em Municipios de Pequeno Porte
Estudo de Caso: Matias Barbosa / MG
Disciplina: Planejamento de Transportes - IME
"""
from __future__ import annotations

import io
import json
from datetime import datetime

import folium
import geopandas as gpd
import pandas as pd
import plotly.express as px
import streamlit as st
from shapely.geometry import Point
from streamlit_folium import st_folium

from modules import (
    data_loader,
    map_utils,
    network_analysis as net,
    od_matrix,
    report_generator,
    scenario_analysis as scen,
)
from modules.config import (
    COLORS,
    DEFAULT_ZOOM,
    DISCLAIMER,
    MATIAS_BARBOSA_CENTER,
    POINT_CATEGORIES,
    ZONE_TYPES,
)


# ---------------------------------------------------------------------------
# CONFIG STREAMLIT
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Mobilidade Urbana - Matias Barbosa/MG",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Estilo customizado
st.markdown(
    """
    <style>
        .main .block-container {padding-top: 1.5rem; padding-bottom: 2rem; max-width: 100%;}
        h1, h2, h3 {color: #4A148C;}
        .kpi-card {
            background: linear-gradient(135deg, #F5EAFB 0%, #FFFFFF 100%);
            border-left: 5px solid #B83DBA;
            padding: 14px 16px;
            border-radius: 10px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.06);
            margin-bottom: 8px;
        }
        .kpi-title {font-size: 0.85rem; color: #555; margin-bottom: 4px;}
        .kpi-value {font-size: 1.6rem; font-weight: 700; color: #4A148C;}
        .legend-dot {display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin-right: 6px; vertical-align: middle;}
        .disclaimer {background: #FFF8E1; border-left: 4px solid #F9A825; padding: 10px 14px; border-radius: 6px; font-size: 0.85rem;}
        .stTabs [data-baseweb="tab"] {font-weight: 600;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# ESTADO DA SESSAO
# ---------------------------------------------------------------------------
def init_session_state() -> None:
    if "initialized" in st.session_state:
        return

    layers = data_loader.load_sample_layers()
    st.session_state.layers = layers
    st.session_state.uploaded_layers = {}  # nome -> gdf

    # Pontos cadastrados manualmente durante a sessao
    st.session_state.user_points = pd.DataFrame(
        columns=["nome", "categoria", "latitude", "longitude", "descricao"]
    )

    # Tabela de zonas para a matriz O-D (editavel)
    st.session_state.zonas_df = od_matrix.default_zonas_dataframe(layers.get("zonas"))

    # Cenarios
    st.session_state.scenarios = [
        scen.Scenario(nome="Cenario Atual", tipo="Cenario atual",
                      descricao="Estado atual sem intervencoes adicionais")
    ]

    # Camadas ativas (toggles)
    st.session_state.show_layers = {
        "area_estudo": True,
        "zonas": True,
        "ferrovia": True,
        "rodovias": True,
        "pontos_viaduto": True,
        "pontos_interesse": True,
        "user_points": True,
        "uploaded": True,
        "flow": False,
    }

    # Resultados calculados
    st.session_state.od_result = None  # DataFrame
    st.session_state.od_summary = None
    st.session_state.flow_records = []
    st.session_state.base_graph = None
    st.session_state.compare_df = None

    st.session_state.initialized = True


init_session_state()


# ---------------------------------------------------------------------------
# CABECALHO
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:14px;">
        <div style="font-size:2.5rem;">🗺️</div>
        <div>
            <h1 style="margin-bottom:0;">Rodovias, Ferrovias e Mobilidade Urbana</h1>
            <p style="margin-top:4px;font-size:1.0rem;color:#555;">
                Prototipo de apoio a analise de mobilidade em municipios de pequeno porte
                &mdash; Estudo de caso: <b>Matias Barbosa / MG</b>
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.divider()


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Painel de Controle")

    st.subheader("📍 Area de estudo")
    st.text_input("Nome do municipio", value="Matias Barbosa - MG", key="municipio_nome")

    st.subheader("🗺️ Camadas visiveis")
    show = st.session_state.show_layers
    show["area_estudo"]     = st.checkbox("Area de estudo",        value=show["area_estudo"])
    show["zonas"]           = st.checkbox("Zonas analiticas",      value=show["zonas"])
    show["ferrovia"]        = st.checkbox("Linha do trem",         value=show["ferrovia"])
    show["rodovias"]        = st.checkbox("Rodovias (BR-040/MG-353/Uniao Industria)", value=show["rodovias"])
    show["pontos_viaduto"]  = st.checkbox("Pontos de estudo de viaduto", value=show["pontos_viaduto"])
    show["pontos_interesse"]= st.checkbox("Pontos de interesse",   value=show["pontos_interesse"])
    show["user_points"]     = st.checkbox("Pontos cadastrados na sessao", value=show["user_points"])
    show["uploaded"]        = st.checkbox("Arquivos importados",   value=show["uploaded"])
    show["flow"]            = st.checkbox("Linhas de fluxo O-D",   value=show["flow"])

    st.divider()

    st.subheader("🎨 Legenda")
    st.markdown(
        f"""
        <div style='font-size:0.85rem;line-height:1.7'>
            <span class='legend-dot' style='background:{COLORS["Z1"]}'></span> Z1 - Centro / Nucleo<br>
            <span class='legend-dot' style='background:{COLORS["Z2"]}'></span> Z2 - Sudeste<br>
            <span class='legend-dot' style='background:{COLORS["Z3"]}'></span> Z3 - Dispersa<br>
            <span class='legend-dot' style='background:{COLORS["Z4"]}'></span> Z4 - Industrial<br>
            <span class='legend-dot' style='background:{COLORS["trem"]}'></span> Linha do trem<br>
            <span class='legend-dot' style='background:{COLORS["uniao_industria"]}'></span> Uniao Industria<br>
            <span class='legend-dot' style='background:{COLORS["br040"]}'></span> BR-040<br>
            <span class='legend-dot' style='background:{COLORS["viaduto_estudo"]}'></span> Estudo de viaduto<br>
            <span class='legend-dot' style='background:{COLORS["fluxo"]}'></span> Fluxo O-D
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown(
        f"<div class='disclaimer'>⚠️ {DISCLAIMER}</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# ABAS
# ---------------------------------------------------------------------------
tabs = st.tabs(
    [
        "🗺️ Mapa",
        "📥 Importar Arquivos",
        "📍 Pontos / Edicao",
        "🔢 Matriz O-D",
        "🛠️ Cenarios",
        "📊 Comparacao",
        "📑 Relatorio",
    ]
)


# ===========================================================================
# ABA 1 - MAPA
# ===========================================================================
def build_main_map() -> folium.Map:
    m = map_utils.create_base_map()

    layers = st.session_state.layers
    show = st.session_state.show_layers

    if show.get("area_estudo"):
        map_utils.add_area_estudo(m, layers.get("area_estudo"))
    if show.get("zonas"):
        map_utils.add_zonas(m, layers.get("zonas"))
    if show.get("ferrovia"):
        map_utils.add_ferrovia(m, layers.get("ferrovia"))
    if show.get("rodovias"):
        map_utils.add_rodovias(m, layers.get("rodovias"))
    if show.get("pontos_viaduto"):
        map_utils.add_pontos_viaduto(m, layers.get("pontos_viaduto"))
    if show.get("pontos_interesse"):
        map_utils.add_pontos_interesse(m, layers.get("pontos_interesse"))

    # Pontos cadastrados na sessao
    if show.get("user_points") and not st.session_state.user_points.empty:
        up_gdf = gpd.GeoDataFrame(
            st.session_state.user_points,
            geometry=[Point(xy) for xy in zip(
                st.session_state.user_points["longitude"],
                st.session_state.user_points["latitude"],
            )],
            crs="EPSG:4326",
        )
        map_utils.add_pontos_interesse(m, up_gdf)

    # Camadas importadas
    if show.get("uploaded"):
        for name, gdf in st.session_state.uploaded_layers.items():
            map_utils.add_custom_layer(m, gdf, f"[Upload] {name}", color="#1565C0")

    # Linhas de fluxo
    if show.get("flow") and st.session_state.flow_records:
        map_utils.add_flow_lines(m, st.session_state.flow_records)

    map_utils.add_draw_control(m)
    map_utils.add_layer_control(m)
    return m


with tabs[0]:
    st.subheader("🗺️ Mapa Interativo")
    col1, col2 = st.columns([3, 1])
    with col1:
        fmap = build_main_map()
        map_state = st_folium(fmap, height=620, use_container_width=True, returned_objects=["last_clicked"])
    with col2:
        st.markdown("##### Indicadores rapidos")
        layers = st.session_state.layers

        n_zonas = 0 if layers.get("zonas") is None else len(layers["zonas"])
        n_viaduto = 0 if layers.get("pontos_viaduto") is None else len(layers["pontos_viaduto"])
        n_poi = 0 if layers.get("pontos_interesse") is None else len(layers["pontos_interesse"])
        n_user = len(st.session_state.user_points)

        for title, value in [
            ("Zonas analiticas", n_zonas),
            ("Pontos de viaduto", n_viaduto),
            ("POIs base", n_poi),
            ("Pontos na sessao", n_user),
            ("Cenarios", len(st.session_state.scenarios)),
            ("Camadas importadas", len(st.session_state.uploaded_layers)),
        ]:
            st.markdown(
                f"<div class='kpi-card'><div class='kpi-title'>{title}</div>"
                f"<div class='kpi-value'>{value}</div></div>",
                unsafe_allow_html=True,
            )

        if map_state and map_state.get("last_clicked"):
            click = map_state["last_clicked"]
            st.info(f"Ultimo clique: lat **{click['lat']:.5f}**, lon **{click['lng']:.5f}**\n\n"
                    f"Copie para adicionar um ponto na aba *Pontos / Edicao*.")


# ===========================================================================
# ABA 2 - IMPORTAR
# ===========================================================================
with tabs[1]:
    st.subheader("📥 Importar arquivos geograficos")
    st.markdown(
        "Formatos suportados: **GeoJSON**, **KML**, **KMZ**, **CSV** com colunas "
        "`nome, tipo, latitude, longitude, descricao`."
    )

    files = st.file_uploader(
        "Arraste ou selecione um ou mais arquivos",
        type=["geojson", "json", "kml", "kmz", "csv"],
        accept_multiple_files=True,
        key="uploader",
    )
    if files:
        for f in files:
            try:
                gdf = data_loader.load_uploaded_file(f)
                st.session_state.uploaded_layers[f.name] = gdf
                st.success(f"✅ {f.name} carregado ({len(gdf)} feicoes)")
            except Exception as exc:
                st.error(f"❌ Falha ao ler {f.name}: {exc}")

    st.divider()

    if st.session_state.uploaded_layers:
        st.markdown("##### Camadas carregadas nesta sessao")
        for name, gdf in list(st.session_state.uploaded_layers.items()):
            with st.expander(f"📂 {name}  -  {len(gdf)} feicoes"):
                non_geom = [c for c in gdf.columns if c != "geometry"]
                if non_geom:
                    st.dataframe(gdf[non_geom].head(50), use_container_width=True)
                col_a, col_b = st.columns([1, 4])
                with col_a:
                    if st.button(f"Remover", key=f"rm_{name}"):
                        del st.session_state.uploaded_layers[name]
                        st.rerun()
    else:
        st.info("Nenhum arquivo carregado. Voce pode usar arquivos KMZ/KML do seu trabalho real "
                "para substituir os dados de exemplo.")


# ===========================================================================
# ABA 3 - PONTOS / EDICAO
# ===========================================================================
with tabs[2]:
    st.subheader("📍 Cadastro de pontos de interesse")
    st.caption("Pontos cadastrados aqui ficam disponiveis durante a sessao e aparecem no mapa.")

    with st.form("form_ponto", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 2, 2])
        with col1:
            nome = st.text_input("Nome do ponto", "")
            categoria = st.selectbox("Categoria", POINT_CATEGORIES, index=0)
        with col2:
            lat = st.number_input("Latitude", value=MATIAS_BARBOSA_CENTER[0], format="%.6f")
            lon = st.number_input("Longitude", value=MATIAS_BARBOSA_CENTER[1], format="%.6f")
        with col3:
            descricao = st.text_area("Descricao", "", height=110)

        submitted = st.form_submit_button("➕ Adicionar ponto", use_container_width=True)
        if submitted:
            if not nome.strip():
                st.warning("Informe um nome para o ponto.")
            else:
                new_row = pd.DataFrame([{
                    "nome": nome, "categoria": categoria,
                    "latitude": lat, "longitude": lon,
                    "descricao": descricao,
                }])
                st.session_state.user_points = pd.concat(
                    [st.session_state.user_points, new_row], ignore_index=True
                )
                st.success(f"Ponto '{nome}' adicionado.")

    st.markdown("##### Pontos cadastrados na sessao")
    if st.session_state.user_points.empty:
        st.info("Nenhum ponto cadastrado ainda.")
    else:
        edited = st.data_editor(
            st.session_state.user_points,
            num_rows="dynamic",
            use_container_width=True,
            key="user_points_editor",
        )
        if not edited.equals(st.session_state.user_points):
            st.session_state.user_points = edited

        csv = st.session_state.user_points.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Baixar pontos como CSV",
            data=csv,
            file_name=f"pontos_sessao_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )


# ===========================================================================
# ABA 4 - MATRIZ O-D
# ===========================================================================
with tabs[3]:
    st.subheader("🔢 Matriz Origem-Destino simplificada (modelo gravitacional)")
    st.markdown(
        "Edite os pesos de **geracao** e **atracao** de cada zona. "
        "A matriz e calculada por $T_{ij} = (G_i \\cdot A_j) / d_{ij}^{\\beta}$, "
        "onde $d_{ij}$ e a distancia (haversine, km) entre os centroides das zonas."
    )

    col_a, col_b = st.columns([3, 1])
    with col_b:
        beta = st.slider("β (atrito da distancia)", 0.5, 4.0, 2.0, 0.1)
        normalize = st.checkbox("Normalizar matriz (%)", value=True)
        recalc = st.button("🔁 Recalcular matriz O-D", use_container_width=True)

    with col_a:
        st.markdown("##### Tabela de zonas (editavel)")
        zonas_edit = st.data_editor(
            st.session_state.zonas_df,
            num_rows="dynamic",
            use_container_width=True,
            key="zonas_editor",
        )
        st.session_state.zonas_df = zonas_edit

    if recalc or st.session_state.od_result is None:
        try:
            zonas_gdf = st.session_state.layers.get("zonas")
            distancias = od_matrix.build_distance_matrix(zonas_gdf)
            od = od_matrix.gravity_od(
                st.session_state.zonas_df, distancias, beta=beta, normalize=normalize
            )
            st.session_state.od_result = od
            st.session_state.od_summary = od_matrix.od_summary(od)
            st.session_state.flow_records = od_matrix.od_flow_records(od, zonas_gdf, threshold=0.5)
        except Exception as exc:
            st.error(f"Erro ao calcular matriz: {exc}")

    if st.session_state.od_result is not None:
        st.markdown("##### Matriz O-D")
        st.dataframe(
            st.session_state.od_result.style.background_gradient(cmap="PuRd", axis=None),
            use_container_width=True,
        )

        st.markdown("##### Viagens por zona")
        st.dataframe(st.session_state.od_summary, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig_g = px.bar(
                st.session_state.od_summary.reset_index().rename(columns={"index": "zona"}),
                x="zona", y="viagens_geradas",
                title="Viagens geradas por zona",
                color="zona",
                color_discrete_map={k: v for k, v in COLORS.items() if k.startswith("Z")},
            )
            st.plotly_chart(fig_g, use_container_width=True)
        with col2:
            fig_a = px.bar(
                st.session_state.od_summary.reset_index().rename(columns={"index": "zona"}),
                x="zona", y="viagens_atraidas",
                title="Viagens atraidas por zona",
                color="zona",
                color_discrete_map={k: v for k, v in COLORS.items() if k.startswith("Z")},
            )
            st.plotly_chart(fig_a, use_container_width=True)

        st.info("Ative a camada **'Linhas de fluxo O-D'** na barra lateral para visualizar "
                "no mapa as linhas com espessura proporcional ao fluxo.")


# ===========================================================================
# ABA 5 - CENARIOS
# ===========================================================================
def get_or_build_base_graph():
    if st.session_state.base_graph is None:
        st.session_state.base_graph = net.build_synthetic_graph(
            st.session_state.layers.get("zonas"),
            st.session_state.layers.get("pontos_viaduto"),
        )
    return st.session_state.base_graph


with tabs[4]:
    st.subheader("🛠️ Simulacao de cenarios de intervencao")
    st.caption(
        "Crie cenarios com novas ligacoes viarias, viadutos, pontes ou bloqueios. "
        "As intervencoes alteram arestas do grafo analitico (centroides de zona + pontos de viaduto)."
    )

    G = get_or_build_base_graph()
    node_options = [n for n in G.nodes]

    if not node_options:
        st.warning("Nenhum no disponivel. Verifique se as zonas estao carregadas.")
    else:
        with st.form("form_cenario", clear_on_submit=False):
            st.markdown("##### Novo cenario")
            col1, col2 = st.columns([2, 2])
            with col1:
                cen_nome = st.text_input("Nome do cenario", value="Cenario com viaduto V2")
                cen_tipo = st.selectbox("Tipo de intervencao", scen.SCENARIO_TYPES, index=1)
                cen_desc = st.text_area("Descricao", value="Implantacao de viaduto sobre a ferrovia ligando Z1 e Z3", height=80)
            with col2:
                from_node = st.selectbox("No A (origem)", node_options, index=0, format_func=lambda n: f"{n} | {G.nodes[n].get('nome','')}")
                to_node = st.selectbox("No B (destino)", node_options, index=min(1, len(node_options) - 1), format_func=lambda n: f"{n} | {G.nodes[n].get('nome','')}")
                factor = st.slider(
                    "Fator de impedancia (1.0 = igual, <1 reduz custo, >1 = restricao)",
                    0.1, 2.0, 0.5, 0.05,
                )
                is_block = st.checkbox("Tratar como bloqueio (remove a aresta)", value=False)

            add_scen = st.form_submit_button("➕ Adicionar cenario", use_container_width=True)
            if add_scen:
                if from_node == to_node:
                    st.warning("Selecione nos diferentes.")
                else:
                    s = scen.Scenario(
                        nome=cen_nome, tipo=cen_tipo, descricao=cen_desc,
                    )
                    if is_block:
                        s.bloqueios.append({"from": from_node, "to": to_node})
                    else:
                        s.intervencoes.append({"from": from_node, "to": to_node, "factor": factor, "tipo": cen_tipo})
                    st.session_state.scenarios.append(s)
                    st.success(f"Cenario '{cen_nome}' adicionado.")

        st.markdown("##### Cenarios cadastrados")
        if st.session_state.scenarios:
            df_scen = pd.DataFrame([{
                "nome": s.nome,
                "tipo": s.tipo,
                "descricao": s.descricao,
                "intervencoes": len(s.intervencoes),
                "bloqueios": len(s.bloqueios),
            } for s in st.session_state.scenarios])
            st.dataframe(df_scen, use_container_width=True)

            idx_to_remove = st.selectbox(
                "Remover cenario (selecione)",
                options=list(range(len(st.session_state.scenarios))),
                format_func=lambda i: f"{i} - {st.session_state.scenarios[i].nome}",
                index=0,
            )
            if st.button("🗑️ Remover cenario selecionado"):
                if st.session_state.scenarios[idx_to_remove].nome == "Cenario Atual":
                    st.warning("Nao remova o 'Cenario Atual' - ele e referencia.")
                else:
                    del st.session_state.scenarios[idx_to_remove]
                    st.rerun()


# ===========================================================================
# ABA 6 - COMPARACAO
# ===========================================================================
with tabs[5]:
    st.subheader("📊 Comparacao de cenarios")

    G = get_or_build_base_graph()
    if not st.session_state.scenarios:
        st.info("Cadastre cenarios na aba **Cenarios**.")
    else:
        try:
            df_compare = scen.compare_scenarios(st.session_state.scenarios, G)
            st.session_state.compare_df = df_compare
        except Exception as exc:
            st.error(f"Erro ao comparar cenarios: {exc}")
            df_compare = pd.DataFrame()

        if not df_compare.empty:
            st.markdown("##### Tabela comparativa")
            st.dataframe(df_compare, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a:
                fig = px.bar(
                    df_compare, x="cenario", y="distancia_media_km",
                    title="Distancia media entre zonas (km)", color="cenario",
                )
                st.plotly_chart(fig, use_container_width=True)
            with col_b:
                fig = px.bar(
                    df_compare, x="cenario", y="reducao_percurso_pct",
                    title="Reducao percentual de percurso (%) - vs Cenario Atual",
                    color="cenario",
                )
                st.plotly_chart(fig, use_container_width=True)

            best = scen.best_scenario(df_compare)
            if best is not None:
                st.markdown("##### 🏆 Interpretacao automatica")
                st.success(
                    f"**Cenario mais vantajoso:** {best['cenario']}  \n"
                    f"**Tipo:** {best['tipo']}  \n"
                    f"**{best['observacao']}**"
                )


# ===========================================================================
# ABA 7 - RELATORIO
# ===========================================================================
with tabs[6]:
    st.subheader("📑 Relatorio do estudo")
    st.caption("Resumo automatico com area de estudo, zonas, pontos, matriz O-D e comparacao de cenarios.")

    G = get_or_build_base_graph()
    # garante calculos atualizados
    try:
        zonas_gdf = st.session_state.layers.get("zonas")
        distancias = od_matrix.build_distance_matrix(zonas_gdf)
        od = od_matrix.gravity_od(st.session_state.zonas_df, distancias, beta=2.0, normalize=True)
        od_sum = od_matrix.od_summary(od)
    except Exception:
        od = st.session_state.od_result
        od_sum = st.session_state.od_summary

    try:
        df_compare = scen.compare_scenarios(st.session_state.scenarios, G)
    except Exception:
        df_compare = pd.DataFrame()

    best = scen.best_scenario(df_compare) if not df_compare.empty else None

    md = report_generator.build_markdown_report(
        area_nome=st.session_state.municipio_nome,
        zonas_df=st.session_state.zonas_df,
        pontos_df=st.session_state.user_points,
        od_matrix=od if od is not None else pd.DataFrame(),
        od_summary_df=od_sum if od_sum is not None else pd.DataFrame(),
        scenarios_compare=df_compare,
        best_scenario_row=best,
    )

    st.markdown(md, unsafe_allow_html=False)

    st.divider()
    st.markdown("##### ⬇️ Download do relatorio")

    col1, col2, col3 = st.columns(3)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    with col1:
        st.download_button(
            "Baixar .md",
            data=md.encode("utf-8"),
            file_name=f"relatorio_{stamp}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "Baixar .txt",
            data=md.encode("utf-8"),
            file_name=f"relatorio_{stamp}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col3:
        html = report_generator.build_html_report(md)
        st.download_button(
            "Baixar .html",
            data=html.encode("utf-8"),
            file_name=f"relatorio_{stamp}.html",
            mime="text/html",
            use_container_width=True,
        )


# ---------------------------------------------------------------------------
# RODAPE
# ---------------------------------------------------------------------------
st.divider()
st.markdown(
    f"""
    <div style='text-align:center; color:#777; font-size:0.85rem;'>
        Disciplina de Planejamento de Transportes - IME &middot;
        Prototipo academico &middot; {datetime.now().year}
    </div>
    """,
    unsafe_allow_html=True,
)
