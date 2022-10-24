
from dash import Dash, html, dcc, Output, Input, State
import pandas as pd
from dash_extensions.javascript import assign, Namespace
import dash_leaflet as dl
import dash_leaflet.express as dlx

external_stylesheets = ['https://cdn.jsdelivr.net/npm/bootstrap@5.2.1/dist/css/bootstrap.min.css']
chroma = "https://cdnjs.cloudflare.com/ajax/libs/chroma-js/2.1.0/chroma.min.js"

app =Dash(__name__, suppress_callback_exceptions=True, external_stylesheets=external_stylesheets, external_scripts=[chroma], prevent_initial_callbacks=True)

server = app.server# assume you have a "long-form" data frame

colorscale = ['red', 'yellow', 'green', 'blue', 'purple']
color_prop = 'qt_votos_nominais'
#color_prop = 'density'
df_dados = pd.read_csv('data/votacao_candidato.csv',sep=';',encoding=' iso-8859-1')
df_votacao_canditado = df_dados.copy()
#vmax = df[color_prop].max()
#vmax = df_eleicao['qt_votos_nominais'].max()
colorbar = dl.Colorbar(colorscale=colorscale, width=20, height=150, min=0, max=100, unit=' Votos')
#ns = Namespace('dashExtensions', 'default')s

# Geojson rendering logic, must be JavaScript as it is executed in clientside.
point_to_layer = assign("""function(feature, latlng, context){
    const {min, max, colorscale, circleOptions, colorProp} = context.props.hideout;
    const csc = chroma.scale(colorscale).domain([min, max]);  // chroma lib to construct colorscale
    circleOptions.fillColor = csc(feature.properties[colorProp]);  // set color based on color prop.
    return L.circleMarker(latlng, circleOptions);  // sender a simple circle marker.
}""")
cluster_to_layer = assign("""function(feature, latlng, index, context){
    const {min, max, colorscale, circleOptions, colorProp} = context.props.hideout;
    const csc = chroma.scale(colorscale).domain([min, max]);
    
    // Set color based on mean value of leaves.
    const leaves = index.getLeaves(feature.properties.cluster_id, limit=Infinity);	
    let valueSum = 0;
    for (let i = 0; i < leaves.length; ++i) {
        valueSum += leaves[i].properties['qt_votos_nominais']
        console.log('teste de contexto',valueSum)
    }
    const valueMean = valueSum / leaves.length;
    // Render a circle with the number of leaves written in the center.
    const icon = L.divIcon.scatter({
        html: '<div style="background-color:white;"><span>' + valueSum + '</span></div>',
        className: "marker-cluster",
       iconSize: L.point(40, 40),
        color: csc(valueMean)
   });
    return L.marker(latlng, {icon : icon})
}""")
# Create geojson.


def filter_candidates(df_votacao_canditado_func, candidato):
    
    df_votacao_canditado_func = df_votacao_canditado_func[df_votacao_canditado_func["nm_candidato"]==candidato]
    df_votacao_canditado_func =df_votacao_canditado_func[df_votacao_canditado_func["qt_votos_nominais"]>0]
    
    df_votacao_araguina = df_votacao_canditado_func[df_votacao_canditado_func["nm_municipio"]=='ARAGUAÍNA']
    df_votacao_araguina['qt_votos_nominais'] = df_votacao_araguina['qt_votos_nominais'].sum()
    df_votacao_canditado_func = df_votacao_canditado_func[df_votacao_canditado_func["nm_municipio"]!='ARAGUAÍNA']
    df_votacao_canditado_func = pd.concat([df_votacao_canditado_func,df_votacao_araguina[df_votacao_araguina['nr_zona']==1]])
    df_cidades = pd.read_json('data/cidades.json')
    df_cidades = df_cidades[df_cidades['codigo_uf']==17]#cidades do tocantins
    df_cidades['nome'] = df_cidades['nome'].apply(lambda x: x.upper())

    df_votacao_canditado_cidades = df_votacao_canditado_func.merge(df_cidades, left_on='nm_municipio', right_on='nome') 
    df_eleicao= df_votacao_canditado_cidades[['nome','latitude','longitude','nm_candidato','sg_partido','qt_votos_nominais','qt_votos_validos' ]]
    
    dict_eleicao = df_eleicao.to_dict('records')
    
    for item in dict_eleicao:
        item["tooltip"] = f"{item['nome']} - {int(item['qt_votos_nominais']) } Votos"
    
    #geojson = dlx.dicts_to_geojson(dicts, lon="lng")  # convert to geojson
    #geobuf = dlx.geojson_to_geobuf(geojson)  # convert to geobuf
    geojson = dlx.dicts_to_geojson(dict_eleicao, lon="longitude", lat='latitude')  # convert to geojson
    geobuf = dlx.geojson_to_geobuf(geojson)  # convert to geobuf
    # Create a colorbar.
    vmax = df_eleicao["qt_votos_nominais"].max()
    colorbar = dl.Colorbar(colorscale=colorscale, width=20, height=150, min=0, max=vmax, unit=' Votos')
    
    # Create geojson.
    geojson = dl.GeoJSON(data=geobuf, id="geojson", format="geobuf",
                        zoomToBounds=True,  # when true, zooms to bounds when data changes
                        cluster=True,  # when true, data are clustered
                        clusterToLayer=cluster_to_layer,  # how to draw clusters
                        zoomToBoundsOnClick=True,  # when true, zooms to bounds of feature (e.g. cluster) on click
                        options=dict(pointToLayer=point_to_layer),  # how to draw points
                        superClusterOptions=dict(radius=200),   # adjust cluster size
                        hideout=dict(colorProp='qt_votos_nominais', circleOptions=dict(fillOpacity=1, stroke=False, radius=20),
                                    min=0, max=100, colorscale=colorscale))
    return  [dl.TileLayer(),geojson, colorbar] 


app.layout = html.Div(children=[
    html.Div([  
        html.Div(
                    [
                        html.Div(
                            [
                                html.H3(
                                    " Eleições 2022 ",
                                    
                                    className="display-4"
                                ),
                                html.H5(
                                    "Primeiro Turno - Tocantins", className="display-6"
                                ),
                                
                            ]
                        )
                    ],
                    className="container",
                    id="title",
                ),
            ],
            id="header",
            className="row align-items-center",
            
        ),
        html.Div([
            html.Div([
                #adiciona, tipo de analise
                html.Div([
                        html.Div([
                                html.Label("Cargo:"),
                                dcc.RadioItems(
                                        id="cargos",
                                        options=[
                                            {"label": "Deputado Estadual ", "value": "Deputado Estadual"},
                                            {"label": "Deputado Federal ", "value": "Deputado Federal"},
                                            {"label": "Governador ", "value": "Governador"},
                                            {"label": "Senador ", "value": "Senador"},
                                            {"label": "Presidente ", "value": "Presidente"},
                                        ],
                                        
                                        labelClassName="form-check-label ",
                                        inputClassName="form-check-input",
                                        className="form-control",	
                                    ),
                                ],
                                className="form-control", ),
                        html.Div([      
                                html.Label("Candidato:"),    
                                dcc.Dropdown(
                                        id='select_candidato',
                                        options=[],
                                        
                                        multi=False,
                                        className="form-control",
                                    ),
                    ],className="form-control"),      
                        html.Div(
                                [
                                    html.Div(
                                        [html.H5("Informações",className="card-title"),
                                        html.H6("Total de votos",className="card-subtitle mb-2 text-muted"),
                                        html.H6("0",id="qtd_votos",className=""), ],
                                    ),
                                ],
                                id="info-container",
                                className="container border",
                            ),
                        html.Div(
                                [
                                    html.Div(
                                        [html.H5("Melhor Votação",className="card-title"),
                                        html.H6("cidade",id="melhor_cidade",className="card-subtitle mb-2 text-muted"),
                                        html.H6("0",id="qtd_votos_cidade"), ],
                                    ),
                                ],
                                
                                className="container border",
                            ),    
                            
                            ], 
                    className="shadow  bg-body rounded",
                    
                ),
            ] ,className="col-md-3"),
            html.Div(
            [               
                html.Div(
                    [
                        
                       html.Div( children=dl.Map(filter_candidates(df_dados.copy(), ""),id="dlMap", style={ 'width': '100%', 'height': '70vh','margin': "auto", "display": "block", "position": "relative" }),
                )],
                    id="map-container",
                    className="shadow  bg-body rounded",
                ),
            ],
            className="col-md-9 ",
        ),               
        ],className="row"),
        
    ],
     className="container-fluid bg-light",
     )
    
    
@app.callback(
    Output(component_id='select_candidato', component_property='options'),
    Input(component_id='cargos', component_property='value')
)
def update_output_div(input_value):
    result_options = df_dados[df_dados['ds_cargo']==input_value]['nm_candidato'].unique().tolist()
    return result_options


@app.callback(
    Output(component_id='qtd_votos', component_property='children'),
    Output(component_id='qtd_votos_cidade', component_property='children'),
    Output(component_id='melhor_cidade', component_property='children'),
    Input(component_id='select_candidato', component_property='value')
)
def update_output_div(input_value):
    df_dados_candidato = df_dados[df_dados['nm_candidato']==input_value]
    result_options = df_dados_candidato['qt_votos_nominais'].sum()
    qtd_votos_cidade = df_dados_candidato['qt_votos_nominais'].max()
    melhor_cidade = df_dados_candidato[df_dados_candidato['qt_votos_nominais']==qtd_votos_cidade]['nm_municipio'].values[0]
    
    
    return f"{result_options} Votos", f"{qtd_votos_cidade} Votos", melhor_cidade

@app.callback(
    Output(component_id='dlMap', component_property='children'),
    Input(component_id='select_candidato', component_property='value')
)
def update_output_div(input_value):
     
     return filter_candidates(df_dados.copy(), input_value)

if __name__ == '__main__':
    app.run_server(debug=True)