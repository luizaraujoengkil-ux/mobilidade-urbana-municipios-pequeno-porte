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
    advanced_assignment,
    data_loader,
    drawing as drawing_utils,
    geocode,
    map_utils,
    metadata_manager,
    network_analysis as net,
    od_matrix,
    osm_pois,
    population_loader,
    rail_params,
    report_generator,
    scenario_analysis as scen,
    traffic_assignment,
    validation,
)
from modules.config import (
    CATEGORY_STYLE,
    COLORS,
    DEFAULT_ZOOM,
    DISCLAIMER,
    EIXO_IMPACTOS,
    EIXO_TYPES,
    INFRA_CATEGORIES,
    MATIAS_BARBOSA_CENTER,
    POINT_CATEGORIES,
    POI_IMPORTANCIA,
    VIA_FUNCOES,
    VIA_TYPES,
    ZONA_COLOR_BY_TIPO,
    ZONA_FUNCAO_OD,
    ZONA_TIPOS,
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
        .disclaimer {background: #FFF8E1; color: #5D4037; border-left: 4px solid #F9A825; padding: 10px 14px; border-radius: 6px; font-size: 0.85rem; line-height: 1.45;}
        .disclaimer * {color: #5D4037 !important;}
        /* === Estilo destacado das abas principais (compacto - cabe 10 abas) === */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            background: linear-gradient(135deg, rgba(74,20,140,0.08) 0%, rgba(184,61,186,0.06) 100%);
            padding: 4px 4px 0 4px;
            border-radius: 8px 8px 0 0;
            border-bottom: 2px solid #B83DBA;
            flex-wrap: nowrap;
        }
        .stTabs [data-baseweb="tab"] {
            font-weight: 600 !important;
            font-size: 0.82rem !important;
            padding: 7px 10px !important;
            min-height: 38px;
            border-radius: 6px 6px 0 0 !important;
            background: rgba(255,255,255,0.04);
            border: 1px solid transparent;
            color: #999 !important;
            transition: all 0.15s ease-in-out;
            letter-spacing: 0.1px;
            white-space: nowrap;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background: rgba(184,61,186,0.18) !important;
            color: #FFFFFF !important;
            border-color: rgba(184,61,186,0.4);
        }
        .stTabs [data-baseweb="tab"][aria-selected="true"] {
            background: linear-gradient(135deg, #4A148C 0%, #B83DBA 100%) !important;
            color: #FFFFFF !important;
            border-color: #4A148C;
            box-shadow: 0 2px 8px rgba(74,20,140,0.35);
        }
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #FFD740 !important;
            height: 3px !important;
        }
        .stTabs [data-baseweb="tab-panel"] {
            padding-top: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# TELA INICIAL - ESCOLHA DO MODO DE ESTUDO
# ---------------------------------------------------------------------------
def show_welcome_screen() -> None:
    """Pagina de boas-vindas - apresenta a escolha demo vs novo estudo.

    Chamada antes da inicializacao do app quando 'study_mode' ainda nao
    esta definido em session_state.
    """
    from pathlib import Path
    logo_path = Path(__file__).resolve().parent / "assets" / "logo_ime.png"
    has_logo = logo_path.exists()

    # ----- Cabecalho: logo IME + tagline + titulo -----
    st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)
    col_logo, col_text = st.columns([1, 5])
    with col_logo:
        if has_logo:
            st.image(str(logo_path), width=140)
        else:
            st.markdown(
                "<div style='display:flex;align-items:center;justify-content:center;"
                "height:140px;'>"
                "<div style='font-size:3.2rem;color:#4A148C;font-weight:900;"
                "letter-spacing:6px;font-family:Georgia, serif;"
                "border:3px solid #4A148C;border-radius:12px;padding:14px 22px;"
                "background:linear-gradient(135deg,#F3E5F5 0%,#FFFFFF 100%);'>"
                "IME"
                "</div></div>",
                unsafe_allow_html=True,
            )
    with col_text:
        st.markdown(
            """
            <div style="padding-top: 14px;">
              <div style="font-size:0.85rem;color:#9C27B0;letter-spacing:3px;
                          font-weight:700;margin-bottom:4px;">
                  PLANEJAMENTO DE TRANSPORTES &middot; IME
              </div>
              <h1 style="color:#4A148C;margin: 4px 0 0 0;font-size:2.1rem;line-height:1.2;">
                  Simulador de Mobilidade Urbana<br>
                  para Municipios de Pequeno Porte
              </h1>
              <p style="font-size:1.0rem;color:#555;margin-top:8px;max-width:780px;">
                  Ferramenta experimental para analise de areas de estudo,
                  matriz origem-destino simplificada e simulacao de intervencoes
                  viarias (viadutos, pontes, novas ligacoes).
              </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:30px;'></div>", unsafe_allow_html=True)

    # Badge HTML reutilizavel (canto superior direito de cada card)
    badge_html = (
        "<div style='position:absolute;top:14px;right:14px;background:#FFFFFF;"
        "border:1px solid #C8B8E0;padding:5px 10px;border-radius:6px;"
        "font-size:0.65rem;letter-spacing:1.6px;color:#4A148C;font-weight:700;'>"
        "PLANEJAMENTO DE<br>TRANSPORTES · IME"
        "</div>"
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#F3E5F5 0%,#FFFFFF 100%);
                        border-left:5px solid #B83DBA;padding:22px;border-radius:10px;
                        box-shadow:0 1px 4px rgba(0,0,0,0.06);min-height:230px;
                        position:relative;">
                {badge_html}
                <h3 style="color:#4A148C;margin-top:0;padding-right:140px;">
                    🎓 Abrir demonstracao
                </h3>
                <p><b>Matias Barbosa / MG</b></p>
                <p style="font-size:0.85rem;color:#777;font-style:italic;margin-top:-6px;">
                    Caso da disciplina de Planejamento de Transportes
                </p>
                <p style="font-size:0.9rem;color:#555;">
                    Estudo de caso pre-carregado com zonas Z1-Z4, linha ferrea, BR-040,
                    MG-353, Uniao Industria e pontos de viaduto. Tudo editavel.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🎓 Abrir demonstracao: Matias Barbosa/MG",
                     use_container_width=True, type="primary", key="btn_mode_demo"):
            st.session_state.study_mode = "demo"
            st.rerun()
    with c2:
        st.markdown(
            f"""
            <div style="background:linear-gradient(135deg,#E8F5E9 0%,#FFFFFF 100%);
                        border-left:5px solid #43A047;padding:22px;border-radius:10px;
                        box-shadow:0 1px 4px rgba(0,0,0,0.06);min-height:230px;
                        position:relative;">
                {badge_html}
                <h3 style="color:#1B5E20;margin-top:0;padding-right:140px;">
                    🌍 Criar novo estudo
                </h3>
                <p><b>Outro municipio</b></p>
                <p style="font-size:0.85rem;color:#777;font-style:italic;margin-top:-6px;">
                    Aplicavel a qualquer cidade brasileira
                </p>
                <p style="font-size:0.9rem;color:#555;">
                    Assistente passo a passo: municipio, area de estudo, vias, eixos
                    estruturantes, zonas analiticas e pontos de interesse.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("🌍 Criar novo estudo",
                     use_container_width=True, key="btn_mode_new"):
            st.session_state.study_mode = "new"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.info(
        "ℹ️ A escolha aqui apenas determina os dados iniciais. Em ambos os modos voce "
        "pode editar, importar arquivos KMZ/KML/GeoJSON, cadastrar pontos, ajustar "
        "zonas, simular intervencoes e gerar relatorios."
    )

    # ----- Assinatura do desenvolvedor -----
    st.markdown(
        """
        <div style="margin-top: 40px; padding: 22px; text-align: center;
                    background: linear-gradient(135deg, rgba(74,20,140,0.04) 0%,
                                                       rgba(184,61,186,0.06) 100%);
                    border-radius: 12px; border: 1px solid rgba(184,61,186,0.15);">
            <div style="font-size:0.75rem;color:#9C27B0;letter-spacing:2px;
                        font-weight:700;margin-bottom:6px;">
                DESENVOLVIDO POR
            </div>
            <div style="font-size:1.15rem;color:#4A148C;font-weight:600;">
                Luiz Araujo de Souza Junior
            </div>
            <div style="font-size:0.9rem;color:#666;margin-top:4px;">
                Instituto Militar de Engenharia (IME) &middot;
                <a href="mailto:luiz.junior@ime.eb.br"
                   style="color:#9C27B0;text-decoration:none;font-weight:500;">
                    luiz.junior@ime.eb.br
                </a>
            </div>
            <div style="font-size:0.75rem;color:#888;margin-top:8px;font-style:italic;">
                Disciplina de Planejamento de Transportes
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Gate: se ainda nao escolheu, mostra a tela inicial e para
if "study_mode" not in st.session_state:
    show_welcome_screen()
    st.stop()


# ---------------------------------------------------------------------------
# ESTADO DA SESSAO
# ---------------------------------------------------------------------------
def _empty_layers() -> dict:
    """Camadas vazias - usado no modo 'Criar novo estudo'."""
    empty_pt = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
    return {
        "area_estudo": empty_pt.copy(),
        "zonas": empty_pt.copy(),
        "ferrovia": empty_pt.copy(),
        "rodovias": empty_pt.copy(),
        "pontos_viaduto": empty_pt.copy(),
        "pontos_interesse": empty_pt.copy(),
    }


def init_session_state() -> None:
    if "initialized" in st.session_state:
        return

    mode = st.session_state.get("study_mode", "demo")
    if mode == "demo":
        layers = data_loader.load_sample_layers()
    else:
        layers = _empty_layers()

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

    # Dados do municipio (preenchidos no Assistente)
    if mode == "demo":
        st.session_state.municipio_info = {
            "nome": "Matias Barbosa", "uf": "MG",
            "center_lat": MATIAS_BARBOSA_CENTER[0],
            "center_lon": MATIAS_BARBOSA_CENTER[1],
        }
    else:
        st.session_state.municipio_info = {
            "nome": "", "uf": "",
            "center_lat": MATIAS_BARBOSA_CENTER[0],
            "center_lon": MATIAS_BARBOSA_CENTER[1],
        }

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
        "osm": True,
    }

    # Malha viaria do OSM (carregada sob demanda)
    st.session_state.osm_graph = None
    st.session_state.osm_edges = None

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
                &mdash; Estudo de caso de demonstracao: <b>Matias Barbosa / MG</b>
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.expander("ℹ️ **Como usar este simulador** (clique para abrir)", expanded=True):
    st.markdown(
        """
        Este e um **prototipo academico** para apoiar a analise de mobilidade urbana
        em municipios de pequeno porte. Ele ja vem carregado com o estudo de caso de
        **Matias Barbosa/MG** para fins de demonstracao, mas pode ser usado para
        **qualquer outra cidade**.

        ### 🎯 Para usar com OUTRA cidade:
        1. **Painel lateral** → mude o **Modo de estudo** para *"Outro municipio"*.
        2. Digite o **nome do municipio** e ajuste **latitude / longitude / zoom** do centro do mapa.
        3. Aba **📥 Importar Arquivos** → envie KMZ, KML, GeoJSON ou CSV da nova cidade.
        4. Aba **🔢 Matriz O-D** → atualize os pesos de geracao e atracao das novas zonas.

        ### 📖 Roteiro de analise (recomendado):
        1. **🗺️ Mapa** &mdash; visualize a area de estudo, zonas e infraestruturas existentes.
        2. **🛣️ Malha viaria real (OSM)** &mdash; *na sidebar*, clique em **"Baixar / atualizar"** para
           trazer as ruas reais do OpenStreetMap. **Isso e essencial** para que os cenarios de
           viaduto / ponte / passagem de nivel calculem distancias atraves das ruas reais.
        3. **📥 Importar Arquivos** &mdash; carregue seus dados reais (opcional).
        4. **📍 Pontos / Edicao** &mdash; cadastre travessias criticas, pontes/viadutos propostos, escolas etc.
        5. **🔢 Matriz O-D** &mdash; ajuste pesos de viagens (geracao / atracao) por zona e veja o fluxo estimado.
        6. **🛠️ Cenarios** &mdash; crie alternativas ("e se construirmos um viaduto aqui?")
           &mdash; as intervencoes sao adicionadas como novas arestas sobre a malha viaria real.
        7. **📊 Comparacao** &mdash; veja o impacto de cada cenario em relacao ao atual.
        8. **📑 Relatorio** &mdash; baixe o resumo em `.md`, `.txt` ou `.html`.

        ### 💡 Dicas rapidas:
        - **Clique no mapa** para ver as coordenadas (uteis para cadastrar pontos).
        - Use a **regua** (canto superior esquerdo do mapa) para medir distancias.
        - Os pontos cadastrados ficam apenas na sua sessao &mdash; exporte como CSV antes de fechar.
        - Use as **caixas de selecao da sidebar** para ligar/desligar cada camada do mapa.
        """
    )

st.divider()


# ---------------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Painel de Controle")

    mode_label = "🎓 Demonstracao" if st.session_state.study_mode == "demo" else "🌍 Novo estudo"
    st.caption(f"Modo atual: **{mode_label}**")
    col_btns_a, col_btns_b = st.columns(2)
    with col_btns_a:
        if st.button("🔄 Tela inicial", use_container_width=True,
                     help="Volta a tela de escolha e limpa todo o estado",
                     key="btn_reset_app"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
    with col_btns_b:
        if st.button("📂 Recarregar KMZs", use_container_width=True,
                     help="Releia a pasta data/demo_matias_barbosa/ - "
                          "use depois de adicionar/editar KMZs",
                     key="btn_reload_kmz"):
            # Recarrega camadas demo sem perder cenarios/pontos do usuario
            new_layers = data_loader.load_sample_layers()
            st.session_state.layers = new_layers
            st.session_state.zonas_df = od_matrix.default_zonas_dataframe(new_layers.get("zonas"))
            st.session_state.base_graph = None  # forca rebuild do grafo
            st.session_state._kmz_signature = data_loader.kmz_folder_signature()
            n_layers = sum(
                1 for v in new_layers.values()
                if v is not None and hasattr(v, "empty") and not v.empty
            )
            st.success(f"✅ {n_layers}/{len(new_layers)} camadas recarregadas da pasta.")
            st.rerun()

    # ----- Deteccao AUTOMATICA de mudancas em KMZs da pasta -----
    # Comparamos a 'assinatura' atual da pasta (nome+mtime) com a guardada.
    # Se mudou, recarrega silenciosamente sem o usuario precisar clicar.
    _cur_sig = data_loader.kmz_folder_signature()
    if st.session_state.get("_kmz_signature") != _cur_sig:
        # Primeira vez OU pasta mudou: recarrega
        if "_kmz_signature" in st.session_state:
            # nao e a primeira vez: deve avisar o usuario
            new_layers = data_loader.load_sample_layers()
            st.session_state.layers = new_layers
            st.session_state.zonas_df = od_matrix.default_zonas_dataframe(new_layers.get("zonas"))
            st.session_state.base_graph = None
            st.toast("📂 Detectei mudancas na pasta de KMZs - camadas recarregadas.", icon="✅")
        st.session_state._kmz_signature = _cur_sig

    st.subheader("🎯 Modo de estudo")
    modo = st.radio(
        "Selecione o modo:",
        ["🎓 Demonstracao - Matias Barbosa/MG", "🌍 Estudar outro municipio"],
        index=0,
        key="modo_estudo",
        help="Use 'Demonstracao' para ver o estudo de caso completo de Matias Barbosa. "
             "Use 'Outro municipio' para configurar uma nova area de estudo.",
    )
    is_demo = modo.startswith("🎓")

    st.subheader("📍 Area de estudo")
    if is_demo:
        st.text_input(
            "Nome do municipio",
            value="Matias Barbosa - MG",
            key="municipio_nome",
        )
        st.session_state.map_center = MATIAS_BARBOSA_CENTER
        st.session_state.map_zoom = DEFAULT_ZOOM
        st.success("📚 Modo demonstracao ativo. Os dados de Matias Barbosa/MG estao carregados.")
    else:
        st.text_input(
            "Nome do municipio",
            value=st.session_state.get("municipio_nome_custom", ""),
            placeholder="Ex: Cataguases - MG",
            key="municipio_nome",
        )
        col_lat, col_lon = st.columns(2)
        with col_lat:
            new_lat = st.number_input(
                "Latitude central",
                value=float(st.session_state.get("custom_lat", MATIAS_BARBOSA_CENTER[0])),
                format="%.6f",
                key="custom_lat",
            )
        with col_lon:
            new_lon = st.number_input(
                "Longitude central",
                value=float(st.session_state.get("custom_lon", MATIAS_BARBOSA_CENTER[1])),
                format="%.6f",
                key="custom_lon",
            )
        new_zoom = st.slider(
            "Zoom inicial",
            min_value=10, max_value=18,
            value=int(st.session_state.get("custom_zoom", DEFAULT_ZOOM)),
            key="custom_zoom",
        )
        st.session_state.map_center = (new_lat, new_lon)
        st.session_state.map_zoom = new_zoom

        st.warning(
            "📌 **Proximos passos para sua cidade:**\n\n"
            "1. Va na aba **📥 Importar Arquivos** e envie KMZ / KML / GeoJSON / CSV.\n"
            "2. (Opcional) Desmarque as **camadas de demonstracao** abaixo para nao misturar com Matias Barbosa.\n"
            "3. Atualize as zonas e pesos na aba **🔢 Matriz O-D**."
        )

    st.subheader("🛣️ Malha viaria real (OSM)")
    st.caption(
        "Baixe a malha viaria real do OpenStreetMap centrada na area de estudo. "
        "Ela e a base sobre a qual viadutos, pontes e passagens de nivel sao avaliados."
    )
    osm_radius = st.slider(
        "Raio de download (metros)",
        min_value=500, max_value=5000,
        value=int(st.session_state.get("osm_radius", 1500)),
        step=100,
        key="osm_radius",
        help="Distancia do centro da area de estudo. Raios maiores demoram mais.",
    )
    osm_status = (
        f"✅ Carregada ({st.session_state.osm_graph.number_of_nodes()} nos, "
        f"{st.session_state.osm_graph.number_of_edges()} arestas)"
        if st.session_state.osm_graph is not None
        else "⚪ Nao carregada"
    )
    st.markdown(f"**Status:** {osm_status}")
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("📥 Baixar / atualizar", use_container_width=True, key="btn_osm_load"):
            if not net.OSMNX_AVAILABLE:
                st.error("OSMnx nao esta disponivel neste ambiente.")
            else:
                center = st.session_state.get("map_center", MATIAS_BARBOSA_CENTER)
                with st.spinner("Baixando malha do OpenStreetMap..."):
                    G_osm = net.load_osm_network(center[0], center[1], osm_radius)
                    if G_osm is None:
                        st.error("Falha no download. Verifique conexao ou raio.")
                    else:
                        st.session_state.osm_graph = G_osm
                        edges = net.osm_edges_gdf(G_osm)
                        st.session_state.osm_edges = edges
                        st.session_state.base_graph = None  # forca rebuild do grafo de analise
                        if edges is None or getattr(edges, "empty", True):
                            st.warning(
                                f"Grafo carregado ({G_osm.number_of_nodes()} nos, "
                                f"{G_osm.number_of_edges()} arestas) mas falha ao "
                                f"extrair geometrias para o mapa. Cenarios continuam "
                                f"funcionando, mas a malha nao sera desenhada."
                            )
                        else:
                            st.success(
                                f"Malha carregada: {G_osm.number_of_nodes()} nos, "
                                f"{G_osm.number_of_edges()} arestas ({len(edges)} segmentos desenhaveis)"
                            )
                        st.rerun()
    with col_btn2:
        if st.button("🗑️ Limpar OSM", use_container_width=True, key="btn_osm_clear"):
            st.session_state.osm_graph = None
            st.session_state.osm_edges = None
            st.session_state.base_graph = None
            st.rerun()

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
    show["osm"]             = st.checkbox("Malha viaria (OSM)",    value=show.get("osm", True))
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
            <span class='legend-dot' style='background:#0D47A1'></span> Malha viaria (OSM) - hierarquia em azul<br>
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
# BARRA DE PROGRESSO GLOBAL (etapas validadas)
# ---------------------------------------------------------------------------
with st.expander("📋 **Progresso do estudo** (clique para ver detalhes)", expanded=False):
    validation.render_progress_bar(compact=False)


# ---------------------------------------------------------------------------
# ABAS
# ---------------------------------------------------------------------------
tabs = st.tabs(
    [
        "🧭 Assistente",
        "🗺️ Mapa",
        "📥 Importar Arquivos",
        "📍 Pontos / Edicao",
        "🔢 Matriz O-D",
        "🛠️ Cenarios",
        "📊 Comparacao",
        "📑 Relatorio",
        "🚦 Alocacao Simplificada",
        "🔄 Atualizacao de Dados",
    ]
)


# ===========================================================================
# ABA 0 - ASSISTENTE (fluxo guiado de criacao do estudo)
# ===========================================================================
WIZARD_STEPS = [
    "1. Municipio",
    "2. Area de estudo",
    "3. Via principal",
    "4. Linha ferrea / eixo estruturante",
    "5. Zonas analiticas",
    "6. Pontos de interesse",
]


def _wizard_mini_map(geom_type: str, height: int = 380) -> dict:
    """Constroi um mini-mapa para desenho dentro de uma etapa do assistente.

    geom_type: 'polygon' ou 'polyline' ou 'marker'.
    Retorna o state dict de st_folium (com 'all_drawings' para extracao).
    """
    center = st.session_state.get("map_center", MATIAS_BARBOSA_CENTER)
    zoom = st.session_state.get("map_zoom", DEFAULT_ZOOM)
    m = map_utils.create_base_map(center=center, zoom=zoom,
                                   label=st.session_state.get("municipio_nome", "Area"))
    # mostra camadas ja salvas como referencia
    layers = st.session_state.layers
    if not layers.get("area_estudo", gpd.GeoDataFrame()).empty:
        map_utils.add_area_estudo(m, layers["area_estudo"])
    if not layers.get("zonas", gpd.GeoDataFrame()).empty:
        map_utils.add_zonas(m, layers["zonas"])
    if not layers.get("rodovias", gpd.GeoDataFrame()).empty:
        map_utils.add_rodovias(m, layers["rodovias"])
    if not layers.get("ferrovia", gpd.GeoDataFrame()).empty:
        map_utils.add_ferrovia(m, layers["ferrovia"])
    if st.session_state.osm_edges is not None:
        map_utils.add_osm_network(m, st.session_state.osm_edges)

    from folium.plugins import Draw
    draw_options = {
        "polyline":     geom_type == "polyline",
        "polygon":      geom_type == "polygon",
        "circle":       False,
        "rectangle":    False,
        "marker":       geom_type == "marker",
        "circlemarker": False,
    }
    Draw(
        export=False, position="topleft",
        draw_options=draw_options,
        edit_options={"edit": True, "remove": True},
    ).add_to(m)
    map_utils.add_layer_control(m)
    return st_folium(m, height=height, use_container_width=True,
                     returned_objects=["all_drawings"])


def _step_municipio() -> None:
    info = st.session_state.municipio_info
    st.markdown("### 1️⃣ Municipio")
    st.caption("Informe o municipio em estudo. Use o botao 'Localizar no mapa' para centralizar.")
    col1, col2, col3 = st.columns([3, 1, 2])
    with col1:
        new_nome = st.text_input("Nome do municipio", value=info.get("nome", ""), key="wiz_nome")
    with col2:
        new_uf = st.text_input("UF", value=info.get("uf", ""), max_chars=2, key="wiz_uf")
    with col3:
        if st.button("📍 Localizar no mapa (geocodificar)", use_container_width=True, key="wiz_geocode"):
            with st.spinner("Buscando coordenadas..."):
                coords = geocode.geocode_municipio(new_nome, new_uf)
            if coords is None:
                st.error("Nao foi possivel localizar o municipio. Tente revisar nome/UF.")
            else:
                info["nome"], info["uf"] = new_nome, new_uf
                info["center_lat"], info["center_lon"] = coords
                info["display"] = f"{new_nome} - {new_uf}" if new_uf else new_nome
                st.session_state.map_center = coords
                st.success(
                    f"✅ Localizado em lat={coords[0]:.5f}, lon={coords[1]:.5f}. "
                    "Va na **sidebar** e atualize o campo 'Nome do municipio' para refletir aqui se desejar."
                )
                st.rerun()
    # sincroniza nome editado no formulario (so no dict, sem tocar nas chaves de widgets)
    if new_nome != info.get("nome") or new_uf != info.get("uf"):
        info["nome"], info["uf"] = new_nome, new_uf
        info["display"] = f"{new_nome} - {new_uf}" if new_uf else new_nome

    st.markdown("**Resumo atual:**")
    st.json({
        "municipio": info.get("nome", ""),
        "UF": info.get("uf", ""),
        "centro do mapa": [info.get("center_lat"), info.get("center_lon")],
    })


def _step_area_estudo() -> None:
    st.markdown("### 2️⃣ Delimitacao da Area de Estudo")
    st.caption(
        "Desenhe o poligono da area de estudo no mapa abaixo (ferramenta de poligono "
        "no canto superior esquerdo do mapa) **ou** importe um arquivo na aba 📥 Importar."
    )
    state = _wizard_mini_map("polygon")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Salvar area desenhada", use_container_width=True, key="save_area"):
            drawn = drawing_utils.extract_drawings(state, allowed_types={"Polygon", "MultiPolygon"})
            if drawn.empty:
                st.warning("Nenhum poligono detectado. Desenhe primeiro no mapa.")
            else:
                drawn["nome"] = "Area de Estudo"
                drawn["descricao"] = "Area delimitada para analise de mobilidade"
                st.session_state.layers["area_estudo"] = drawn
                st.success(f"✅ Area salva ({len(drawn)} poligono(s)).")
                st.rerun()
    with col2:
        if st.button("🗑️ Limpar area", use_container_width=True, key="clear_area"):
            st.session_state.layers["area_estudo"] = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
            st.rerun()

    cur = st.session_state.layers.get("area_estudo")
    if cur is not None and not cur.empty:
        st.success(f"📐 Area de estudo cadastrada com {len(cur)} feicao(oes).")
    else:
        st.info("Nenhuma area de estudo definida ainda.")


def _step_via_principal() -> None:
    st.markdown("### 3️⃣ Definicao da Via Principal")
    st.caption("Desenhe a polilinha da via principal e classifique-a abaixo.")
    state = _wizard_mini_map("polyline")

    with st.form("form_via", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            via_nome = st.text_input("Nome da via", value="", key="via_nome")
            via_tipo = st.selectbox("Tipo", VIA_TYPES, key="via_tipo")
        with col2:
            via_funcao = st.selectbox("Funcao predominante", VIA_FUNCOES, key="via_funcao")
            via_obs = st.text_input("Observacoes", value="", key="via_obs")
        submit_via = st.form_submit_button("➕ Adicionar via desenhada", use_container_width=True)

    if submit_via:
        drawn = drawing_utils.extract_drawings(state, allowed_types={"LineString", "MultiLineString"})
        if drawn.empty:
            st.warning("Nenhuma linha detectada. Desenhe primeiro no mapa.")
        else:
            drawn["nome"] = via_nome or "Via principal"
            drawn["tipo"] = via_tipo
            drawn["categoria"] = via_tipo.lower().replace(" ", "_")
            drawn["funcao"] = via_funcao
            drawn["observacoes"] = via_obs
            cur = st.session_state.layers.get("rodovias")
            if cur is None or cur.empty:
                st.session_state.layers["rodovias"] = drawn
            else:
                st.session_state.layers["rodovias"] = gpd.GeoDataFrame(
                    pd.concat([cur, drawn], ignore_index=True), crs="EPSG:4326"
                )
            st.success(f"✅ Via '{via_nome or 'Via principal'}' adicionada.")
            st.rerun()

    cur = st.session_state.layers.get("rodovias")
    if cur is not None and not cur.empty:
        cols_show = [c for c in ["nome", "tipo", "funcao", "observacoes"] if c in cur.columns]
        st.markdown("**Vias cadastradas:**")
        st.dataframe(cur[cols_show] if cols_show else cur.drop(columns=["geometry"], errors="ignore"),
                     use_container_width=True)
        if st.button("🗑️ Apagar todas as vias", key="clear_vias"):
            st.session_state.layers["rodovias"] = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
            st.rerun()


def _step_eixo_estruturante() -> None:
    st.markdown("### 4️⃣ Linha Ferrea ou Eixo Estruturante")
    st.caption(
        "Desenhe a polilinha que representa o eixo estruturante "
        "(ferrovia, rodovia urbana, BRT, rio/canal, etc.) e classifique-o."
    )
    state = _wizard_mini_map("polyline")

    with st.form("form_eixo", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            eixo_nome = st.text_input("Nome do eixo", value="", key="eixo_nome")
            eixo_tipo = st.selectbox("Tipo", EIXO_TYPES, key="eixo_tipo")
        with col2:
            eixo_imp = st.selectbox("Impacto predominante", EIXO_IMPACTOS, key="eixo_imp")
            eixo_obs = st.text_input("Observacoes", value="", key="eixo_obs")
        submit_eixo = st.form_submit_button("➕ Adicionar eixo desenhado", use_container_width=True)

    if submit_eixo:
        drawn = drawing_utils.extract_drawings(state, allowed_types={"LineString", "MultiLineString"})
        if drawn.empty:
            st.warning("Nenhuma linha detectada.")
        else:
            drawn["nome"] = eixo_nome or "Eixo estruturante"
            drawn["tipo"] = eixo_tipo
            drawn["impacto"] = eixo_imp
            drawn["observacoes"] = eixo_obs
            cur = st.session_state.layers.get("ferrovia")
            if cur is None or cur.empty:
                st.session_state.layers["ferrovia"] = drawn
            else:
                st.session_state.layers["ferrovia"] = gpd.GeoDataFrame(
                    pd.concat([cur, drawn], ignore_index=True), crs="EPSG:4326"
                )
            st.success(f"✅ Eixo '{eixo_nome or 'Eixo estruturante'}' adicionado.")
            st.rerun()

    cur = st.session_state.layers.get("ferrovia")
    if cur is not None and not cur.empty:
        cols_show = [c for c in ["nome", "tipo", "impacto", "observacoes"] if c in cur.columns]
        st.markdown("**Eixos cadastrados:**")
        st.dataframe(cur[cols_show] if cols_show else cur.drop(columns=["geometry"], errors="ignore"),
                     use_container_width=True)
        if st.button("🗑️ Apagar todos os eixos", key="clear_eixos"):
            st.session_state.layers["ferrovia"] = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
            st.rerun()


def _step_zonas() -> None:
    st.markdown("### 5️⃣ Zonas Analiticas")
    st.caption(
        "Desenhe o poligono da zona, preencha os dados e clique em 'Adicionar zona'. "
        "Codigos sugeridos: Z1, Z2, Z3, Z4..."
    )
    state = _wizard_mini_map("polygon")

    with st.form("form_zona", clear_on_submit=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            z_cod = st.text_input("Codigo (Z1...)", value="Z1", key="z_cod")
            z_nome = st.text_input("Nome", value="", key="z_nome")
        with col2:
            z_tipo = st.selectbox("Tipo predominante", ZONA_TIPOS, key="z_tipo")
            z_funcao = st.selectbox("Funcao na O-D", ZONA_FUNCAO_OD, key="z_funcao")
        with col3:
            z_ger = st.number_input("Peso geracao", 0.0, 1000.0, 50.0, 5.0, key="z_ger")
            z_atr = st.number_input("Peso atracao", 0.0, 1000.0, 50.0, 5.0, key="z_atr")
        col4, col5, col6 = st.columns(3)
        with col4:
            z_pop = st.number_input("Populacao estimada", 0, 1_000_000, 0, 100, key="z_pop")
        with col5:
            z_emp = st.number_input("Empregos/atividades", 0, 1_000_000, 0, 50, key="z_emp")
        with col6:
            z_cor = st.color_picker("Cor", value=ZONA_COLOR_BY_TIPO.get(z_tipo, "#9E9E9E"), key="z_cor")
        z_obs = st.text_input("Observacoes", "", key="z_obs")
        submit_zona = st.form_submit_button("➕ Adicionar zona desenhada", use_container_width=True)

    if submit_zona:
        drawn = drawing_utils.extract_drawings(state, allowed_types={"Polygon", "MultiPolygon"})
        if drawn.empty:
            st.warning("Nenhum poligono detectado.")
        else:
            drawn["zona"] = z_cod
            drawn["nome"] = z_nome or z_cod
            drawn["tipo"] = z_tipo
            drawn["funcao_od"] = z_funcao
            drawn["geracao"] = z_ger
            drawn["atracao"] = z_atr
            drawn["populacao"] = z_pop
            drawn["empregos"] = z_emp
            drawn["cor"] = z_cor
            drawn["observacoes"] = z_obs
            cur = st.session_state.layers.get("zonas")
            if cur is None or cur.empty:
                st.session_state.layers["zonas"] = drawn
            else:
                st.session_state.layers["zonas"] = gpd.GeoDataFrame(
                    pd.concat([cur, drawn], ignore_index=True), crs="EPSG:4326"
                )
            # atualiza tabela de zonas para a matriz O-D
            st.session_state.zonas_df = od_matrix.default_zonas_dataframe(st.session_state.layers["zonas"])
            st.success(f"✅ Zona '{z_cod}' adicionada.")
            st.rerun()

    cur = st.session_state.layers.get("zonas")
    if cur is not None and not cur.empty:
        cols_show = [c for c in ["zona", "nome", "tipo", "geracao", "atracao", "populacao"] if c in cur.columns]
        st.markdown("**Zonas cadastradas:**")
        st.dataframe(cur[cols_show] if cols_show else cur.drop(columns=["geometry"], errors="ignore"),
                     use_container_width=True)
        if st.button("🗑️ Apagar todas as zonas", key="clear_zonas"):
            st.session_state.layers["zonas"] = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")
            st.session_state.zonas_df = od_matrix.default_zonas_dataframe(None)
            st.rerun()


def _step_pois() -> None:
    st.markdown("### 6️⃣ Pontos de Interesse e Pontos Criticos")
    st.caption(
        "Cadastre pontos manualmente OU busque automaticamente no OpenStreetMap "
        "(escolas, hospitais, prefeitura, comercios, industrias, estacoes, paradas, passagens de nivel...)."
    )

    st.success(
        "🎯 **Lembrete do fluxo de analise:**  \n"
        "• O **cenario baseline** (atual, sem intervencao) ja existe automaticamente.  \n"
        "• Pontos cadastrados aqui com categoria **Viaduto proposto, Ponte proposta, "
        "Passagem inferior/superior de nivel, Travessia critica ou Nova ligacao viaria** "
        "se tornam nos selecionaveis na aba 🛠️ **Cenarios**.  \n"
        "• Apos cadastrar, va em 🛠️ Cenarios para simular, depois em 📊 Comparacao e "
        "📑 Relatorio para ver a melhora ou piora **em relacao ao baseline**."
    )

    st.markdown("##### 🔍 Busca automatica no OSM")
    st.info(
        "ℹ️ **Os pontos sugeridos sao obtidos de bases abertas (OpenStreetMap) e podem estar "
        "incompletos ou desatualizados. Recomenda-se validacao local.**"
    )
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown(
            "A busca usa o **poligono da Area de Estudo** definida na etapa 2. "
            "Se a area nao estiver desenhada, defina-a antes."
        )
    with col2:
        if st.button("🔍 Buscar POIs do OSM", use_container_width=True, key="btn_fetch_pois"):
            area_gdf = st.session_state.layers.get("area_estudo")
            if area_gdf is None or area_gdf.empty:
                st.error("Defina a area de estudo na etapa 2 antes de buscar POIs.")
            else:
                try:
                    polygon = area_gdf.geometry.iloc[0]
                except Exception:
                    polygon = None
                if polygon is None or polygon.is_empty:
                    st.error("Poligono da area de estudo invalido.")
                else:
                    with st.spinner("Consultando OpenStreetMap..."):
                        pois = osm_pois.fetch_pois_in_polygon(polygon)
                    if pois is None or pois.empty:
                        st.warning("Nenhum POI encontrado ou OSMnx indisponivel.")
                    else:
                        # mescla com pontos do usuario
                        new_rows = pois[["nome", "categoria", "latitude", "longitude", "descricao"]].copy()
                        st.session_state.user_points = pd.concat(
                            [st.session_state.user_points, new_rows], ignore_index=True
                        ).drop_duplicates(subset=["nome", "latitude", "longitude"])
                        st.success(f"✅ {len(new_rows)} POIs sugeridos adicionados a tabela. "
                                   f"Valide e edite na tabela abaixo ou na aba 📍 Pontos / Edicao.")
                        st.rerun()

    st.divider()
    st.markdown("##### 📋 POIs cadastrados (sugeridos + manuais)")
    if st.session_state.user_points.empty:
        st.info("Nenhum POI cadastrado. Use o botao acima ou cadastre manualmente na aba 📍 Pontos / Edicao.")
    else:
        edited = st.data_editor(
            st.session_state.user_points,
            num_rows="dynamic",
            use_container_width=True,
            key="wiz_poi_editor",
        )
        if not edited.equals(st.session_state.user_points):
            st.session_state.user_points = edited
        c1, c2 = st.columns(2)
        with c1:
            csv = st.session_state.user_points.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Baixar POIs como CSV", csv,
                               file_name="pois.csv", mime="text/csv",
                               use_container_width=True, key="wiz_dl_pois")
        with c2:
            if st.button("🗑️ Limpar todos os POIs", use_container_width=True, key="wiz_clear_pois"):
                st.session_state.user_points = pd.DataFrame(
                    columns=["nome", "categoria", "latitude", "longitude", "descricao"]
                )
                st.rerun()


# Renderizacao da aba Assistente
with tabs[0]:
    st.subheader("🧭 Assistente de Configuracao do Estudo")
    st.markdown(
        f"**Modo:** {'🎓 Demonstracao - Matias Barbosa/MG' if st.session_state.study_mode == 'demo' else '🌍 Novo estudo'}  \n"
        "Use as etapas abaixo para construir (ou ajustar) seu estudo de mobilidade. "
        "Mesmo no modo demonstracao, voce pode editar/redesenhar tudo."
    )

    if st.session_state.study_mode == "demo":
        st.info(
            "📚 *Dados demonstrativos elaborados para fins academicos, com base em "
            "zoneamento analitico e areas validadas preliminarmente pelos autores.*"
        )

    # Step state
    if "wizard_step_idx" not in st.session_state:
        st.session_state.wizard_step_idx = 0

    # ----- ATALHO: pular configuracao e ir direto para intervencoes -----
    if st.session_state.study_mode == "demo":
        st.markdown(
            """
            <div style="background:linear-gradient(135deg,#FFF8E1 0%,#FFFFFF 100%);
                        border-left:5px solid #F9A825;padding:16px 18px;border-radius:10px;
                        margin: 8px 0 12px 0;color:#5D4037;">
                <b>🚀 Atalho rapido para usar o estudo demonstrativo</b><br>
                <span style="font-size:0.9rem;">
                Se voce nao quer reconfigurar nada da demonstracao, pule direto para a
                <b>etapa 6</b> onde voce cadastra pontos de viaduto, ponte ou passagem de nivel.
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_sh1, col_sh2 = st.columns([1, 1])
        with col_sh1:
            if st.button("✅ Manter configuracao e ir para INTERVENCOES (etapa 6)",
                         use_container_width=True, type="primary", key="wiz_jump_to_pois"):
                st.session_state.wizard_step_idx = 5
                st.session_state.study_config_validated = True
                st.rerun()
        with col_sh2:
            st.markdown(
                """
                <div style="font-size:0.85rem;color:#666;padding:8px 4px;">
                ⚙️ <b>Fluxo recomendado:</b><br>
                1️⃣ <b>Baseline</b> ja existe ('Cenario Atual' na aba 🛠️ Cenarios) sem intervencoes.<br>
                2️⃣ Cadastre viadutos/pontes na etapa 6.<br>
                3️⃣ Crie cenarios usando esses pontos.<br>
                4️⃣ Veja melhora ou piora em 📊 Comparacao e 📑 Relatorio.
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.divider()

    # Barra de etapas
    cur_idx = st.session_state.wizard_step_idx
    st.markdown(f"**Etapa atual:** {cur_idx + 1} de {len(WIZARD_STEPS)} - **{WIZARD_STEPS[cur_idx]}**")
    st.progress((cur_idx + 1) / len(WIZARD_STEPS))

    # Botoes de navegacao
    cnav1, cnav2, cnav3, cnav4 = st.columns([1, 1, 1, 3])
    with cnav1:
        if st.button("⬅️ Voltar", use_container_width=True, disabled=cur_idx == 0, key="wiz_back"):
            st.session_state.wizard_step_idx = max(0, cur_idx - 1)
            st.rerun()
    with cnav2:
        if st.button("Proximo ➡️", use_container_width=True,
                     disabled=cur_idx == len(WIZARD_STEPS) - 1, key="wiz_next"):
            st.session_state.wizard_step_idx = min(len(WIZARD_STEPS) - 1, cur_idx + 1)
            st.rerun()
    with cnav3:
        if st.button("⏭️ Pular", use_container_width=True, key="wiz_skip"):
            st.session_state.wizard_step_idx = min(len(WIZARD_STEPS) - 1, cur_idx + 1)
            st.rerun()
    with cnav4:
        sel = st.selectbox("Ir para etapa:", list(range(len(WIZARD_STEPS))),
                           index=cur_idx, format_func=lambda i: WIZARD_STEPS[i],
                           label_visibility="collapsed", key="wiz_jump")
        if sel != cur_idx:
            st.session_state.wizard_step_idx = sel
            st.rerun()

    st.divider()

    # Renderiza a etapa
    step_renderers = [_step_municipio, _step_area_estudo, _step_via_principal,
                      _step_eixo_estruturante, _step_zonas, _step_pois]
    step_renderers[cur_idx]()

    st.divider()
    st.markdown("### ✅ Validar etapa de configuracao do estudo")
    validation.render_validation_button(
        state_key="study_config_validated",
        pending_label="Confirmar e manter configuracao atual do estudo",
        done_message="Configuracao atual mantida com sucesso.",
        next_step_label="🗺️ Mapa",
    )
    st.caption(
        "💡 Apos validar a configuracao, va nas abas seguintes na ordem: "
        "**🗺️ Mapa**, **📥 Importar**, **📍 Pontos**, **🔢 Matriz O-D**, **🛠️ Cenarios**, "
        "**📊 Comparacao** e **📑 Relatorio**."
    )


# ===========================================================================
# ABA 1 - MAPA
# ===========================================================================
def build_main_map() -> folium.Map:
    center = st.session_state.get("map_center", MATIAS_BARBOSA_CENTER)
    zoom = st.session_state.get("map_zoom", DEFAULT_ZOOM)
    label = (
        st.session_state.get("municipio_nome")
        or st.session_state.get("municipio_info", {}).get("display")
        or "Area de Estudo"
    )
    m = map_utils.create_base_map(center=center, zoom=zoom, label=label)

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
        viad_gdf_full = layers.get("pontos_viaduto")
        if viad_gdf_full is not None and not viad_gdf_full.empty:
            # Cada ponto vira uma camada individual no controle do mapa.
            # Os ativos comecam visiveis; os inativos comecam ocultos.
            # O usuario tambem pode toggle visualmente direto no mapa.
            active = st.session_state.get("active_viaducts", set(range(len(viad_gdf_full))))
            map_utils.add_pontos_viaduto(m, viad_gdf_full, active_indices=active)
        else:
            map_utils.add_pontos_viaduto(m, viad_gdf_full)
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

    # Malha viaria real (OSM)
    if show.get("osm") and st.session_state.osm_edges is not None:
        map_utils.add_osm_network(m, st.session_state.osm_edges)

    # Linhas de fluxo
    if show.get("flow") and st.session_state.flow_records:
        map_utils.add_flow_lines(m, st.session_state.flow_records)

    map_utils.add_draw_control(m)
    map_utils.add_layer_control(m)
    return m


with tabs[1]:
    st.subheader("🗺️ Mapa Interativo")

    # ----- PONTOS DE VIADUTO: controle de PARTICIPACAO NA SIMULACAO -----
    # Importante: esta secao precede o mapa para deixar claro que
    # estes checkboxes sao a fonte da verdade da simulacao.
    viad_gdf_top = st.session_state.layers.get("pontos_viaduto")
    if viad_gdf_top is not None and not viad_gdf_top.empty:
        st.markdown("### 🟢 Pontos de estudo de viaduto - **PARTICIPACAO NA SIMULACAO**")
        st.warning(
            "⚠️ **IMPORTANTE:** os checkboxes ABAIXO determinam quais viadutos entram nos "
            "cenarios da aba 🛠️ Cenarios.  \n"
            "👁️ O controle de camadas DENTRO do mapa (lateral direita) e **apenas visual** &mdash; "
            "ele NAO afeta a simulacao."
        )

        if "active_viaducts" not in st.session_state:
            st.session_state.active_viaducts = set(range(min(4, len(viad_gdf_top))))
        current_active_top = set(st.session_state.active_viaducts)

        n_pts_top = len(viad_gdf_top)
        cols_chk_top = st.columns(min(n_pts_top, 4))
        new_active_top = set()
        for i, (_, row) in enumerate(viad_gdf_top.iterrows()):
            nome = row.get("nome", f"Ponto {i+1}")
            descricao = row.get("descricao", "")
            with cols_chk_top[i % len(cols_chk_top)]:
                was_active = i in current_active_top
                would_exceed = (len(new_active_top) >= 4) and not was_active
                checked = st.checkbox(
                    f"✅ **{nome}**" if was_active else f"⬜ {nome}",
                    value=was_active,
                    key=f"chk_viad_top_{i}",
                    help=f"{descricao}\n\nMarcar = incluir na simulacao",
                    disabled=would_exceed,
                )
                if checked and not would_exceed:
                    new_active_top.add(i)

        if new_active_top != current_active_top:
            st.session_state.active_viaducts = new_active_top
            st.session_state.base_graph = None  # forca rebuild do grafo
            validation.invalidate("map_step_validated")
            st.rerun()

        active_count_top = len(st.session_state.active_viaducts)
        if active_count_top == 0:
            st.error("❌ **Nenhum viaduto incluido na simulacao.** Cenarios de viaduto NAO "
                     "serao gerados. Apenas a matriz O-D base estara disponivel.")
        elif active_count_top == len(viad_gdf_top):
            st.success(f"✅ Todos os {active_count_top} viadutos serao considerados na simulacao.")
        else:
            inactive_names = [
                viad_gdf_top.iloc[i].get("nome", f"V{i+1}")
                for i in range(len(viad_gdf_top))
                if i not in st.session_state.active_viaducts
            ]
            st.info(
                f"✅ **{active_count_top} de {len(viad_gdf_top)} viaduto(s)** serao considerados. "
                f"Excluidos: _{', '.join(inactive_names)}_."
            )
        st.divider()

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

    # ----- Botao de validacao da etapa Mapa -----
    st.divider()
    st.markdown("### ✅ Salvar alteracoes do mapa")
    validation.render_validation_button(
        state_key="map_step_validated",
        pending_label="Salvar alteracoes do mapa",
        done_message="Alteracoes do mapa salvas com sucesso.",
        next_step_label="📥 Importar Arquivos Geograficos",
    )


# ===========================================================================
# ABA 2 - IMPORTAR
# ===========================================================================
with tabs[2]:
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
                validation.invalidate("imports_step_validated")
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

    # ----- Pergunta + validacao da etapa Importar -----
    st.divider()
    st.markdown("### 📥 Deseja importar outros dados geograficos relevantes para este estudo?")
    if "imports_choice" not in st.session_state:
        st.session_state.imports_choice = "Nao, manter dados atuais"
    st.session_state.imports_choice = st.radio(
        "Selecione uma opcao:",
        options=["Sim, importar arquivos (use o uploader acima)", "Nao, manter dados atuais"],
        index=0 if st.session_state.imports_choice.startswith("Sim") else 1,
        key="imports_choice_radio",
    )

    st.markdown("### ✅ Confirmar dados geograficos")
    validation.render_validation_button(
        state_key="imports_step_validated",
        pending_label="Confirmar dados geograficos",
        done_message="Dados geograficos confirmados.",
        next_step_label="📍 Cadastro de Pontos de Interesse",
    )


# ===========================================================================
# ABA 3 - PONTOS / EDICAO
# ===========================================================================
with tabs[3]:
    st.subheader("📍 Cadastro de pontos de interesse")
    st.caption("Pontos cadastrados aqui ficam disponiveis durante a sessao e aparecem no mapa.")

    # ----- Toggle 'Manter' vs 'Liberar edicao' -----
    if "points_edit_mode" not in st.session_state:
        st.session_state.points_edit_mode = "manter"  # default: read-only nos cadastros

    col_pt_a, col_pt_b = st.columns(2)
    with col_pt_a:
        if st.button(
            "🔒 Manter dados do estudo atual",
            use_container_width=True,
            type="primary" if st.session_state.points_edit_mode == "manter" else "secondary",
            key="btn_pts_manter",
        ):
            st.session_state.points_edit_mode = "manter"
            st.rerun()
    with col_pt_b:
        if st.button(
            "✏️ Liberar edicao (editar / remover pontos)",
            use_container_width=True,
            type="primary" if st.session_state.points_edit_mode == "editar" else "secondary",
            key="btn_pts_editar",
        ):
            st.session_state.points_edit_mode = "editar"
            st.rerun()

    if st.session_state.points_edit_mode == "manter":
        st.info(
            "🔒 **Modo 'Manter'** ativo: os dados base do estudo permanecem preservados. "
            "Voce **continua podendo adicionar novos pontos** (viadutos, pontes, etc.) "
            "abaixo, mas a tabela existente fica em **somente leitura**."
        )
    else:
        st.success(
            "✏️ **Edicao liberada**: voce pode adicionar, editar e remover pontos. "
            "Cuidado: alteracoes/remocoes refletem na aba 🛠️ Cenarios e na 📑 Relatorio."
        )

    st.info(
        "💡 **Pontos com categorias de infraestrutura** "
        "(Viaduto proposto, Ponte proposta, Passagem inferior/superior/em nivel, "
        "Travessia critica, Nova ligacao viaria) **viram automaticamente nos selecionaveis "
        "na aba 🛠️ Cenarios** &mdash; assim voce pode simular interligacoes a partir deles."
    )

    with st.expander("📖 O que cada categoria significa"):
        st.markdown(
            """
| Categoria | Significado |
|---|---|
| **🟢 Estudo de viaduto** | Ponto candidato a receber um viaduto, ainda em estudo de viabilidade |
| **🟢 Viaduto proposto** | Local definido para um viaduto (passagem **superior** sobre via/ferrovia/curso d'agua) |
| **🔵 Ponte proposta** | Local de uma nova ponte (geralmente sobre rio, corrego ou vale) |
| **🟠 Passagem inferior de nivel** | Tunel/passagem por **baixo** da ferrovia ou rodovia |
| **🟢 Passagem superior de nivel** | Passagem por **cima** (equivalente conceitual a viaduto) |
| **🔴 Passagem em nivel** | Cruzamento no mesmo nivel da via principal &mdash; geralmente critico em ferrovias |
| **🔴 Travessia critica** | Ponto onde pedestres / veiculos atravessam de forma insegura |
| **🟣 Nova ligacao viaria** | Trecho de rua/avenida proposto para conectar areas hoje isoladas |
| **🔵 Escola / 🟢 Comercio / 🔴 Industria / 🟠 Terminal** | Geradores/atratores de viagens (entram apenas como POIs, nao como nos do grafo) |
"""
        )

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
                validation.invalidate("pois_step_validated")
                st.success(f"Ponto '{nome}' adicionado.")

    st.markdown("##### Pontos cadastrados na sessao")
    if st.session_state.user_points.empty:
        st.info("Nenhum ponto cadastrado ainda.")
    else:
        if st.session_state.points_edit_mode == "manter":
            # somente leitura - preserva os dados do estudo
            st.dataframe(
                st.session_state.user_points,
                use_container_width=True,
                hide_index=True,
            )
            st.caption("🔒 Tabela em modo leitura. Clique em '✏️ Liberar edicao' acima para modificar.")
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

    # ----- Validacao da etapa Pontos de Interesse -----
    st.divider()
    if st.session_state.user_points.empty:
        st.info(
            "ℹ️ **Nenhum ponto de interesse foi cadastrado ate o momento.** "
            "Voce pode cadastrar pontos manualmente, importar arquivo ou manter o estudo "
            "sem pontos de interesse adicionais."
        )
    st.markdown("### ✅ Confirmar pontos de interesse")
    validation.render_validation_button(
        state_key="pois_step_validated",
        pending_label="Confirmar pontos de interesse",
        done_message="Pontos de interesse confirmados.",
        next_step_label="🔢 Matriz O-D",
    )


# ===========================================================================
# ABA 4 - MATRIZ O-D
# ===========================================================================
with tabs[4]:
    st.subheader("🔢 Matriz Origem-Destino simplificada (modelo gravitacional)")
    st.info(
        "📘 **A matriz origem-destino simplificada representa os fluxos potenciais entre "
        "zonas analiticas** com base em pesos de geracao, pesos de atracao e distancia "
        "entre zonas. **Os pontos de estudo de viaduto NAO alteram esta matriz "
        "diretamente** &mdash; eles serao considerados na etapa de 🛠️ Cenarios, onde as "
        "intervencoes mudam o trajeto pelas ruas e, consequentemente, a distancia "
        "efetiva entre as zonas."
    )
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

    if recalc:
        validation.invalidate("od_step_validated")
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
        # matriz O-D - usa format() simples (background_gradient requer matplotlib)
        st.dataframe(
            st.session_state.od_result.style.format("{:.3f}"),
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

    # ----- Validacao da etapa Matriz O-D -----
    st.divider()
    st.markdown("### ✅ Confirmar Matriz O-D")
    validation.render_validation_button(
        state_key="od_step_validated",
        pending_label="Confirmar Matriz O-D",
        done_message="Matriz O-D confirmada. Os dados estao validados para a etapa de Cenarios.",
        next_step_label="🛠️ Cenarios",
    )


# ===========================================================================
# ABA 5 - CENARIOS
# ===========================================================================
def get_or_build_base_graph(force: bool = False):
    if force or st.session_state.base_graph is None:
        st.session_state.base_graph = net.build_analysis_graph(
            st.session_state.layers.get("zonas"),
            st.session_state.layers.get("pontos_viaduto"),
            osm_graph=st.session_state.get("osm_graph"),
            user_points_df=st.session_state.get("user_points"),
            infra_categories=INFRA_CATEGORIES,
        )
    return st.session_state.base_graph


with tabs[5]:
    st.subheader("🛠️ Simulacao de cenarios de intervencao")
    st.caption(
        "Crie cenarios com novas ligacoes viarias, viadutos, pontes ou bloqueios. "
        "As intervencoes alteram arestas do grafo analitico (centroides de zona + pontos de viaduto)."
    )

    # Aviso sobre pontos de viaduto ativos
    viad_gdf_layer = st.session_state.layers.get("pontos_viaduto")
    active_viaducts_set = st.session_state.get("active_viaducts", set())
    if viad_gdf_layer is not None and not viad_gdf_layer.empty:
        n_active = len(active_viaducts_set)
        n_total = len(viad_gdf_layer)
        if n_active == 0:
            st.warning(
                "⚠️ **Nenhum ponto de estudo de viaduto esta ativo na aba 🗺️ Mapa.** "
                "Cenarios com viaduto NAO serao gerados ate que pelo menos um ponto seja ativado. "
                "Apenas o cenario atual (baseline) e a matriz O-D estarao disponiveis."
            )
        else:
            st.success(f"✅ {n_active} de {n_total} ponto(s) de viaduto ativo(s) - "
                       f"cenarios de viaduto serao considerados.")

    # ----- Modo de simulacao: cenario individual ou completa -----
    if "scenarios_mode" not in st.session_state:
        st.session_state.scenarios_mode = None
    if "scenarios_generated" not in st.session_state:
        st.session_state.scenarios_generated = False

    st.markdown("### 🎯 Escolha o tipo de simulacao")
    col_mode1, col_mode2 = st.columns(2)
    with col_mode1:
        sel_a = st.button(
            "🎯 Simulacao de cenario (individual)",
            use_container_width=True,
            type="primary" if st.session_state.scenarios_mode == "individual" else "secondary",
            help="Escolha manualmente um cenario especifico (viaduto, ponte, nova ligacao, "
                 "bloqueio, etc.)",
            key="btn_mode_individual",
        )
        if sel_a:
            st.session_state.scenarios_mode = "individual"
            st.rerun()
    with col_mode2:
        sel_b = st.button(
            "🚀 Simulacao completa (automatica)",
            use_container_width=True,
            type="primary" if st.session_state.scenarios_mode == "completa" else "secondary",
            help="Gera automaticamente um cenario para cada ponto de viaduto ativo.",
            key="btn_mode_completa",
        )
        if sel_b:
            st.session_state.scenarios_mode = "completa"
            st.rerun()

    if st.session_state.scenarios_mode is None:
        st.info("👆 Selecione um dos modos acima para comecar.")

    # Reconstrucao do grafo sempre que esta aba e exibida, para incorporar
    # pontos novos cadastrados pelo usuario na aba Pontos/Edicao.
    G = get_or_build_base_graph(force=True)
    # Mostra apenas nos analiticos (zonas, pontos de viaduto, pontos do usuario);
    # os nos OSM sao apenas a estrutura interna usada para calcular caminhos reais.
    node_options = [
        n for n, d in G.nodes(data=True)
        if d.get("tipo") in ("zona", "viaduto", "usuario")
    ]

    def _fmt_node(n):
        d = G.nodes[n]
        cat = d.get("categoria")
        nome = d.get("nome", n)
        tipo = d.get("tipo")
        prefix = {"zona": "🟪 Zona", "viaduto": "🟢 Pto. viaduto", "usuario": "📍 Cadastrado"}.get(tipo, tipo)
        if cat:
            return f"{prefix} | {nome} ({cat})"
        return f"{prefix} | {nome}"

    if st.session_state.get("osm_graph") is not None:
        st.info(
            f"🛣️ Malha viaria OSM ativa - as distancias entre zonas sao calculadas "
            f"atraves das ruas reais ({st.session_state.osm_graph.number_of_edges()} segmentos). "
            f"As intervencoes (viaduto/ponte/passagem de nivel) sao adicionadas como "
            f"novas arestas que se conectam a essa malha."
        )
    else:
        st.warning(
            "⚠️ Malha viaria OSM nao carregada. As distancias usam haversine entre centroides. "
            "Para resultados mais realistas, baixe a malha na barra lateral em **🛣️ Malha viaria real (OSM)**."
        )

    if not node_options:
        st.warning("Nenhum no disponivel. Verifique se as zonas estao carregadas.")
    elif st.session_state.scenarios_mode == "completa":
        st.markdown("### 🚀 Simulacao completa (automatica)")
        st.caption(
            "Gera um cenario para cada **ponto de viaduto ativo** na aba 🗺️ Mapa, "
            "conectando-o a zona mais proxima com fator de impedancia 0.5 (atalho por viaduto)."
        )
        viad_layer = st.session_state.layers.get("pontos_viaduto")
        active_set = st.session_state.get("active_viaducts", set())
        if viad_layer is None or viad_layer.empty or not active_set:
            st.warning("Nenhum ponto de viaduto ativo - habilite na aba 🗺️ Mapa primeiro.")
        else:
            if st.button("🛠️ Gerar cenarios automaticamente (1 por viaduto ativo)",
                         use_container_width=True, type="secondary", key="btn_gen_auto"):
                # remove cenarios automaticos anteriores (mantem o atual e os manuais)
                st.session_state.scenarios = [
                    s for s in st.session_state.scenarios
                    if s.nome == "Cenario Atual" or not s.nome.startswith("[AUTO]")
                ]
                viaduto_nodes = [n for n, d in G.nodes(data=True) if d.get("tipo") == "viaduto"]
                zona_nodes = [n for n, d in G.nodes(data=True) if d.get("tipo") == "zona"]
                created = 0
                for i in active_set:
                    if i >= len(viad_layer):
                        continue
                    p_nome = viad_layer.iloc[i].get("nome", f"V{i+1}")
                    target_v = next((n for n in viaduto_nodes if G.nodes[n].get("nome") == p_nome), None)
                    if target_v is None and viaduto_nodes:
                        target_v = viaduto_nodes[i % len(viaduto_nodes)]
                    if target_v is None or len(zona_nodes) < 2:
                        continue

                    # NOVO: viaduto serve como PONTE entre as 2 zonas que estao em
                    # lados opostos do ponto. Buscamos as 2 zonas mais distantes
                    # entre si que estejam relativamente proximas ao viaduto - elas
                    # tipicamente representam o conflito ferrovia/rodovia que o
                    # viaduto resolve.
                    v_lat, v_lon = G.nodes[target_v]["lat"], G.nodes[target_v]["lon"]
                    # raio de relevancia: zonas a ate 3 km do viaduto
                    nearby = []
                    for z in zona_nodes:
                        z_lat, z_lon = G.nodes[z]["lat"], G.nodes[z]["lon"]
                        d = od_matrix.haversine_km(v_lat, v_lon, z_lat, z_lon)
                        if d <= 3.0:
                            nearby.append((z, d))
                    if len(nearby) < 2:
                        # fallback: pega as 2 zonas mais proximas mesmo se distantes
                        all_z = sorted(
                            [(z, od_matrix.haversine_km(v_lat, v_lon,
                                                         G.nodes[z]["lat"], G.nodes[z]["lon"]))
                             for z in zona_nodes],
                            key=lambda x: x[1],
                        )
                        nearby = all_z[:2]

                    # entre as zonas proximas, escolhe o par com maior distancia
                    # entre si (= par que mais se beneficia do atalho)
                    best_pair, best_pair_d = None, -1.0
                    for a_idx in range(len(nearby)):
                        for b_idx in range(a_idx + 1, len(nearby)):
                            z_a, z_b = nearby[a_idx][0], nearby[b_idx][0]
                            d_ab = od_matrix.haversine_km(
                                G.nodes[z_a]["lat"], G.nodes[z_a]["lon"],
                                G.nodes[z_b]["lat"], G.nodes[z_b]["lon"],
                            )
                            if d_ab > best_pair_d:
                                best_pair_d, best_pair = d_ab, (z_a, z_b)

                    if best_pair is None:
                        continue
                    z_a, z_b = best_pair
                    s = scen.Scenario(
                        nome=f"[AUTO] Viaduto {p_nome}",
                        tipo="Cenario com viaduto",
                        descricao=(
                            f"Viaduto em {p_nome} servindo como ponte entre "
                            f"{z_a.replace('Z:','')} e {z_b.replace('Z:','')}"
                        ),
                    )
                    # Duas arestas: V -> Z_a (factor 0.4) e V -> Z_b (factor 0.4)
                    # Isso permite que Z_a <-> Z_b passem por V como atalho.
                    s.intervencoes.append({
                        "from": target_v, "to": z_a, "factor": 0.4, "tipo": "viaduto",
                    })
                    s.intervencoes.append({
                        "from": target_v, "to": z_b, "factor": 0.4, "tipo": "viaduto",
                    })
                    # Aresta direta entre as duas zonas com fator pequeno,
                    # representando que o viaduto efetivamente encurta o trajeto.
                    s.intervencoes.append({
                        "from": z_a, "to": z_b, "factor": 0.5, "tipo": "viaduto-shortcut",
                    })
                    st.session_state.scenarios.append(s)
                    created += 1
                if created:
                    st.success(f"✅ {created} cenarios automaticos gerados.")
                    st.session_state.scenarios_generated = True
                    validation.invalidate("scenarios_step_validated")
                    st.rerun()
                else:
                    st.warning("Nenhum cenario foi gerado.")

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

    elif st.session_state.scenarios_mode == "individual":
        with st.form("form_cenario", clear_on_submit=False):
            st.markdown("##### Novo cenario")
            col1, col2 = st.columns([2, 2])
            with col1:
                cen_nome = st.text_input("Nome do cenario", value="Cenario com viaduto V2")
                cen_tipo = st.selectbox("Tipo de intervencao", scen.SCENARIO_TYPES, index=1)
                cen_desc = st.text_area("Descricao", value="Implantacao de viaduto sobre a ferrovia ligando Z1 e Z3", height=80)
            with col2:
                from_node = st.selectbox("No A (origem)", node_options, index=0, format_func=_fmt_node)
                to_node = st.selectbox("No B (destino)", node_options, index=min(1, len(node_options) - 1), format_func=_fmt_node)
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
                    st.session_state.scenarios_generated = True
                    validation.invalidate("scenarios_step_validated")
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
                    validation.invalidate("scenarios_step_validated")
                    st.rerun()

    # ----- Validacao da etapa Cenarios -----
    if st.session_state.scenarios_mode is not None:
        st.divider()
        st.markdown("### ✅ Confirmar simulacao de cenarios")
        n_extra = sum(1 for s in st.session_state.scenarios if s.nome != "Cenario Atual")
        if n_extra == 0:
            st.info(
                "ℹ️ Voce ainda nao adicionou nenhum cenario alem do baseline. "
                "Adicione ao menos um cenario antes de validar esta etapa "
                "(ou marque como validado para usar apenas o baseline)."
            )
        validation.render_validation_button(
            state_key="scenarios_step_validated",
            pending_label="Gerar / confirmar simulacao de cenarios",
            done_message="Simulacao de cenarios gerada com sucesso.",
            next_step_label="📊 Comparacao e 📑 Relatorio",
        )


# ===========================================================================
# ABA 6 - COMPARACAO
# ===========================================================================
with tabs[6]:
    st.subheader("📊 Comparacao de cenarios")

    # Gating: so mostra se cenarios foram efetivamente gerados
    if not st.session_state.get("scenarios_generated", False):
        st.warning(
            "⚠️ **Nenhuma simulacao de cenario foi gerada ainda.** "
            "Acesse a aba 🛠️ Cenarios e clique em **'Simulacao de cenario'** ou "
            "**'Simulacao completa'** para gerar a comparacao."
        )
        st.stop()

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
                # so vale a pena destacar se o melhor cenario nao for o baseline
                if best["cenario"] != "Cenario Atual" and float(best.get("reducao_percurso_pct", 0)) > 0.5:
                    red_pct = float(best["reducao_percurso_pct"])
                    dist_med = float(best["distancia_media_km"])
                    tempo_med = float(best["tempo_medio_min"])
                    # baseline
                    base_row = df_compare[df_compare["cenario"] == "Cenario Atual"].iloc[0]
                    base_dist = float(base_row["distancia_media_km"])
                    base_tempo = float(base_row["tempo_medio_min"])
                    dist_savings = base_dist - dist_med
                    tempo_savings = base_tempo - tempo_med

                    nome_curto = best["cenario"].replace("[AUTO] Viaduto ", "").replace("[AUTO]", "").strip()

                    st.success(
                        f"### 🏆 **{nome_curto}** foi o ponto de estudo que mais reduziu o tempo de "
                        f"travessia entre as zonas da cidade.  \n\n"
                        f"📉 **Reducao media de percurso entre zonas:** **{red_pct:.1f}%**  \n"
                        f"📏 **Distancia media baseline:** {base_dist:.3f} km → **com intervencao:** {dist_med:.3f} km "
                        f"(economia de **{dist_savings:.3f} km** por viagem)  \n"
                        f"⏱️ **Tempo medio baseline:** {base_tempo:.2f} min → **com intervencao:** {tempo_med:.2f} min "
                        f"(economia de **{tempo_savings:.2f} min** por viagem)  \n\n"
                        f"💡 **Interpretacao:** A implantacao do **{nome_curto}** "
                        f"({best['tipo'].lower()}) reduz significativamente a distancia que veiculos precisam "
                        f"percorrer hoje contornando a ferrovia/rodovia para ligar as zonas urbanas. "
                        f"Indicando ganho de **conectividade urbana** e diminuicao do **efeito barreira** "
                        f"sobre a mobilidade do municipio."
                    )
                elif best["cenario"] == "Cenario Atual":
                    st.warning(
                        "📊 **Nenhuma intervencao gerou reducao significativa** em relacao ao baseline. "
                        "Possiveis causas:  \n"
                        "• A malha viaria OSM cobre uma area pequena (aumente o raio na sidebar);  \n"
                        "• Os pontos de viaduto ja estao em areas com boa conectividade;  \n"
                        "• A configuracao das intervencoes (fator de impedancia) pode ser ajustada na aba 🛠️ Cenarios."
                    )
                else:
                    st.info(
                        f"**Cenario mais vantajoso:** {best['cenario']}  \n"
                        f"**Tipo:** {best['tipo']}  \n"
                        f"{best['observacao']}"
                    )

            # ============================================================
            # MATRIZES O-D POR CENARIO (par a par)
            # ============================================================
            st.divider()
            st.markdown("### 🔢 Matrizes O-D por cenario (par a par)")
            st.caption(
                "Para cada cenario, mostramos a matriz de **distancia entre zonas** "
                "(km via rede viaria), a matriz de **viagens** (modelo gravitacional) "
                "e o **delta** comparando com o cenario baseline ponto a ponto."
            )

            # Computa baseline primeiro
            zonas_gdf = st.session_state.layers.get("zonas")
            if zonas_gdf is None or zonas_gdf.empty:
                st.warning("Cadastre zonas analiticas para ver as matrizes detalhadas.")
            else:
                baseline_scen = st.session_state.scenarios[0]  # 'Cenario Atual'
                G_base_sc = baseline_scen.apply(G)
                dist_base_net = net.zone_distance_matrix(G_base_sc)
                dist_base = od_matrix.network_distance_matrix_to_zonas_df(
                    dist_base_net, st.session_state.zonas_df
                )
                if dist_base.empty:
                    # fallback haversine se a rede nao da resultado util
                    dist_base = od_matrix.build_distance_matrix(zonas_gdf)
                od_base = od_matrix.gravity_od(
                    st.session_state.zonas_df, dist_base, beta=2.0, normalize=True
                )

                st.markdown("##### 🟢 Baseline (Cenario Atual - sem intervencao)")
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    st.caption("**Distancia entre zonas (km)**")
                    st.dataframe(dist_base.style.format("{:.3f}"), use_container_width=True)
                with col_b2:
                    st.caption("**Viagens estimadas (matriz O-D normalizada %)**")
                    st.dataframe(od_base.style.format("{:.3f}"), use_container_width=True)

                # Por cenario nao-baseline
                for s in st.session_state.scenarios[1:]:
                    with st.expander(f"📊 Cenario: **{s.nome}** ({s.tipo})"):
                        try:
                            G_s = s.apply(G)
                            dist_s_net = net.zone_distance_matrix(G_s)
                            dist_s = od_matrix.network_distance_matrix_to_zonas_df(
                                dist_s_net, st.session_state.zonas_df
                            )
                            if dist_s.empty:
                                dist_s = od_matrix.build_distance_matrix(zonas_gdf)
                            od_s = od_matrix.gravity_od(
                                st.session_state.zonas_df, dist_s, beta=2.0, normalize=True
                            )
                        except Exception as exc:
                            st.error(f"Erro ao calcular: {exc}")
                            continue

                        c1, c2 = st.columns(2)
                        with c1:
                            st.caption("**Distancia entre zonas (km)**")
                            st.dataframe(dist_s.style.format("{:.3f}"), use_container_width=True)
                        with c2:
                            st.caption("**Viagens estimadas (matriz O-D %)**")
                            st.dataframe(od_s.style.format("{:.3f}"), use_container_width=True)

                        # Delta vs baseline (par a par)
                        common_idx = [i for i in dist_s.index if i in dist_base.index]
                        common_col = [c for c in dist_s.columns if c in dist_base.columns]
                        if common_idx and common_col:
                            ds = dist_s.loc[common_idx, common_col].astype(float)
                            db = dist_base.loc[common_idx, common_col].astype(float)
                            delta_dist = (ds - db).round(3)
                            pct_dist = ((ds - db) / db.replace(0, float("nan")) * 100).round(2)

                            os = od_s.loc[common_idx, common_col].astype(float)
                            ob = od_base.loc[common_idx, common_col].astype(float)
                            delta_od = (os - ob).round(3)

                            st.markdown("**🔄 Delta vs baseline:**")
                            dc1, dc2, dc3 = st.columns(3)
                            with dc1:
                                st.caption("Δ Distancia (km, negativo = melhor)")
                                st.dataframe(delta_dist.style.format("{:+.3f}"),
                                             use_container_width=True)
                            with dc2:
                                st.caption("Δ Distancia (% - reducao se negativo)")
                                st.dataframe(pct_dist.style.format("{:+.2f}%"),
                                             use_container_width=True)
                            with dc3:
                                st.caption("Δ Viagens (positivo = mais fluxo gerado)")
                                st.dataframe(delta_od.style.format("{:+.3f}"),
                                             use_container_width=True)

                            # Pares mais beneficiados
                            d_unstack = pct_dist.where(pct_dist < 0).stack().sort_values()
                            if not d_unstack.empty:
                                top_pairs = d_unstack.head(3)
                                st.markdown("**📌 Top pares com maior reducao de distancia:**")
                                for (i, j), pct in top_pairs.items():
                                    if i == j:
                                        continue
                                    st.markdown(f"- **{i} → {j}**: reducao de **{abs(pct):.2f}%** "
                                               f"({delta_dist.loc[i, j]:+.3f} km)")


# ===========================================================================
# ABA 7 - RELATORIO
# ===========================================================================
with tabs[7]:
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

    area_nome_report = (
        st.session_state.get("municipio_nome")
        or st.session_state.get("municipio_info", {}).get("display")
        or "Area de Estudo"
    )
    # Dados opcionais do bloco de atualizacao (aba 9)
    _rp = st.session_state.get("_rail_params")
    _rail_table = rail_params.compute_blocking_table(_rp) if _rp else None
    _assign_edges = (
        st.session_state.get("assignment_result", {}).get("edges_df")
        if "assignment_result" in st.session_state else None
    )
    md = report_generator.build_markdown_report(
        area_nome=area_nome_report,
        zonas_df=st.session_state.zonas_df,
        pontos_df=st.session_state.user_points,
        od_matrix=od if od is not None else pd.DataFrame(),
        od_summary_df=od_sum if od_sum is not None else pd.DataFrame(),
        scenarios_compare=df_compare,
        best_scenario_row=best,
        metadata_bases=st.session_state.get("_metadata"),
        calibration_source=st.session_state.get("calibration_source"),
        rail_params_data=_rp,
        rail_blocking_table=_rail_table,
        social_cost=st.session_state.get("_social_cost"),
        assignment_edges_df=_assign_edges,
    )

    st.markdown(md, unsafe_allow_html=False)

    st.divider()
    st.markdown("##### ⬇️ Download do relatorio")

    col1, col2, col3, col4 = st.columns(4)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    with col1:
        st.download_button(
            "📄 Baixar .md",
            data=md.encode("utf-8"),
            file_name=f"relatorio_{stamp}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "📃 Baixar .txt",
            data=md.encode("utf-8"),
            file_name=f"relatorio_{stamp}.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col3:
        html = report_generator.build_html_report(md)
        st.download_button(
            "🌐 Baixar .html",
            data=html.encode("utf-8"),
            file_name=f"relatorio_{stamp}.html",
            mime="text/html",
            use_container_width=True,
        )
    with col4:
        try:
            pdf_bytes = report_generator.build_pdf_report(
                area_nome=area_nome_report,
                zonas_df=st.session_state.zonas_df,
                pontos_df=st.session_state.user_points,
                od_matrix=od if od is not None else pd.DataFrame(),
                od_summary_df=od_sum if od_sum is not None else pd.DataFrame(),
                scenarios_compare=df_compare,
                best_scenario_row=best,
            )
        except Exception as exc:
            pdf_bytes = None
            st.caption(f"⚠️ PDF indisponivel: {exc}")
        if pdf_bytes is not None:
            st.download_button(
                "📕 Baixar .pdf",
                data=pdf_bytes,
                file_name=f"relatorio_{stamp}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            st.info("📕 PDF indisponivel - reportlab nao instalado neste ambiente. Use .html ou .md.")


# ===========================================================================
# ABA 8 - ALOCACAO SIMPLIFICADA (all-or-nothing na rede OSM)
# ===========================================================================
with tabs[8]:
    st.subheader("🚦 Alocacao Simplificada dos Fluxos O-D na Rede")
    st.caption(
        "Aloca os fluxos da matriz O-D nos caminhos minimos da rede viaria "
        "real para identificar trechos com maior carregamento potencial."
    )

    st.warning(
        "⚠️ **Esta alocacao e exploratoria** (metodo 'all-or-nothing'). "
        "Nao substitui modelo de trafego calibrado, contagens volumetricas "
        "ou simulacao microscopica (SUMO/AequilibraE)."
    )

    osm_graph = st.session_state.get("osm_graph")
    od_result = st.session_state.get("od_result")
    zonas_gdf = st.session_state.layers.get("zonas")

    col_a1, col_a2 = st.columns([2, 1])
    with col_a1:
        st.markdown("##### Pre-requisitos")
        chk_osm = osm_graph is not None
        chk_od = od_result is not None and not od_result.empty
        chk_zonas = zonas_gdf is not None and not zonas_gdf.empty
        st.markdown(
            f"- {'✅' if chk_osm else '❌'} Malha viaria OSM carregada "
            f"(sidebar → 'Baixar/atualizar')  \n"
            f"- {'✅' if chk_od else '❌'} Matriz O-D calculada "
            f"(aba 🔢 Matriz O-D → 'Recalcular')  \n"
            f"- {'✅' if chk_zonas else '❌'} Zonas analiticas com centroides"
        )
    with col_a2:
        run_assignment = st.button(
            "🚀 Executar alocacao", type="primary",
            use_container_width=True, key="btn_run_assignment",
            disabled=not (chk_osm and chk_od and chk_zonas),
        )

    if run_assignment:
        with st.spinner("Calculando caminhos minimos e alocando fluxos..."):
            centroids = od_matrix.zone_centroids(zonas_gdf)
            assignment_result = traffic_assignment.assign_od_to_network(
                od_matrix=od_result,
                zone_centroids_df=centroids,
                osm_graph=osm_graph,
            )
            if assignment_result is None or assignment_result.get("edge_loads") is None:
                st.error("Falha ao executar alocacao. Verifique se OSMnx esta funcional.")
            else:
                edges_df = traffic_assignment.classify_load_levels(
                    assignment_result["edge_loads"]
                )
                st.session_state.assignment_result = {
                    "edges_df": edges_df,
                    "unreachable": assignment_result["unreachable"],
                    "n_paths": len(assignment_result["paths"]),
                }
                st.success(f"✅ Alocacao concluida: {len(edges_df)} arestas carregadas, "
                           f"{len(assignment_result['paths'])} caminhos calculados.")

    # Apresenta resultados se houver
    if "assignment_result" in st.session_state:
        result = st.session_state.assignment_result
        edges_df = result["edges_df"]

        st.divider()
        st.markdown("##### 🏆 Ranking - Trechos com maior carregamento potencial")
        top_n = st.slider("Mostrar top N trechos:", 5, 50, 15, 5, key="top_edges_slider")
        st.dataframe(
            edges_df.head(top_n)[
                ["nome_via", "highway", "comprimento_m",
                 "fluxo_acumulado", "n_pares_od", "pares_od"]
            ],
            use_container_width=True,
        )

        st.markdown("##### 📊 Distribuicao de carregamento")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            st.metric("Arestas carregadas", len(edges_df))
        with col_d2:
            st.metric("Fluxo maximo (relativo)",
                      f"{edges_df['fluxo_acumulado'].max():.2f}")
        with col_d3:
            st.metric("Pares O-D sem caminho", len(result["unreachable"]))

        if result["unreachable"]:
            with st.expander("⚠️ Pares O-D sem caminho na rede"):
                st.write(", ".join(f"{o}→{d}" for o, d in result["unreachable"]))

        csv_export = edges_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Baixar alocacao (CSV)", data=csv_export,
            file_name="alocacao_simplificada.csv", mime="text/csv",
        )
    else:
        if not (chk_osm and chk_od and chk_zonas):
            st.info(
                "📌 Complete os pre-requisitos acima antes de rodar a alocacao. "
                "Se a rede nao estiver disponivel, a alocacao em rede esta indisponivel - "
                "consulte a matriz O-D direta na aba 🔢 Matriz O-D."
            )


# ===========================================================================
# ABA 9 - ATUALIZACAO DE DADOS (metadados, populacao, ferroviario, custo)
# ===========================================================================
with tabs[9]:
    st.subheader("🔄 Atualizacao de Dados")
    st.caption(
        "Controle de versao das bases (populacao, malha viaria, POIs...), "
        "parametros ferroviarios editaveis e calculos de custo social."
    )

    # ----- Carrega/garante metadata e rail_params -----
    if "_metadata" not in st.session_state:
        st.session_state._metadata = metadata_manager.load_metadata()
    if "_rail_params" not in st.session_state:
        st.session_state._rail_params = rail_params.load_rail_params()

    sub_tab1, sub_tab2, sub_tab3, sub_tab4, sub_tab5 = st.tabs([
        "📋 Bases",
        "👥 Populacao",
        "📈 Geracao de viagens",
        "🚂 Ferroviario",
        "💰 Tempo x Custo",
    ])

    # ===== SUB 1: BASES =====
    with sub_tab1:
        st.markdown("##### Bases controladas")
        meta = st.session_state._metadata

        # Avalia status atual de cada base
        rows = []
        for b in meta.get("bases", []):
            status_eval = metadata_manager.evaluate_freshness(b) if b.get("data_ultima_atualizacao") else b.get("status", "pendente")
            rows.append({
                "ID": b["id"],
                "Base": b["nome"],
                "Fonte": b["fonte"],
                "Ano": b.get("ano", "—") or "—",
                "Ultima atualizacao": b.get("data_ultima_atualizacao") or "—",
                "Validade (anos)": b.get("validade_anos", "—"),
                "Responsavel": b.get("responsavel", "") or "—",
                "Status": metadata_manager.STATUS_LABELS.get(status_eval, status_eval),
                "Arquivo": b.get("arquivo", "") or "—",
            })
        df_meta = pd.DataFrame(rows)
        st.dataframe(df_meta, use_container_width=True, hide_index=True)

        st.markdown("##### Acoes")
        col_act1, col_act2, col_act3 = st.columns(3)
        with col_act1:
            sel_id = st.selectbox(
                "Base", options=[b["id"] for b in meta["bases"]],
                format_func=lambda i: next(
                    (b["nome"] for b in meta["bases"] if b["id"] == i), i
                ),
                key="sel_base_meta",
            )
        with col_act2:
            sel_resp = st.text_input("Responsavel (opcional)", "", key="resp_meta")
        with col_act3:
            st.markdown("&nbsp;")
            if st.button("✅ Marcar como atualizado",
                         use_container_width=True, key="btn_meta_update"):
                metadata_manager.mark_as_updated(sel_id, sel_resp)
                st.session_state._metadata = metadata_manager.load_metadata()
                st.success(f"Base '{sel_id}' marcada como atualizada hoje.")
                st.rerun()

        col_act4, col_act5 = st.columns(2)
        with col_act4:
            if st.button("🔍 Verificar dados disponiveis",
                         use_container_width=True, key="btn_meta_verify"):
                checks = []
                for b in meta["bases"]:
                    arq = b.get("arquivo", "")
                    if arq:
                        # checa se algum arquivo do padrao existe
                        from pathlib import Path as _P
                        demo = _P("data/demo_matias_barbosa")
                        found = list(demo.glob(arq.split(",")[0].strip())) if arq else []
                        checks.append(f"- {'✅' if found else '⚠️'} {b['nome']}: "
                                      f"{len(found)} arquivo(s) encontrado(s)")
                    else:
                        checks.append(f"- ℹ️ {b['nome']}: sem arquivo fixo")
                st.info("\n".join(checks))
        with col_act5:
            if st.button("🔁 Recalibrar modelo com dados atualizados",
                         use_container_width=True, key="btn_meta_recal"):
                st.session_state.base_graph = None
                st.session_state.od_result = None
                if "assignment_result" in st.session_state:
                    del st.session_state.assignment_result
                st.success("Modelo invalidado. Recalcule matriz O-D e cenarios.")

    # ===== SUB 2: POPULACAO =====
    with sub_tab2:
        st.markdown("##### Bases populacionais")
        st.caption("Aceita CSV com colunas: zona, populacao")

        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("**IPEA 2010**")
            up_2010 = st.file_uploader(
                "Carregar populacao 2010", type=["csv"], key="up_pop_2010",
            )
            if up_2010:
                try:
                    df_up = pd.read_csv(up_2010)
                    dest = population_loader.population_file_path(2010)
                    df_up.to_csv(dest, index=False, encoding="utf-8")
                    metadata_manager.mark_as_updated("populacao_ipea_2010")
                    st.success(f"Salvo em {dest.name}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Falha: {exc}")
        with col_p2:
            st.markdown("**IBGE 2022**")
            up_2022 = st.file_uploader(
                "Carregar populacao 2022", type=["csv"], key="up_pop_2022",
            )
            if up_2022:
                try:
                    df_up = pd.read_csv(up_2022)
                    dest = population_loader.population_file_path(2022)
                    df_up.to_csv(dest, index=False, encoding="utf-8")
                    metadata_manager.mark_as_updated("populacao_ibge_2022")
                    st.success(f"Salvo em {dest.name}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Falha: {exc}")

        pop_2010 = population_loader.load_population_demo(2010)
        pop_2022 = population_loader.load_population_demo(2022)

        if pop_2010 is None and pop_2022 is None:
            st.info("📂 Nenhuma base populacional carregada ainda. "
                    "Use os uploaders acima.")
        else:
            if pop_2022 is None:
                st.warning("⚠️ Base populacional 2022 nao encontrada. "
                           "O modelo utilizara populacao 2010 ou pesos manuais.")
            elif pop_2010 is None:
                st.info("ℹ️ Base populacional 2010 nao encontrada. "
                        "Comparacao 2010 vs 2022 indisponivel.")

            df_cmp = population_loader.compare_populations(pop_2010, pop_2022)
            st.markdown("##### Comparativo populacional")
            st.dataframe(df_cmp, use_container_width=True, hide_index=True)

    # ===== SUB 3: GERACAO DE VIAGENS =====
    with sub_tab3:
        st.markdown("##### Geracao de viagens")
        st.caption(
            "Calibre os pesos de geracao das zonas a partir de populacao "
            "IPEA 2010, IBGE 2022 ou manualmente."
        )
        pop_2010 = population_loader.load_population_demo(2010)
        pop_2022 = population_loader.load_population_demo(2022)
        options = ["Manter pesos manuais"]
        if pop_2010 is not None: options.append("Populacao IPEA 2010")
        if pop_2022 is not None: options.append("Populacao IBGE 2022")
        if pop_2010 is not None and pop_2022 is not None:
            options.append("Media ponderada 2010+2022")

        opc = st.radio("Fonte de calibracao:", options, key="rad_calib_pop")

        if st.button("🔁 Calibrar geracao de viagens",
                     type="primary", use_container_width=True, key="btn_calib_pop"):
            base_df = None
            if opc == "Populacao IPEA 2010":
                base_df = pop_2010
            elif opc == "Populacao IBGE 2022":
                base_df = pop_2022
            elif opc.startswith("Media"):
                # Mescla simples: media entre 2010 e 2022
                merged = pop_2010.set_index("zona")["populacao"].rename("p10").to_frame()
                merged["p22"] = pop_2022.set_index("zona")["populacao"]
                merged["populacao"] = merged.mean(axis=1).round(0).astype(int)
                base_df = merged.reset_index()[["zona", "populacao"]]
            if base_df is not None:
                st.session_state.zonas_df = population_loader.calibrate_weights_from_population(
                    st.session_state.zonas_df, base_df
                )
                st.session_state.calibration_source = opc
                st.success(
                    f"✅ Pesos de geracao recalibrados com a base selecionada: **{opc}**. "
                    "Confira a tabela na aba 🔢 Matriz O-D."
                )

        if "calibration_source" in st.session_state:
            st.info(f"📌 Ultima calibracao: **{st.session_state.calibration_source}**")

    # ===== SUB 4: FERROVIARIO =====
    with sub_tab4:
        st.markdown("##### Dados ferroviarios (editaveis)")
        rp = st.session_state._rail_params

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            rp["velocidade_media_kmh"] = st.number_input(
                "Velocidade media do trem (km/h)",
                value=float(rp.get("velocidade_media_kmh", 55.0)),
                min_value=10.0, max_value=200.0, step=5.0,
            )
        with col_f2:
            rp["fator_operacional_bloqueio"] = st.number_input(
                "Fator operacional de bloqueio",
                value=float(rp.get("fator_operacional_bloqueio", 2.0)),
                min_value=1.0, max_value=10.0, step=0.1,
            )
        with col_f3:
            rp["passagens_por_dia"] = st.number_input(
                "Passagens por dia",
                value=float(rp.get("passagens_por_dia", 8.0)),
                min_value=0.0, max_value=200.0, step=1.0,
            )

        st.markdown("##### Trens (edite para refletir a operacao local)")
        df_trens = pd.DataFrame(rp.get("trens", []))
        edited_trens = st.data_editor(
            df_trens, num_rows="dynamic", use_container_width=True,
            key="ed_trens",
        )
        rp["trens"] = edited_trens.to_dict("records")

        st.markdown("##### Calculo de bloqueio")
        df_block = pd.DataFrame(rail_params.compute_blocking_table(rp))
        st.dataframe(df_block, use_container_width=True, hide_index=True)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("💾 Salvar parametros ferroviarios",
                         type="primary", use_container_width=True,
                         key="btn_save_rail"):
                rail_params.save_rail_params(rp)
                metadata_manager.mark_as_updated("dados_ferroviarios")
                st.success("Parametros salvos em rail_parameters.json")
                st.rerun()
        with col_b2:
            if st.button("↩️ Restaurar parametros padrao",
                         use_container_width=True, key="btn_reset_rail"):
                st.session_state._rail_params = rail_params.reset_to_default()
                st.success("Parametros restaurados ao padrao")
                st.rerun()

    # ===== SUB 5: TEMPO x CUSTO =====
    with sub_tab5:
        st.markdown("##### Tempo x Custo Social")
        st.caption(
            "Estima atraso e custo social do bloqueio ferroviario com base "
            "nos parametros configurados."
        )
        rp = st.session_state._rail_params

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            rp["valor_tempo_pessoa_hora"] = st.number_input(
                "Valor do tempo (R$/pessoa/hora)",
                value=float(rp.get("valor_tempo_pessoa_hora", 25.0)),
                min_value=0.0, step=1.0,
            )
            rp["ocupacao_media_veiculo"] = st.number_input(
                "Ocupacao media por veiculo (pessoas)",
                value=float(rp.get("ocupacao_media_veiculo", 1.5)),
                min_value=0.1, step=0.1,
            )
        with col_c2:
            rp["fluxo_afetado_por_bloqueio"] = st.number_input(
                "Fluxo afetado por bloqueio (veiculos)",
                value=float(rp.get("fluxo_afetado_por_bloqueio", 80)),
                min_value=0.0, step=10.0,
            )
            rp["dias_por_ano"] = st.number_input(
                "Dias operacionais por ano",
                value=int(rp.get("dias_por_ano", 365)),
                min_value=1, max_value=366, step=1,
            )

        if st.button("💾 Salvar parametros de custo",
                     use_container_width=True, key="btn_save_cost"):
            rail_params.save_rail_params(rp)
            metadata_manager.mark_as_updated("parametros_tempo_custo")
            st.success("Parametros salvos")

        st.markdown("##### Estimativa de impacto")
        res = rail_params.compute_social_cost(rp)
        col_r1, col_r2, col_r3 = st.columns(3)
        with col_r1:
            st.metric("Pessoas/bloqueio", f"{res['pessoas_afetadas_por_bloqueio']:.0f}")
            st.metric("Horas perdidas/bloqueio", f"{res['horas_perdidas_por_bloqueio']:.2f}")
        with col_r2:
            st.metric("Custo/bloqueio", f"R$ {res['custo_por_bloqueio_R$']:.2f}")
            st.metric("Custo diario", f"R$ {res['custo_diario_R$']:.2f}")
        with col_r3:
            st.metric("Custo anual", f"R$ {res['custo_anual_R$']:.2f}")
            st.metric("Atraso anual (horas)", f"{res['atraso_anual_horas']:.0f}")

        st.warning(
            "⚠️ **Valores exploratorios** que dependem de calibracao com "
            "dados locais (contagens, pesquisas O-D, valor do tempo regional)."
        )
        st.session_state._social_cost = res

    # ===== Evolucoes futuras =====
    st.divider()
    with st.expander("🚀 Evolucoes futuras de simulacao"):
        st.markdown(
            "Em versoes futuras, este simulador pode ser integrado a "
            "ferramentas abertas mais avancadas:"
        )
        for item in advanced_assignment.FUTURE_INTEGRATIONS:
            st.markdown(
                f"- **[{item['nome']}]({item['url']})** "
                f"({item['complexidade']}) — {item['descricao']}  \n"
                f"  Status atual: *{item['status_no_prototipo']}*"
            )
        st.info(
            "Estas integracoes **nao sao dependencias obrigatorias** "
            "da versao atual. A arquitetura ja preve placeholders em "
            "`modules/advanced_assignment.py`."
        )


# ---------------------------------------------------------------------------
# RODAPE
# ---------------------------------------------------------------------------
st.divider()
st.markdown(
    f"""
    <div style='text-align:center; color:#777; font-size:0.85rem;
                padding: 16px 12px; border-top: 1px solid rgba(255,255,255,0.06);'>
        Disciplina de Planejamento de Transportes &middot; <b>IME</b> &middot;
        Prototipo academico &middot; {datetime.now().year}<br>
        Desenvolvido por <b>Luiz Araujo de Souza Junior</b> &middot;
        <a href='mailto:luiz.junior@ime.eb.br' style='color:#9C27B0;
            text-decoration:none;'>luiz.junior@ime.eb.br</a>
    </div>
    """,
    unsafe_allow_html=True,
)
