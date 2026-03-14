# data_processing/feature_engineering.py

import pandas as pd
import numpy as np

def add_ema_features(df, alphas=[0.5, 0.7, 0.9], windows=[5, 7, 9]):
    """
    For each player, compute EMA of fantasy_points
    using multiple alpha values
    
    CRITICAL: Use shift(1) so we never leak future data
    (prediction for match N can only use matches 1 to N-1)
    """
    df = df.sort_values(['player', 'date']).copy()
    
    for alpha in alphas:
        col_name = f'ema_pts_alpha{int(alpha*10)}'
        
        # Group by player, compute EMA, shift by 1 to avoid leakage
        df[col_name] = (
            df.groupby('player')['fantasy_points']
              .transform(lambda x: x.shift(1)           # exclude current match
                                    .ewm(alpha=alpha,   # exponential weight
                                         adjust=False)  # standard EMA formula
                                    .mean())
        )
    
    return df


def add_hcma_features(df, windows=[10, 30, 50]):
    """
    Historical Cumulative Moving Average
    window=10  → average of last 10 matches
    window=30  → average of last 30 matches  
    window=50  → average of last 50 matches
    
    Again: shift(1) is critical to prevent data leakage
    """
    df = df.sort_values(['player', 'date']).copy()
    
    for window in windows:
        col_name = f'hcma_pts_w{window}'
        
        df[col_name] = (
            df.groupby('player')['fantasy_points']
              .transform(lambda x: x.shift(1)
                                    .rolling(window=window,
                                             min_periods=1)  # allow < window matches
                                    .mean())
        )
    
    return df


def add_rolling_std(df, windows=[5, 10, 20]):
    """
    Standard deviation of fantasy points
    = How consistent/volatile is this player?
    
    High std = risky pick (good for captain)
    Low std  = safe pick (good for VC)
    """
    df = df.sort_values(['player', 'date']).copy()
    
    for window in windows:
        col_name = f'std_pts_w{window}'
        
        df[col_name] = (
            df.groupby('player')['fantasy_points']
              .transform(lambda x: x.shift(1)
                                    .rolling(window=window, min_periods=3)
                                    .std())
        )
    
    return df


def add_all_features(df):
    """
    Master function — call this once on your raw DataFrame
    """
    print("Adding EMA features...")
    df = add_ema_features(df, alphas=[0.5, 0.7, 0.9])
    
    print("Adding HCMA features...")
    df = add_hcma_features(df, windows=[10, 30, 50])
    
    print("Adding rolling std features...")
    df = add_rolling_std(df, windows=[5, 10, 20])
    
    print("Adding format-specific rolling averages...")
    # Rolling average PER FORMAT
    # (T20 form ≠ Test form for the same player)
    for fmt in ['T20', 'ODI', 'Test']:
        fmt_df = df[df['format'] == fmt].copy()
        for window in [5, 10, 20]:
            col = f'rolling_avg_{fmt.lower()}_w{window}'
            df.loc[df['format'] == fmt, col] = (
                fmt_df.groupby('player')['fantasy_points']
                      .transform(lambda x: x.shift(1)
                                             .rolling(window, min_periods=1)
                                             .mean())
            )
    
    # Fill NaN (new players with no history) with global mean
    feature_cols = [c for c in df.columns if c.startswith(('ema_', 'hcma_', 'std_', 'rolling_'))]
    global_mean = df['fantasy_points'].mean()
    df[feature_cols] = df[feature_cols].fillna(global_mean)
    
    print(f"Features added: {feature_cols}")
    return df
