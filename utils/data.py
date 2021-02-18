import pandas as pd

from nba_api.stats.static import players
from nba_api.stats.endpoints import playergamelog, commonallplayers, playercareerstats, shotchartdetail

def data_filter_shot(shot, quarter, time, year, zone_basic):
    if quarter==0:
        pass
    elif 1<=quarter<= 4:
        shot = shot[shot['PERIOD']==quarter]
    else:
        shot = shot[shot['PERIOD']>=quarter]

    shot = shot[shot['min_left'] <= time]
    shot = shot[(shot['year'] <= year[1]) & (shot['year'] >= year[0])]
    shot = shot[shot['SHOT_ZONE_BASIC'].isin(zone_basic)]

    return shot

def get_shot_detail_data(player_id):
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
                'SHOT_ZONE_BASIC': ['', ''],
                'SHOT_ZONE_AREA': ['', ''],
                'ACTION_TYPE': ['', ''],
            }
        )

    return shot 

def get_gamelog_data(player_id):
    df = playergamelog.PlayerGameLog(player_id=player_id).get_data_frames()[0][['GAME_DATE', stat, 'MATCHUP', 'WL', 'FG_PCT']]
    df = df.rename(columns={'WL': 'Win/Lose'})
    df['size'] = df['FG_PCT'] * 10
    df['date'] = pd.to_datetime(df['GAME_DATE'])
    df = df.sort_values(by=['date'])
    df['stat'] = stat
    df['avg'] = df[stat].ewm(com=0.9).mean()

    return df

def get_career_stat_data(player_id):
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