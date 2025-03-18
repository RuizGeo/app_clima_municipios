# Importar as bibliotecas
import pandas as pd
import geopandas as gpd
import json
import requests
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st

import folium
from streamlit_folium import st_folium
import datetime
import plotly.express as px
import plotly.graph_objects as go

import matplotlib.colors as mcolors

st.set_page_config(layout="wide",page_title="Análise Climática por Município")  # Permite usar toda a largura da tela




def obter_shapefile_municipios(cod_uf):
    
    # URL para municípios (v4 da API)
    url = f"https://servicodados.ibge.gov.br/api/v4/malhas/estados/{cod_uf}?formato=application/json&intrarregiao=Municipio&qualidade=intermediaria"
    # Obtendo acesso a URL
    response = requests.get(url) #  Envia uma requisição HTTP GET para a url.
    # Verificar se
    if response.status_code == 200: #  Se for 200, significa que os dados foram baixados corretamente

        municipios  = gpd.read_file(response.text)# contém os dados retornados pela URL, que devem estar em um formato compatível com geopandas, como GeoJSON,
        
        return municipios
    
    else:
        print("Erro:", response.status_code, response.text)  # Debug detalhado


def obter_municipios_por_estado(uf: str):
    """
    Obtém a lista de municípios de um estado específico com códigos IBGE
    
    Parâmetros:
    uf (str): Sigla da UF (ex: 'SP', 'RJ', 'MG')
    
    Retorna:
    DataFrame com colunas: ['codigo_ibge', 'municipio', 'uf']
    """
    url = f"https://servicodados.ibge.gov.br/api/v1/localidades/estados/{uf}/municipios"
    
    response = requests.get(url)
    
    if response.status_code == 200:
        dados = response.json()
        
        municipios = [{
            'codigo_ibge': mun['id'],
            'municipio': mun['nome'],
            'uf': uf.upper()
        } for mun in dados]
        
        return pd.DataFrame(municipios)
        
    else:
        print(f"Erro {response.status_code}: {response.text}")
        return pd.DataFrame()

# Título do APP
st.title("🌍 Análise da Temperatura e da Precipitação por Município")
st.markdown("Explore os dados climáticos de temperatura e precipitação de diferentes municípios de forma interativa. 📊🌦️")
# Parâmetros
uf = 'MT'
# Dicionários de códigos IBGE
dict_uf = {'MT':'51', 'SP':'35', 'RJ':'33', 'MG':'31', 'AM':'13', 'PA':'15'
           , 'BA':'29', 'RS':'43', 'PR':'41', 'SC':'42', 'GO':'52', 'MS':'50'
           , 'TO':'17', 'RO':'11', 'AC':'12', 'RR':'14', 'AP':'16', 'MA':'21'
           , 'PI':'22', 'CE':'23', 'RN':'24', 'PB':'25', 'PE':'26', 'AL':'27'
           , 'SE':'28', 'DF':'53', 'ES':'32'}

# Criando um selectbox para escolher a cidade
uf_selecionado = st.sidebar.selectbox("Escolha o Estado:",dict_uf.keys())
# Obter o shapefile
gdf = obter_shapefile_municipios(dict_uf[uf_selecionado])

# Setar o CRS
gdf = gdf.set_crs(epsg=4674)

# Exemplo de uso:
df_mun = obter_municipios_por_estado(uf_selecionado)

# nomes municípios
municipios = df_mun['municipio'].values
# Para criar um dicionário de código -> nome:
dict_mun = dict(zip(df_mun['codigo_ibge'], df_mun['municipio']))

# Criando um selectbox para escolher a cidade
cidade_selecionada = st.sidebar.selectbox("Escolha uma cidade:", df_mun['municipio'])

# Selecionar o código IBGE da cidade a partir da cidade_selecionada
geocod = str(df_mun[df_mun['municipio'] == cidade_selecionada]['codigo_ibge'].to_list()[0])

# Selecionar o GeoDataFrame
gdf = gdf[gdf.codarea == geocod]
# Obter as coordenadas
long_x = gdf.geometry.centroid.x.values[0]
lat_y = gdf.geometry.centroid.y.values[0]

# Criar o mapa com Folium
mapa = folium.Map(location=[lat_y, long_x], zoom_start=10)

# Exibir no Streamlit
st.header("Município selecionado")

# Adicionar a camada de Imóveis Rurais
folium.GeoJson(
    data=gdf,  # GeoDataFrame convertido diretamente em GeoJson
    name = 'Município',  # Nome da camada no LayerControl
    tooltip=folium.GeoJsonTooltip(  # Configurar tooltip
        fields=['codarea'],  # Coluna(s) para mostrar no tooltip
        aliases=['Código município: '],  # Nomes amigáveis no tooltip
        localize=True
    ),
    style_function=lambda x: {
        'fillColor': 'white',  # Cor de preenchimento
        'color': 'black',       # Cor das bordas
        'weight': 1,            # Largura das bordas
        'fillOpacity': 0.6      # Opacidade do preenchimento
    }
).add_to(mapa)
# Adicionar Folium
st_folium(mapa, use_container_width=True, height=500)


# Definir data mínima e máxima
start_date = datetime.date(2020, 1, 1)
end_date = datetime.date(2025, 2, 28)

# Obtendo as datas de início e fim
# Criar o seletor de intervalo de datas no sidebar
data_range = st.sidebar.date_input(
    "Selecione o intervalo de datas:",
    value=(start_date, end_date),
    min_value=start_date,
    max_value=datetime.date(2025, 12, 31),
)

# Verificar se o usuário selecionou um intervalo válido
if isinstance(data_range, tuple) and len(data_range) == 2:
    start_date = data_range[0].strftime("%Y%m%d")  # Exemplo: '20240101'
    end_date = data_range[1].strftime("%Y%m%d")  # Exemplo: '20240131'

    # Exibir as datas formatadas
    st.sidebar.write(f"**Data de Início:** {start_date}")
    st.sidebar.write(f"**Data de Fim:** {end_date}")


    # Definir os parâmetros do EndPoint
    variavel = 'PRECTOTCORR,T2M'#,RH2M,T2M_MAX,T2M_MIN,T2M,QV2M'
    # URL NASA Power
    endpoint_nasa_power = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters={variavel}&community=SB&longitude={long_x}&latitude={lat_y}&start={start_date}&end={end_date}&format=JSON"

    # Aplicar a requisição e obter o conteúdo
    req_power = requests.get(endpoint_nasa_power).content

    # Carregar o conteúdo como json
    json_power = json.loads(req_power)

    # Converter json para DataFrame
    df = pd.DataFrame(json_power['properties']['parameter'])

    # renomear colunas
    df.rename(columns = {'PRECTOTCORR':'prec','T2M':'temp'},inplace=True)

    #@title Agrupar os dados por ano e mês
    # Convertendo o índice para datetime
    df.index = pd.to_datetime(df.index)
    
    # Extrair o mês
    df['month'] = df.index.month
    # Extrair o ano
    df['year'] = df.index.year
    # Calcular a média dos dados por ano e mês
    df_mean = df.groupby(['year', 'month']).mean()
    # Calcular o desvio padrão dos dados por ano e mês
    df_std = df.groupby(['year', 'month']).std()
    # Calcular a suma dos dados por ano e mês
    df_sum = df.groupby(['year', 'month']).sum()


    #@title Plotar o gráfico do comportamento da Precipitação (Ano e Mês)
    # Transformar índices em colunas
    dfp = df_sum.reset_index()


    # Criar a paleta do Seaborn e converter para hex
    paleta_seaborn = sns.light_palette("blue", n_colors=dfp["year"].nunique(), as_cmap=False)
    paleta_plotly = [mcolors.to_hex(color) for color in paleta_seaborn]


    # Criar o gráfico com Plotly
    fig = px.line(
        dfp, x="month", y="prec", color="year",
        markers=True, title="Precipitação Mensal por Ano",
        labels={"month": "Mês", "prec": "Precipitação acumulada", "year": "Ano"},
        color_discrete_sequence=px.colors.sequential.Blues  # Usando a paleta do Plotly

        # Suaviza a linha
    )

    # Melhorar layout do gráfico
    fig.update_layout(
        xaxis=dict(title="Mês",
            tickmode="array",
            tickvals=list(range(1, 13)),  # Posições dos meses
            ticktext=["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]  # Nomes dos meses
        ),
        yaxis=dict(title="Precipitação acumulada (mm/dia)"),
        legend_title="Ano",
        template="plotly_white"
    )

    # Exibir no Streamlit
    st.plotly_chart(fig)

    #@title Plotar o gráfico do comportamento da Temperatura(Ano e Mês)
    # Transformar índices em colunas
    dft = df_mean.reset_index()


    # Criar a paleta do Seaborn e converter para hex
    paleta_seaborn = sns.light_palette("blue", n_colors=dft["year"].nunique(), as_cmap=False)
    paleta_plotly = [mcolors.to_hex(color) for color in paleta_seaborn]


    # Criar o gráfico com Plotly
    fig = px.line(
        dft, x="month", y="temp", color="year",
        markers=True, title="Temperatura média Mensal por Ano",
        labels={"month": "Mês", "prec": "Precipitação", "year": "Ano"},
        color_discrete_sequence=px.colors.sequential.Reds  # Usando a paleta do Plotly

        # Suaviza a linha
    )

    # Melhorar layout do gráfico
    fig.update_layout(
        xaxis=dict(title="Mês",
            tickmode="array",
            tickvals=list(range(1, 13)),  # Posições dos meses
            ticktext=["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]  # Nomes dos meses
        ),
        yaxis=dict(title="Temperatura média (°C)"),
        legend_title="Ano",
        template="plotly_white"
    )

    # Exibir no Streamlit
    st.plotly_chart(fig)
        
else:
    st.sidebar.warning("Por favor, selecione um intervalo válido de datas.")





 





