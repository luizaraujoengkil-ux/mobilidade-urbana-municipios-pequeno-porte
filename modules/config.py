"""Configuracoes globais e constantes do prototipo."""

# Centro aproximado de Matias Barbosa/MG
MATIAS_BARBOSA_CENTER = (-21.8722, -43.3122)
DEFAULT_ZOOM = 14

# Paleta de cores das zonas e camadas
COLORS = {
    "Z1": "#B83DBA",   # magenta/roxo - centro
    "Z2": "#F4A261",   # laranja claro - sudeste
    "Z3": "#F2D544",   # amarelo - residencial dispersa
    "Z4": "#E63946",   # vermelho - industrial
    "trem": "#1D6FE0",        # azul - linha ferrea
    "uniao_industria": "#C92A2A",  # vermelho - Uniao Industria
    "viaduto_estudo": "#2ECC71",   # verde - pontos de estudo
    "br040": "#7B4B2A",       # marrom - BR-040
    "mg353": "#A06A3F",       # marrom claro - MG-353
    "area_estudo": "#3A3A3A", # cinza forte - contorno
    "malha_viaria": "#888888",
    "fluxo": "#FF6B35",
}

ZONE_TYPES = {
    "Z1": "Centro / Nucleo urbano",
    "Z2": "Area urbana sudeste",
    "Z3": "Area residencial dispersa",
    "Z4": "Area industrial / logistica",
}

POINT_CATEGORIES = [
    "Estudo de viaduto",
    "Viaduto proposto",
    "Ponte proposta",
    "Passagem inferior de nivel",
    "Passagem superior de nivel",
    "Passagem em nivel",
    "Travessia critica",
    "Nova ligacao viaria",
    "Acesso a rodovia",
    "Escola",
    "Hospital",
    "Posto de saude",
    "Prefeitura",
    "Comercio",
    "Industria",
    "Terminal/Parada",
    "Estacao ferroviaria",
    "Outro",
]

# Tipos / funcoes editaveis no assistente
VIA_TYPES = [
    "Rodovia federal",
    "Rodovia estadual",
    "Avenida urbana",
    "Estrada municipal",
    "Eixo historico",
    "Eixo industrial/logistico",
    "Outro",
]

VIA_FUNCOES = [
    "ligacao regional",
    "acesso ao centro",
    "corredor industrial",
    "ligacao intermunicipal",
    "travessia urbana",
    "outro",
]

EIXO_TYPES = [
    "Linha ferrea",
    "Rodovia urbana",
    "Avenida arterial",
    "Corredor de transporte coletivo",
    "Rio/canal",
    "Barreira fisica",
    "Outro",
]

EIXO_IMPACTOS = [
    "efeito barreira",
    "conflito viario",
    "travessia critica",
    "acessibilidade reduzida",
    "integracao regional",
    "outro",
]

ZONA_TIPOS = [
    "Centro / nucleo urbano",
    "Residencial",
    "Comercial / servicos",
    "Industrial / logistico",
    "Rural / periurbano",
    "Equipamentos publicos",
    "Misto",
    "Outro",
]

ZONA_FUNCAO_OD = [
    "predominantemente origem",
    "predominantemente destino",
    "origem e destino",
]

# Cores sugeridas por tipo de zona (usuario pode sobrescrever)
ZONA_COLOR_BY_TIPO = {
    "Centro / nucleo urbano":     "#B83DBA",   # roxo/magenta
    "Residencial":                "#F2D544",   # amarelo
    "Comercial / servicos":       "#64B5F6",   # azul claro
    "Industrial / logistico":     "#E63946",   # vermelho
    "Rural / periurbano":         "#43A047",   # verde
    "Equipamentos publicos":      "#7E57C2",   # roxo claro
    "Misto":                      "#F4A261",   # laranja
    "Outro":                      "#9E9E9E",   # cinza
}

POI_IMPORTANCIA = ["baixa", "media", "alta", "critica"]

# Categorias que representam intervencoes de infraestrutura -
# pontos com essas categorias viram nos do grafo de analise (selecionaveis em Cenarios)
INFRA_CATEGORIES = {
    "Estudo de viaduto",
    "Viaduto proposto",
    "Ponte proposta",
    "Passagem inferior de nivel",
    "Passagem superior de nivel",
    "Passagem em nivel",
    "Travessia critica",
    "Nova ligacao viaria",
}

# Cores e icones por categoria de ponto (Folium / mapa)
CATEGORY_STYLE = {
    "Estudo de viaduto":         {"color": "green",     "icon": "star",          "marker": "#2ECC71"},
    "Viaduto proposto":          {"color": "darkgreen", "icon": "road",          "marker": "#1B5E20"},
    "Ponte proposta":            {"color": "blue",      "icon": "anchor",        "marker": "#1565C0"},
    "Passagem inferior de nivel":{"color": "orange",    "icon": "arrow-down",    "marker": "#EF6C00"},
    "Passagem superior de nivel":{"color": "darkgreen", "icon": "arrow-up",      "marker": "#1B5E20"},
    "Passagem em nivel":         {"color": "red",       "icon": "warning-sign",  "marker": "#C62828"},
    "Travessia critica":         {"color": "red",       "icon": "exclamation-sign","marker": "#D32F2F"},
    "Nova ligacao viaria":       {"color": "purple",    "icon": "random",        "marker": "#7B1FA2"},
    "Escola":                    {"color": "blue",      "icon": "graduation-cap","marker": "#1976D2"},
    "Comercio":                  {"color": "green",     "icon": "shopping-cart", "marker": "#388E3C"},
    "Industria":                 {"color": "darkred",   "icon": "industry",      "marker": "#B71C1C"},
    "Terminal/Parada":           {"color": "orange",    "icon": "bus",           "marker": "#F57C00"},
    "Outro":                     {"color": "gray",      "icon": "info-sign",     "marker": "#757575"},
    # POIs adicionais
    "Hospital":                  {"color": "red",       "icon": "plus-sign",     "marker": "#D32F2F"},
    "Posto de saude":            {"color": "lightred",  "icon": "plus-sign",     "marker": "#EF5350"},
    "Prefeitura":                {"color": "purple",    "icon": "home",          "marker": "#6A1B9A"},
    "Estacao ferroviaria":       {"color": "darkblue",  "icon": "train",         "marker": "#283593"},
    "Acesso a rodovia":          {"color": "cadetblue", "icon": "road",          "marker": "#1565C0"},
}

DISCLAIMER = (
    "Este prototipo utiliza zoneamento analitico e dados simplificados para "
    "apoio ao planejamento, nao substituindo levantamento de campo, projeto "
    "executivo ou modelagem de trafego detalhada."
)
