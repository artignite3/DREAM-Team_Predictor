def calculate_fantasy_points(row, match_format='T20'):
    """
    Takes ONE player-match row
    Returns fantasy_points (float)
    
    Formula source: Dream11 official scoring rules
    """
    pts = 0
    fmt = match_format.upper()
    
    # ════════════════════════════════════
    # PLAYING XI BONUS (all formats)
    # ════════════════════════════════════
    if row.get('playing_xi', 0) == 1:
        pts += 4
    
    # ════════════════════════════════════
    # BATTING POINTS
    # ════════════════════════════════════
    runs = row.get('runs', 0)
    
    # Base runs
    pts += runs * 1          # 1 pt per run (all formats)
    
    # Boundaries
    pts += row.get('fours', 0) * 1     # +1 per four
    pts += row.get('sixes', 0) * 2     # +2 per six
    
    # Milestones
    if row.get('hundreds', 0):
        pts += 16                       # century bonus
    elif row.get('fifties', 0):
        pts += 8                        # half century bonus
    elif row.get('thirties', 0) and fmt == 'T20':
        pts += 4                        # 30+ bonus (T20 only)
    
    # Duck penalty (only if dismissed, not not-out)
    if row.get('duck', 0) and row.get('not_out', 1) == 0:
        if fmt in ['T20', 'ODI']:
            pts -= 2                    # duck penalty (not for Test)
    
    # Strike Rate bonus/penalty (only T20 and ODI, min 10 balls)
    balls_faced = row.get('balls_faced', 0)
    if balls_faced >= 10:
        sr = row.get('batting_sr', 0)
        
        if fmt == 'T20':
            if sr > 170:   pts += 6
            elif sr > 150: pts += 4
            elif sr > 130: pts += 2
            elif sr < 50:  pts -= 6
            elif sr < 60:  pts -= 4
            elif sr < 70:  pts -= 2
        
        elif fmt == 'ODI':
            if sr > 140:   pts += 6
            elif sr > 120: pts += 4
            elif sr > 100: pts += 2
            elif sr < 40:  pts -= 6
            elif sr < 50:  pts -= 4
            elif sr < 60:  pts -= 2
    
    # ════════════════════════════════════
    # BOWLING POINTS
    # ════════════════════════════════════
    wickets = row.get('wickets', 0)
    
    # Base wickets
    pts += wickets * 25               # 25 pts per wicket
    
    # Wicket haul bonuses
    if wickets >= 5:    pts += 16
    elif wickets >= 4:  pts += 8
    elif wickets >= 3:  pts += 4
    
    # Maiden overs
    pts += row.get('maidens', 0) * 8  # 8 pts per maiden
    
    # Economy bonus/penalty (min 2 overs = 12 balls)
    balls_bowled = row.get('balls_bowled', 0)
    if balls_bowled >= 12:
        eco = row.get('economy', 0)
        
        if fmt == 'T20':
            if eco < 5:    pts += 6
            elif eco < 6:  pts += 4
            elif eco < 7:  pts += 2
            elif eco > 12: pts -= 6
            elif eco > 11: pts -= 4
            elif eco > 10: pts -= 2
        
        elif fmt == 'ODI':
            if eco < 2.5:  pts += 6
            elif eco < 3.5: pts += 4
            elif eco < 4.5: pts += 2
            elif eco > 9:  pts -= 6
            elif eco > 8:  pts -= 4
            elif eco > 7:  pts -= 2
    
    # ════════════════════════════════════
    # FIELDING POINTS
    # ════════════════════════════════════
    catches   = row.get('catches', 0)
    stumpings = row.get('stumpings', 0)
    ro_direct = row.get('run_outs_direct', 0)
    ro_indir  = row.get('run_outs_indirect', 0)
    
    pts += catches   * 8    # 8 per catch
    pts += stumpings * 12   # 12 per stumping
    pts += ro_direct * 12   # 12 direct run out
    pts += ro_indir  * 6    # 6 indirect run out
    
    # 3+ catches in a match bonus
    if catches >= 3:
        pts += 4
    
    return pts