import dash, dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import requests
from bs4 import BeautifulSoup
from datetime import datetime

import pandas as pd

from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, commonallplayers, playercareerstats, shotchartdetail

from flask_caching import Cache

# TODO
# 1. Add selecitions for shot zone basic and area
# 2. Add fg% to pie chart
# 3. hexagonify shot chart
# 4. add fg% to shot accuracy chart
# 5. associate mouse selected data in distance with other plots if possible

# external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, meta_tags=[{"name": "viewport", "content": "width=device-width"}])

cache = Cache(app.server, config={
    'CACHE_TYPE': 'simple'
})

TIMEOUT = 60

# all_players = commonallplayers.CommonAllPlayers().get_data_frames()[0]
active_players = all_players[all_players.TO_YEAR == all_players.TO_YEAR.max()]
cur_year = datetime.today().year

app.layout = html.Div([
    html.Div(id="output-clientside"),
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

@app.callback(
    [
        Output('graph-shot-hist', 'figure'), 
        Output('graph-fga', 'figure'), 
        Output('graph-fgp', 'figure'), 
        # Output('career-stat', 'data'), 
        Output('player-img', 'src'),
        Output('graph-shot-pie', 'figure'), 
    ],   
    [
        Input('name-search', 'value'),
        Input('quarter-radio', 'value'),
        Input('time-slider', 'value'),
        Input('year-slider', 'value'),
        # Input('stat-pick', 'value'),
    ]
)
def update_gamelog_figure(player_id=None, quarter='0', time=12, year=[2003, cur_year]):
    # stat = 'PTS'
    src = None
    fig = go.Figure()
    fig1 = go.Figure()
    draw_plotly_court(fig1)
    fig2 = go.Figure()
    draw_plotly_court(fig2)
    fig3 = go.Figure()

    shot = shot_detail(player_id)

    if quarter==0:
        quarter_name = 'each quarter'
    elif 1<=quarter<= 4:
        shot = shot[shot['PERIOD']==quarter]
        if quarter==1:
            quarter_name = f'1st quarter'
        elif quarter==2:
            quarter_name = f'2nd quarter'
        elif quarter==3:
            quarter_name = f'3rd quarter'
        else:
            quarter_name = f'4th quarter'
    else:
        shot = shot[shot['PERIOD']>=quarter]
        quater_name = 'overtime'

    if time==12:
        pass
    else:
        shot = shot[shot['min_left'] <= time]

    if year==[2003, cur_year]:
        pass
    else:
        shot = shot[(shot['year'] <= year[1]) & (shot['year'] >= year[0])]

    if player_id:
        src = f'https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png'
        player_name = active_players.loc[active_players.PERSON_ID==int(player_id), 'DISPLAY_FIRST_LAST'].values[0]
        print(player_name, player_id)
        fig.add_trace(go.Histogram(
            x=shot.loc[shot['SHOT_ATTEMPTED_FLAG']==1, 'SHOT_DISTANCE'],
            # customdata = df[['MATCHUP','Win/Lose','stat','avg']],
            xbins=dict(
                      start=0,
                      end=100,
                      size=1),
            name='Attempted Shot',
            ))
        fig.add_trace(go.Histogram(
            x=shot.loc[shot['SHOT_MADE_FLAG']==1, 'SHOT_DISTANCE'],
            xbins=dict(
                      start=0,
                      end=100,
                      size=1),
            # customdata = df[['MATCHUP','Win/Lose','stat','avg']], 
            name='Made Shot',
            ))
        
        # Overlay both histograms
        
        fig.update_layout(barmode='overlay', 
                title=f'Shot selection from {year[0]} to {year[1]} during last {time} minutes of {quarter_name}'
            )
        # Reduce opacity to see both histograms
        fig.update_traces(opacity=0.6)

        shot_area = shot.groupby('ACTION_TYPE', as_index=False).sum(['SHOT_ATTEMPTED_FLAG', 'SHOT_MADE_FLAG'])
        # fig3 = px.pie(shot_area, values='SHOT_ATTEMPTED_FLAG', names='ACTION_TYPE')
        fig3 = make_subplots(rows=1, cols=2, specs=[[{'type':'domain'}, {'type':'domain'}]])
        fig3.add_trace(go.Pie(
                labels=shot_area['ACTION_TYPE'],
                values=shot_area['SHOT_MADE_FLAG'],
                name='Made Shot'),
                1, 1
            )
        fig3.add_trace(go.Pie(
                labels=shot_area['ACTION_TYPE'],
                values=shot_area['SHOT_ATTEMPTED_FLAG'],
                name='SHOT ATTEMPT'),
                1, 2
            )

        fig3.update_traces(
            hoverinfo='label+percent', 
            textinfo='none',
            hole=.4
            )
        
        fig3.update_layout(
            height=600,
            title="Shot type distribution",
            # Add annotations in the center of the donut pies.
            annotations=[dict(text='FG Made', x=0.195, y=0.5, font_size=20, showarrow=False),
                        dict(text='FG Attempted', x=0.825, y=0.5, font_size=20, showarrow=False)])
        # fig3.update(layout_showlegend=False)
    # fig.update_traces(
    #     mode="lines+markers",
    #     marker = dict(
    #         size = 10
    #     ),
    #     hovertemplate="<b>%{customdata[0]} (%{customdata[1]})</b><br><br>%{customdata[2]}: %{y}",
    # )
    fig.update_layout(
        hovermode="closest",
        plot_bgcolor="#F9F9F9",
        paper_bgcolor="#F9F9F9",
    )

    fig3.update_layout(
        hovermode="closest",
        plot_bgcolor="#F9F9F9",
        paper_bgcolor="#F9F9F9",
    )
    
    fig1.add_trace(go.Scatter(
        x=shot['LOC_X'], 
        y=shot['LOC_Y'], 
        mode='markers',
        marker=dict(
            opacity=.3,
            size = 10,
            color=shot['SHOT_MADE_FLAG'],
            colorscale=[[0, 'red'], [1, 'green']]
            # symbol='hexagon',
        ),

        # name = 'Made Shot'
    ))
    # fig1.add_trace(go.Scatter(
    #     x=shot.loc[shot['EVENT_TYPE']=='Missed Shot', 'LOC_X'], 
    #     y=shot.loc[shot['EVENT_TYPE']=='Missed Shot', 'LOC_Y'], 
    #     mode='markers',
    #     marker=dict(
    #         opacity=.2,
    #         color='red'
    #     ),
    #     name = 'Missed Shot'
    # ))

    # fig1.add_trace(go.Histogram2dContour(
    #     x=shot['LOC_X'], 
    #     y=shot['LOC_Y'],
    #     # histnorm = 'percent',
    #     opacity = .7,
    #     colorscale = 'hot',
    #     reversescale = True,
    # ))

    # margins = 10
    # fig1.update_xaxes(range=[-1250, 1250])
    # fig1.update_yaxes(range=[-52.5, 417.5])

    ss = shot.groupby(['x', 'y'], as_index=False).agg({'SHOT_ATTEMPTED_FLAG': 'sum', 'SHOT_MADE_FLAG': 'sum'})

    max_freq = 0.002
    # freq_by_hex = np.array([min(max_freq, i) for i in league_hexbin_stats['freq_by_hex']])
    # colorscale = 'YlOrRd'
    marker_cmin = 10
    marker_cmax = 200
    ticktexts = [str(marker_cmin), "", str(marker_cmax)]
    fig2.add_trace(go.Scatter(
        # x=shot['x'], 
        # y=shot['y'], 
        x = ss['x'],
        y = ss['y'],
        mode='markers',
        marker=dict(
            opacity=.2,
            # color='red',
            color = ss['SHOT_ATTEMPTED_FLAG'],
            size = 10,
            colorscale = 'YlOrRd',
            reversescale = True,
            colorbar=dict(
            thickness=15,
            x=0.84,
            y=0.87,
            yanchor='middle',
            len=0.2,
            title=dict(
                text="<B>Accuracy</B>",
                font=dict(
                    size=11,
                    color='#4d4d4d'
                ),
            ),
            tickvals=[marker_cmin, (marker_cmin + marker_cmax) / 2, marker_cmax],
            ticktext=ticktexts,
            tickfont=dict(
                size=11,
                color='#4d4d4d'
            )
        ),
            cmin=marker_cmin, cmax=marker_cmax,
        line=dict(width=1, color='#333333'),
        ),
        name = 'Shot'
    ))

    fig1.update_layout(
        title={
        'text': "Shot location chart",
        'y':0.98,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'}
    )
    fig2.update_layout(
        title={
        'text': "Shot accuracy location chart",
        'y':.98,
        'x':0.5,
        'xanchor': 'center',
        'yanchor': 'top'}
    )

    return fig, fig1, fig2, src, fig3

@cache.memoize(timeout=TIMEOUT)
def shot_detail(player_id):
    print('cache is not used!')
    if player_id:
        shot = shotchartdetail.ShotChartDetail(
            team_id='0', player_id=player_id, context_measure_simple='FGA'
        ).get_data_frames()[0]

        shot = shot[shot.LOC_Y<=417]

        shot['x'] = (shot['LOC_X'] + 250 + 5) // 10 * 10 -250
        shot['y'] = (shot['LOC_Y'] + 52.5 + 5) // 10 * 10 - 52.5

        shot['min_left'] = shot['SECONDS_REMAINING']/60 + shot['MINUTES_REMAINING']
        shot['year'] = shot['GAME_DATE'].map(lambda x: int(x[:4]))
    else:
        shot = pd.DataFrame.from_dict(
            {
                'EVENT_TYPE': ['Made Shot', 'Missed Shot'], 
                'LOC_X': [1000, 1000],
                'LOC_Y': [1000, 1000],
                'SHOT_ATTEMPTED_FLAG': [0, 0],
                'SHOT_MADE_FLAG': [0, 0],
                'x': [0, 0],
                'y': [0, 0],
                'min_left': [0, 0],
                'year': [0, 0],
                'SHOT_ZONE_AREA': ['', ''],
                'ACTION_TYPE': ['', ''],
            }
        )

    return shot 

@cache.memoize(timeout=TIMEOUT)
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
    
    return cs

def draw_plotly_court(fig, fig_width=800, margins=10):

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

def gamelog(player_id):
    df = playergamelog.PlayerGameLog(player_id=player_id).get_data_frames()[0][['GAME_DATE', stat, 'MATCHUP', 'WL', 'FG_PCT']]
    df = df.rename(columns={'WL': 'Win/Lose'})
    df['size'] = df['FG_PCT'] * 10
    df['date'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values(by=['date'])
    df['stat'] = stat
    df['avg'] = df[stat].ewm(com=0.9).mean()

    return df

if __name__ == '__main__':
    app.run_server(debug=True)