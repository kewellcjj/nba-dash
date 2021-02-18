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

from utils.data import get_shot_detail_data, data_filter_shot
from utils.figure import draw_plotly_court
from utils.layout import app_layout
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

all_players = commonallplayers.CommonAllPlayers().get_data_frames()[0]
active_players = all_players[all_players.TO_YEAR == all_players.TO_YEAR.max()]
cur_year = datetime.today().year

app.layout = app_layout(active_players, cur_year)

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
        Input('zone-basic', 'value'),
    ]
)
def update_gamelog_figure(player_id=None, quarter='0', time=12, year=[2003, cur_year], zone_basic=None):
    # stat = 'PTS'
    src = None
    fig = go.Figure()
    fig1 = go.Figure()
    draw_plotly_court(fig1)
    fig2 = go.Figure()
    draw_plotly_court(fig2)
    fig3 = go.Figure()

    shot = shot_detail(player_id)
    shot = data_filter_shot(shot, quarter, time, year, zone_basic)

    if quarter==0:
        quarter_name = 'each quarter'
    elif quarter==1:
        quarter_name = f'1st quarter'
    elif quarter==2:
        quarter_name = f'2nd quarter'
    elif quarter==3:
        quarter_name = f'3rd quarter'
    elif quarter==4:
        quarter_name = f'4th quarter'
    else:
        quater_name = 'overtime'

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
                text=100*shot_area['SHOT_MADE_FLAG']/shot_area['SHOT_ATTEMPTED_FLAG'],
                name=''
                ),
                1, 1
            )
        fig3.add_trace(go.Pie(
                labels=shot_area['ACTION_TYPE'],
                values=shot_area['SHOT_ATTEMPTED_FLAG'],
                text=100*shot_area['SHOT_MADE_FLAG']/shot_area['SHOT_ATTEMPTED_FLAG'],
                name=''
                ),
                1, 2
            )

        fig3.update_traces(
            hoverinfo='none', 
            textinfo='none',
            hovertemplate="<b>%{label} (%{percent})</b><br><br>Count: %{value}<br>FG%: %{text:.1f}%",
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
    return get_shot_detail_data(player_id)

if __name__ == '__main__':
    app.run_server(debug=True)