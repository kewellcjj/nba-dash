import dash_core_components as dcc
import dash_html_components as html

def app_layout(active_players, cur_year):
 return html.Div([
        # html.Div(id="output-clientside"),
        html.H1(
            children='Active NBA Player Shot Selection',
            style={
                'textAlign': 'center',
            }
        ),

    #     html.Div(children='Dash: A web application framework for Python.', style={
    #         'textAlign': 'center',
    #         'color': colors['text']
    #     }),
        
        html.Div(
            [
                html.Div(
                    [
                
                        dcc.Dropdown(
                            id='name-search',
                            options=[{'label': name,'value': str(id)} for name, id in zip(active_players.DISPLAY_FIRST_LAST, active_players.PERSON_ID)],
                            value=None,
                            searchable=True,
                            placeholder="Select a player",
                            className="dcc_control",
                            multi=False
                        ),
                        html.P(
                            "Filter by year:",
                            className="control_label",
                        ),
                        dcc.RangeSlider(
                            id="year-slider",
                            min=2003,
                            max=cur_year,
                            value=[2003, cur_year],
                            step = 1,
                            marks={i: str(i) for i in range(2003, cur_year+1) 
                                    if (i%5==0 and i-2003>=2 and cur_year-i>=2) or i==2003 or i==cur_year},
                            className="dcc_control",
                        ),
                        html.P("Filter by quarters:", className="control_label"),
                        dcc.RadioItems(
                            id='quarter-radio',
                            options=[
                                {'label': 'All', 'value': 0},
                                {'label': '1st Qtr', 'value': 1},
                                {'label': '2nd Qtr', 'value': 2},
                                {'label': '3rd Qtr', 'value': 3},
                                {'label': '4th Qtr', 'value': 4},
                                {'label': 'OT', 'value': 5},
                            ],
                            value=0,
                            labelStyle={'display': 'inline-block'},
                            className="dcc_control",
                        ),
                        html.P(
                            "Filter by minutes left in the quarter:",
                            className="control_label",
                        ),
                        dcc.Slider(
                            id="time-slider",
                            min=0,
                            max=12,
                            value=12,
                            step = .1,
                            marks={
                                i: str(i) for i in range(0, 13, 3)
                            },
                            className="dcc_control",
                        ),
                        html.P(
                            "Filter by shot zones:",
                            className="control_label",
                        ),
                        dcc.Dropdown(
                            id='zone-basic',
                            options=[
                                    {'label': name,'value': name} for name in [
                                        'Restricted Area',
                                        'In The Paint (Non-RA)',    
                                        'Mid-Range',
                                        'Left Corner 3',
                                        'Right Corner 3',
                                        'Above the Break 3',
                                        ]
                                ],
                            value=[
                                    'Restricted Area',
                                    'In The Paint (Non-RA)',    
                                    'Mid-Range',
                                    'Left Corner 3',
                                    'Right Corner 3',
                                    'Above the Break 3',
                                ],
                            className="dcc_control",
                            multi=True,
                        ),
                        html.Img(id='player-img', style={'width':'50%'}),
                    ],
                    className = "pretty_container four columns"
                ),
                
                html.Div(
                    [dcc.Graph(id='graph-shot-hist')],
                    # id="right-column",
                    className='pretty_container eight columns',
                ),

                

            ],
            className="row flex-display",
        ),
        
        html.Div(
            [
                html.Div(
                    [dcc.Graph(id='graph-shot-pie')],
                    className='pretty_container twelve columns',
                ),
            ],
            className="row flex-display",
        ), 

        html.Div(
            [
                html.Div(
                    [dcc.Graph(id='graph-fga')],
                    className='pretty_container six columns',
                ),
                html.Div(
                    [dcc.Graph(id='graph-fgp')],
                    className='pretty_container six columns',
                ),
            ],
            className="row flex-display",
        ), 
        
        
    ],
    id="mainContainer",
    style={"display": "flex", "flex-direction": "column"},
    )