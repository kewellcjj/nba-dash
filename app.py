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
from nba_api.stats.endpoints import playergamelog, commonallplayers, playercareerstats

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
    
    
],
id="mainContainer",
style={"display": "flex", "flex-direction": "column"},
)

@app.callback(
    # [
        Output('graph-gamelog', 'figure'), 
        # Output('career-stat', 'data'), 
        # Output('player-pic', 'src'),
    # ],   
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
    
    # src = f'https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png'

    return fig
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

if __name__ == '__main__':
    app.run_server(debug=True)