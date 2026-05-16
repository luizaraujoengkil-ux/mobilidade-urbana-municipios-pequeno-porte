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
    "Travessia critica",
    "Ponte proposta",
    "Viaduto proposto",
    "Escola",
    "Comercio",
    "Industria",
    "Terminal/Parada",
    "Outro",
]

DISCLAIMER = (
    "Este prototipo utiliza zoneamento analitico e dados simplificados para "
    "apoio ao planejamento, nao substituindo levantamento de campo, projeto "
    "executivo ou modelagem de trafego detalhada."
)
