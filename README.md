# Rodovias, Ferrovias e Mobilidade Urbana em Municipios de Pequeno Porte
## Estudo de Caso: Matias Barbosa / MG

Prototipo web interativo desenvolvido para a disciplina de **Planejamento de
Transportes (IME)**. Permite carregar a area de estudo, zonas analiticas, malha
viaria, linha ferrea, rodovias e pontos de interesse, alem de simular
intervencoes (viadutos, pontes, novas conexoes) e gerar relatorios.

O estudo de caso vem pre-carregado com dados aproximados de **Matias Barbosa /
MG**, mas o sistema e generico e aceita arquivos KMZ / KML / GeoJSON / CSV para
estudos em outras localidades.

---

## 🧱 Stack utilizada

- **Python 3.10+**
- **Streamlit** (interface web)
- **Folium + streamlit-folium** (mapa interativo)
- **GeoPandas / Shapely / Fiona** (dados geograficos)
- **NetworkX** (grafo viario / cenarios)
- **OSMnx** (opcional - baixar malha real do OpenStreetMap)
- **Plotly** (graficos)

---

## 📁 Estrutura do projeto

```
.
├── app.py                       # aplicacao principal Streamlit
├── requirements.txt
├── README.md
├── data/
│   ├── sample/                  # dados iniciais sinteticos
│   │   ├── area_estudo.geojson
│   │   ├── zonas.geojson
│   │   ├── ferrovia.geojson
│   │   ├── rodovias.geojson
│   │   ├── pontos_viaduto.geojson
│   │   └── pontos_interesse.geojson
│   └── uploads/                 # arquivos enviados pelo usuario na sessao
└── modules/
    ├── config.py                # cores, constantes, listas
    ├── data_loader.py           # leitura de arquivos
    ├── kmz_utils.py             # leitura de KML/KMZ
    ├── map_utils.py             # construcao do mapa Folium
    ├── od_matrix.py             # modelo gravitacional O-D
    ├── network_analysis.py      # grafo + OSMnx
    ├── scenario_analysis.py     # cenarios e indicadores
    └── report_generator.py      # relatorio .md/.txt/.html
```

---

## ⚙️ Instalacao

> Recomenda-se Python 3.10+ e um ambiente virtual.

### 1. Criar ambiente virtual

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

> **Dica Windows:** `geopandas`, `fiona` e `shapely` podem exigir instalacao
> via `pipwin` ou wheels do Christoph Gohlke se o `pip` reclamar. Em
> distribuicoes recentes (>= 3.10) a instalacao direta costuma funcionar.

### 3. (Opcional) Habilitar OSMnx

`osmnx` so e usado se voce quiser baixar a malha viaria real do
OpenStreetMap. Quando indisponivel, o sistema cai num grafo sintetico baseado
nos centroides das zonas + pontos de viaduto, e tudo continua funcionando
offline.

---

## ▶️ Como rodar

Na raiz do projeto, com o ambiente virtual ativo:

```bash
streamlit run app.py
```

O Streamlit abrira automaticamente o navegador em
`http://localhost:8501`.

---

## 🗺️ Funcionalidades

### Aba **Mapa**
- Base **OpenStreetMap**, alternancia para **Satelite (Esri)** e **Mapa Claro**.
- Zoom inicial em Matias Barbosa / MG.
- Camadas ativaveis/desativaveis pela barra lateral.
- Controle de medicao e mini-mapa.
- Indicadores rapidos: numero de zonas, viadutos, POIs, cenarios.

### Aba **Importar Arquivos**
Formatos aceitos:
- **GeoJSON** (`.geojson`, `.json`)
- **KML** (`.kml`)
- **KMZ** (`.kmz`) - descompactado automaticamente
- **CSV** com as colunas: `nome, tipo, latitude, longitude, descricao`

As camadas importadas aparecem no mapa e podem ser removidas a qualquer momento.

### Aba **Pontos / Edicao**
- Cadastro de pontos com categoria (Estudo de viaduto, Travessia critica,
  Ponte/Viaduto proposto, Escola, Comercio, Industria, Terminal/Parada, Outro).
- Tabela editavel dos pontos cadastrados.
- Exportacao em CSV.
- Dica: clique no mapa para ver as coordenadas e cole-as no formulario.

### Aba **Matriz O-D**
- Tabela editavel de zonas (geracao, atracao, populacao).
- Modelo gravitacional: $T_{ij} = (G_i \\cdot A_j) / d_{ij}^{\\beta}$.
- Parametro **β** ajustavel (atrito da distancia).
- Distancia entre centroides das zonas (haversine).
- Normalizacao percentual.
- Graficos de viagens geradas e atraidas por zona.
- Camada de **linhas de fluxo** no mapa, com espessura proporcional ao fluxo.

### Aba **Cenarios**
Tipos suportados:
- Cenario atual (referencia)
- Cenario com viaduto
- Cenario com ponte
- Cenario com nova ligacao viaria
- Cenario com bloqueio/restricao

Para cada cenario voce escolhe dois nos do grafo (centroides Z1..Z4 e pontos de
viaduto V1..V4) e um **fator de impedancia** (`<1` reduz custo, `>1`
representa restricao). Tambem e possivel marcar a aresta como bloqueio.

### Aba **Comparacao**
- Tabela comparativa com **distancia media**, **tempo medio estimado**,
  **n. zonas conectadas**, **reducao percentual de percurso** e **observacao
  tecnica automatica**.
- Graficos comparativos.
- Identificacao automatica do **cenario mais vantajoso**.

### Aba **Relatorio**
- Resumo textual com area de estudo, zonas, pontos, matriz O-D resumida,
  cenarios e cenario mais vantajoso.
- Download em **.md**, **.txt** e **.html**.

---

## 🧩 Como substituir os dados sinteticos por arquivos reais

Voce tem duas opcoes:

### Opcao A - manter os dados como **uploads de sessao**
Va na aba **Importar Arquivos** e envie seu `.kmz` / `.kml` / `.geojson`. Os
dados ficam ativos enquanto a sessao do Streamlit estiver aberta.

### Opcao B - substituir os arquivos de exemplo
Substitua os arquivos dentro de `data/sample/` mantendo os mesmos nomes:

```
data/sample/area_estudo.geojson
data/sample/zonas.geojson
data/sample/ferrovia.geojson
data/sample/rodovias.geojson
data/sample/pontos_viaduto.geojson
data/sample/pontos_interesse.geojson
```

Para `zonas.geojson`, preserve as propriedades:
- `zona` (Z1, Z2, Z3, Z4...)
- `nome`
- `tipo`
- `geracao` (peso de geracao de viagens)
- `atracao` (peso de atracao)
- `populacao`
- `observacoes`

Para os pontos, mantenha pelo menos: `nome`, `categoria`, `descricao`.

---

## 🚀 Como evoluir o prototipo

Sugestoes:

1. **Integrar OSMnx real:** baixar a malha viaria de Matias Barbosa e
   substituir o grafo sintetico do modulo `network_analysis.py`.
2. **Alocacao em rede:** distribuir as viagens da matriz O-D nos arcos viarios
   e gerar mapas de carga.
3. **Calibracao real:** alimentar `geracao` e `atracao` com dados do
   IBGE/contagens de campo.
4. **Cenarios multi-modais:** acrescentar transporte coletivo / ciclovias.
5. **Camadas socioeconomicas:** densidade demografica, renda, uso do solo.
6. **Exportacao GIS:** salvar cenarios em Shapefile/GeoPackage para QGIS/ArcGIS.
7. **Acessibilidade:** indicador isocronico (areas alcancaveis em N minutos).

---

## ⚠️ Limitacoes

- Os dados pre-carregados sao **aproximacoes analiticas** para fins
  demonstrativos.
- O modelo gravitacional e simplificado, usa distancia haversine entre
  centroides e nao representa capacidade viaria nem congestionamento.
- As intervencoes alteram o grafo no nivel logico - nao ha modelagem detalhada
  de geometria de viaduto/ponte.
- Sem calibracao com contagens de trafego reais.

> Este prototipo utiliza zoneamento analitico e dados simplificados para apoio
> ao planejamento, **nao substituindo** levantamento de campo, projeto
> executivo ou modelagem de trafego detalhada.

---

## 📜 Licenca / Uso

Material academico desenvolvido para a disciplina de Planejamento de
Transportes do **IME**. Uso livre para fins de estudo e demonstracao.
