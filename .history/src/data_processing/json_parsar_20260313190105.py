# data_processing/json_parser.py

import json
import os
import pandas as pd
from pathlib import Path

def parse_single_match(filepath):
    """
    Takes ONE JSON file → returns list of player-rows for that match
    """
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    info = data['info']
    
    # ── STEP 1: Extract match-level metadata ──────────────────────
    match_meta = {
        'match_id':    Path(filepath).stem,       # filename = match ID
        'date':        info['dates'][0],           # first date
        'format':      info['match_type'],         # T20 / ODI / Test
        'venue':       info.get('venue', 'Unknown'),
        'team1':       info['teams'][0],
        'team2':       info['teams'][1],
        'toss_winner': info['toss']['winner'],
        'toss_decision': info['toss']['decision'],
    }
    
    # ── STEP 2: Find which players are Playing XI ─────────────────
    # 'players' key has the confirmed XI per team
    playing_xi = {}
    for team, players in info.get('players', {}).items():
        for player in players:
            playing_xi[player] = team
    
    # ── STEP 3: Set up per-player stat collectors ─────────────────
    # Every player starts at zero for everything
    player_stats = {}
    
    for player, team in playing_xi.items():
        player_stats[player] = {
            **match_meta,            # copy match info into every row
            'player':       player,
            'team':         team,
            'opponent':     [t for t in info['teams'] if t != team][0],
            'playing_xi':   1,       # +4 pts in Dream11 for playing
            
            # Batting stats
            'runs':         0,
            'balls_faced':  0,
            'fours':        0,
            'sixes':        0,
            'fifties':      0,       # 1 if scored 50-99
            'hundreds':     0,       # 1 if scored 100+
            'thirties':     0,       # 1 if scored 30-49 (T20)
            'duck':         0,       # 1 if out for 0
            'not_out':      1,       # will flip if dismissed
            
            # Bowling stats
            'balls_bowled': 0,
            'runs_conceded': 0,
            'wickets':      0,
            'maidens':      0,
            'dot_balls':    0,
            'wides':        0,
            'noballs':      0,
            
            # Fielding stats
            'catches':      0,
            'stumpings':    0,
            'run_outs_direct':   0,
            'run_outs_indirect': 0,
        }
    
    # ── STEP 4: Walk through EVERY ball in the match ──────────────
    for innings in data.get('innings', []):
        batting_team = innings['team']
        
        for over_data in innings.get('overs', []):
            over_number = over_data['over']
            deliveries_in_over = over_data['deliveries']
            runs_in_over = 0
            wickets_in_over = 0
            
            for delivery in deliveries_in_over:
                batter  = delivery['batter']
                bowler  = delivery['bowler']
                runs    = delivery['runs']
                
                # Only count if player is in our playing XI
                if batter not in player_stats:
                    player_stats[batter] = {**match_meta}  # edge case
                
                # ── Batting: credit the batter ────────────────
                batter_runs = runs['batter']   # runs off bat (not extras)
                player_stats[batter]['runs']        += batter_runs
                player_stats[batter]['balls_faced'] += 1
                
                if batter_runs == 4:
                    player_stats[batter]['fours'] += 1
                if batter_runs == 6:
                    player_stats[batter]['sixes'] += 1
                
                # ── Bowling: debit the bowler ─────────────────
                if bowler in player_stats:
                    player_stats[bowler]['balls_bowled']  += 1
                    player_stats[bowler]['runs_conceded'] += runs['total']
                    runs_in_over += runs['total']
                
                # ── Extras: wides and noballs ─────────────────
                extras = delivery.get('extras', {})
                if 'wides' in extras and bowler in player_stats:
                    player_stats[bowler]['wides']   += 1
                    player_stats[bowler]['balls_bowled'] -= 1  # wide = no ball
                if 'noballs' in extras and bowler in player_stats:
                    player_stats[bowler]['noballs'] += 1
                
                # ── Wickets: dismissals ───────────────────────
                for wicket in delivery.get('wickets', []):
                    dismissed_player = wicket['player_out']
                    kind = wicket['kind']
                    
                    # Batter is out
                    if dismissed_player in player_stats:
                        player_stats[dismissed_player]['not_out'] = 0
                        if player_stats[dismissed_player]['runs'] == 0:
                            player_stats[dismissed_player]['duck'] = 1
                    
                    # Bowler gets credit
                    # (run out = no credit to bowler)
                    if kind not in ['run out', 'retired hurt', 'obstructing the field']:
                        if bowler in player_stats:
                            player_stats[bowler]['wickets'] += 1
                            wickets_in_over += 1
                    
                    # Fielder gets credit
                    for fielder in wicket.get('fielders', []):
                        fielder_name = fielder.get('name', '')
                        if fielder_name in player_stats:
                            if kind == 'caught':
                                player_stats[fielder_name]['catches'] += 1
                            elif kind == 'stumped':
                                player_stats[fielder_name]['stumpings'] += 1
                            elif kind == 'run out':
                                if fielder.get('substitute', False):
                                    player_stats[fielder_name]['run_outs_indirect'] += 1
                                else:
                                    player_stats[fielder_name]['run_outs_direct'] += 1
            
            # ── Maiden over check ─────────────────────────────
            # Maiden = 6 balls, 0 runs, no wides/noballs
            if runs_in_over == 0 and len(deliveries_in_over) == 6:
                if bowler in player_stats:
                    player_stats[bowler]['maidens'] += 1
    
    # ── STEP 5: Compute milestone flags after match ends ─────────
    for player, stats in player_stats.items():
        r = stats['runs']
        if r >= 100:
            stats['hundreds'] = 1
        elif r >= 50:
            stats['fifties']  = 1
        elif r >= 30:
            stats['thirties'] = 1
        
        # Compute Strike Rate and Economy for storage
        stats['batting_sr'] = (r / stats['balls_faced'] * 100) \
                               if stats['balls_faced'] > 0 else 0
        
        overs_bowled = stats['balls_bowled'] / 6
        stats['economy'] = (stats['runs_conceded'] / overs_bowled) \
                            if overs_bowled > 0 else 0
    
    return list(player_stats.values())


def parse_all_matches(data_dir, format_filter=None):
    """
    Loops through ALL JSON files → builds master DataFrame
    """
    all_rows = []
    json_files = list(Path(data_dir).glob('**/*.json'))
    
    print(f"Found {len(json_files)} JSON files")
    
    for i, filepath in enumerate(json_files):
        try:
            rows = parse_single_match(filepath)
            
            # Optional: filter by format
            if format_filter:
                rows = [r for r in rows if r.get('format') == format_filter]
            
            all_rows.extend(rows)
            
            if i % 500 == 0:
                print(f"Parsed {i}/{len(json_files)} files...")
        
        except Exception as e:
            print(f"Error parsing {filepath}: {e}")
            continue
    
   df = pd.DataFrame(all_rows)
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values(['player', 'date']).reset_index(drop=True)

print(f"Total rows: {len(df)} | Players: {df['player'].nunique()}")

# ── SAVE CSV FOR CHECKING ─────────────────────
output_file = "parsed_player_data.csv"
df.to_csv(output_file, index=False)

print(f"CSV file saved: {output_file}")
print("Preview of data:")
print(df.head())

return df