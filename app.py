import dash, dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go

import requests
from bs4 import BeautifulSoup


import pandas as pd

from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, commonallplayers, playercareerstats, shotchartdetail

# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}])

# colors = {
#     'background': '#111111',
#     'text': '#7FDBFF'
# }

# assume you have a "long-form" data frame
# see https://plotly.com/python/px-arguments/ for more options
# df = pd.DataFrame({
#     "Fruit": ["Apples", "Oranges", "Bananas", "Apples", "Oranges", "Bananas"],
#     "Amount": [4, 1, 2, 2, 4, 5],
#     "City": ["SF", "SF", "SF", "Montreal", "Montreal", "Montreal"]
# })

# fig = px.bar(df, x="Fruit", y="Amount", color="City", barmode="group")

# fig.update_layout(
#     plot_bgcolor=colors['background'],
#     paper_bgcolor=colors['background'],
#     font_color=colors['text']
# )

all_players = commonallplayers.CommonAllPlayers().get_data_frames()[0]
active_players = all_players[all_players.TO_YEAR == all_players.TO_YEAR.max()]

app.layout = html.Div([
    html.Div(id="output-clientside"),
    html.H1(
        children='NBA Player Tracker',
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
                        value=[],
                        searchable=True,
                        placeholder="Select a player",
                        className="dcc_control",
                        multi=True
                    ),

                    dcc.RadioItems(
                        id='stat-pick',
                        options=[
                            {'label': 'Points', 'value': 'PTS'},
                            {'label': 'Rebounds', 'value': 'REB'},
                            {'label': 'Assists', 'value': 'AST'},
                            {'label': 'Steals', 'value': 'STL'},
                            {'label': 'Blocks', 'value': 'BLK'},
                        ],
                        value='PTS',
                        labelStyle={'display': 'inline-block'},
                        className="dcc_control",
                    ),    
                ],
                className = "pretty_container four columns"
            ),

            html.Div(
                [dcc.Graph(id='graph-gamelog')],
                # id="right-column",
                className='pretty_container eight columns',
            ),
        ],
        className="row flex-display",
    ),
    
    html.Div(
                [dcc.Graph(id='graph-shot')],
                # id="right-column",
                className='pretty_container',
            ),
    
    
],
id="mainContainer",
style={"display": "flex", "flex-direction": "column"},
)

@app.callback(
    [
        Output('graph-gamelog', 'figure'), 
        Output('graph-shot', 'figure'), 
        # Output('career-stat', 'data'), 
        # Output('player-pic', 'src'),
    ],   
    [
        Input('name-search', 'value'),
        Input('stat-pick', 'value'),
    ]
)
def update_gamelog_figure(player_id=[], stat='PTS'):
    fig = go.Figure()
    
    for p in player_id:
        # print(playergamelog.PlayerGameLog(player_id=p).get_data_frames()[0])
        df = playergamelog.PlayerGameLog(player_id=p).get_data_frames()[0][['GAME_DATE', stat, 'MATCHUP', 'WL', 'FG_PCT']]
        df = df.rename(columns={'WL': 'Win/Lose'})
        df['size'] = df['FG_PCT'] * 10
        df['date'] = pd.to_datetime(df['GAME_DATE'])
        df = df.sort_values(by=['date'])
        df['stat'] = stat
    #     df['MATCHUP'] = df['MATCHUP'].map(lambda x: ' '.join(x.replace('.', '').split(' ')[1:]))
    #     df['type'] = stat
        # print(df)
    #     df_ewa = df.copy()
        df['avg'] = df[stat].ewm(com=0.9).mean()
#     df_ewa['type'] = 'EWA '+ stat
#     df = pd.concat([df, df_ewa])

        player_name = active_players.loc[active_players.PERSON_ID==int(p), 'DISPLAY_FIRST_LAST'].values[0]
        fig.add_trace(go.Scatter(x=df['date'], y=df[stat], customdata = df[['MATCHUP','Win/Lose','stat','avg']], name=player_name))

    fig.update_traces(
        mode="lines+markers",
        marker = dict(
            size = 10
        ),
        hovertemplate="<b>%{customdata[0]} (%{customdata[1]})</b><br><br>%{customdata[2]}: %{y}",
    )
    fig.update_layout(
        hovermode="closest",
        plot_bgcolor="#F9F9F9",
        paper_bgcolor="#F9F9F9",
    )
    
    

    fig1 = go.Figure()
    draw_plotly_court(fig1)
    
    if player_id != []:
        shot = shotchartdetail.ShotChartDetail(
            team_id='0', player_id=player_id[0], context_measure_simple='FGA'
        ).get_data_frames()[0]

        shot = shot[shot.LOC_Y<=417]
    else:
        shot = pd.DataFrame.from_dict(
            {
                'EVENT_TYPE': ['Made Shot', 'Missed Shot'], 
                'LOC_X': [1000, 1000],
                'LOC_Y': [1000, 1000],
            }
        )
        
    fig1.add_trace(go.Scatter(
        x=shot.loc[shot['EVENT_TYPE']=='Made Shot', 'LOC_X'], 
        y=shot.loc[shot['EVENT_TYPE']=='Made Shot', 'LOC_Y'], 
        mode='markers',
        marker=dict(
            opacity=.2,
            color='green'
        ),
        name = 'Made Shot'
    ))
    fig1.add_trace(go.Scatter(
        x=shot.loc[shot['EVENT_TYPE']=='Missed Shot', 'LOC_X'], 
        y=shot.loc[shot['EVENT_TYPE']=='Missed Shot', 'LOC_Y'], 
        mode='markers',
        marker=dict(
            opacity=.2,
            color='red'
        ),
        name = 'Missed Shot'
    ))

    # src = f'https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png'

    return fig, fig1
    # , cs.to_dict('records'), src

def career_stat(player_id):
    career = playercareerstats.PlayerCareerStats(player_id)
    career.get_data_frames()[0]
    cs = career.get_data_frames()[0]
    cs = cs[cs.TEAM_ID!=0]
    for c in ['MIN', 'FGM', 'FGA', 'FG3M', 
              'FG3A', 'FTM', 'FTA', 'OREB', 
              'DREB', 'REB', 'AST', 'STL',
              'BLK', 'TOV', 'PF', 'PTS']:
        cs[c] = (cs[c] / cs['GP']).round(1)

    cs['FG'] = cs['FGM'].astype(str) + '-' + cs['FGA'].astype(str)
    cs['3PT'] = cs['FG3M'].astype(str) + '-' + cs['FG3A'].astype(str)
    cs['FT'] = cs['FTM'].astype(str) + '-' + cs['FTA'].astype(str)
    cs['FG%'] = (100*cs['FG_PCT']).round(1)
    cs['3PT%'] = (100*cs['FG3_PCT']).round(1)
    cs['FT%'] = (100*cs['FT_PCT']).round(1)
    cs = cs.rename(columns={
        'SEASON_ID': 'SEASON',
        'TOV': 'TO',
        'TEAM_ABBREVIATION': 'TEAM'
    })
    
    print(cs[['SEASON', 'TEAM', 'GP', 'GS', 'MIN', 'FG', 'FG%', '3PT',
           '3PT%', 'FT', 'FT%', 'OREB', 'DREB', 'REB', 'AST', 'STL',
           'BLK', 'TO', 'PF', 'PTS']])
def draw_plotly_court(fig, fig_width=600, margins=10):

    import numpy as np

    # From: https://community.plot.ly/t/arc-shape-with-path/7205/5
    def ellipse_arc(x_center=0.0, y_center=0.0, a=10.5, b=10.5, start_angle=0.0, end_angle=2 * np.pi, N=200, closed=False):
        t = np.linspace(start_angle, end_angle, N)
        x = x_center + a * np.cos(t)
        y = y_center + b * np.sin(t)
        path = f'M {x[0]}, {y[0]}'
        for k in range(1, len(t)):
            path += f'L{x[k]}, {y[k]}'
        if closed:
            path += ' Z'
        return path

    fig_height = fig_width * (470 + 2 * margins) / (500 + 2 * margins)
    fig.update_layout(width=fig_width, height=fig_height)

    # Set axes ranges
    fig.update_xaxes(range=[-250 - margins, 250 + margins])
    fig.update_yaxes(range=[-52.5 - margins, 417.5 + margins])

    threept_break_y = 89.47765084
    three_line_col = "#777777"
    main_line_col = "#777777"

    fig.update_layout(
        # Line Horizontal
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        yaxis=dict(
            scaleanchor="x",
            scaleratio=1,
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks='',
            showticklabels=False,
            fixedrange=True,
        ),
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showline=False,
            ticks='',
            showticklabels=False,
            fixedrange=True,
        ),
        shapes=[
            dict(
                type="rect", x0=-250, y0=-52.5, x1=250, y1=417.5,
                line=dict(color=main_line_col, width=1),
                # fillcolor='#333333',
                layer='below'
            ),
            dict(
                type="rect", x0=-80, y0=-52.5, x1=80, y1=137.5,
                line=dict(color=main_line_col, width=1),
                # fillcolor='#333333',
                layer='below'
            ),
            dict(
                type="rect", x0=-60, y0=-52.5, x1=60, y1=137.5,
                line=dict(color=main_line_col, width=1),
                # fillcolor='#333333',
                layer='below'
            ),
            dict(
                type="circle", x0=-60, y0=77.5, x1=60, y1=197.5, xref="x", yref="y",
                line=dict(color=main_line_col, width=1),
                # fillcolor='#dddddd',
                layer='below'
            ),
            dict(
                type="line", x0=-60, y0=137.5, x1=60, y1=137.5,
                line=dict(color=main_line_col, width=1),
                layer='below'
            ),

            dict(
                type="rect", x0=-2, y0=-7.25, x1=2, y1=-12.5,
                line=dict(color="#ec7607", width=1),
                fillcolor='#ec7607',
            ),
            dict(
                type="circle", x0=-7.5, y0=-7.5, x1=7.5, y1=7.5, xref="x", yref="y",
                line=dict(color="#ec7607", width=1),
            ),
            dict(
                type="line", x0=-30, y0=-12.5, x1=30, y1=-12.5,
                line=dict(color="#ec7607", width=1),
            ),

            dict(type="path",
                 path=ellipse_arc(a=40, b=40, start_angle=0, end_angle=np.pi),
                 line=dict(color=main_line_col, width=1), layer='below'),
            dict(type="path",
                 path=ellipse_arc(a=237.5, b=237.5, start_angle=0.386283101, end_angle=np.pi - 0.386283101),
                 line=dict(color=main_line_col, width=1), layer='below'),
            dict(
                type="line", x0=-220, y0=-52.5, x1=-220, y1=threept_break_y,
                line=dict(color=three_line_col, width=1), layer='below'
            ),
            dict(
                type="line", x0=-220, y0=-52.5, x1=-220, y1=threept_break_y,
                line=dict(color=three_line_col, width=1), layer='below'
            ),
            dict(
                type="line", x0=220, y0=-52.5, x1=220, y1=threept_break_y,
                line=dict(color=three_line_col, width=1), layer='below'
            ),

            dict(
                type="line", x0=-250, y0=227.5, x1=-220, y1=227.5,
                line=dict(color=main_line_col, width=1), layer='below'
            ),
            dict(
                type="line", x0=250, y0=227.5, x1=220, y1=227.5,
                line=dict(color=main_line_col, width=1), layer='below'
            ),
            dict(
                type="line", x0=-90, y0=17.5, x1=-80, y1=17.5,
                line=dict(color=main_line_col, width=1), layer='below'
            ),
            dict(
                type="line", x0=-90, y0=27.5, x1=-80, y1=27.5,
                line=dict(color=main_line_col, width=1), layer='below'
            ),
            dict(
                type="line", x0=-90, y0=57.5, x1=-80, y1=57.5,
                line=dict(color=main_line_col, width=1), layer='below'
            ),
            dict(
                type="line", x0=-90, y0=87.5, x1=-80, y1=87.5,
                line=dict(color=main_line_col, width=1), layer='below'
            ),
            dict(
                type="line", x0=90, y0=17.5, x1=80, y1=17.5,
                line=dict(color=main_line_col, width=1), layer='below'
            ),
            dict(
                type="line", x0=90, y0=27.5, x1=80, y1=27.5,
                line=dict(color=main_line_col, width=1), layer='below'
            ),
            dict(
                type="line", x0=90, y0=57.5, x1=80, y1=57.5,
                line=dict(color=main_line_col, width=1), layer='below'
            ),
            dict(
                type="line", x0=90, y0=87.5, x1=80, y1=87.5,
                line=dict(color=main_line_col, width=1), layer='below'
            ),

            dict(type="path",
                 path=ellipse_arc(y_center=417.5, a=60, b=60, start_angle=-0, end_angle=-np.pi),
                 line=dict(color=main_line_col, width=1), layer='below'),

        ]
    )
    return True

if __name__ == '__main__':
    app.run_server(debug=True)