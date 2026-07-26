import sqlite3
import pandas as pd

DB_PATH = 'database/strategy_learning.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_asset_ranking(min_trades=3, lookback=None):
    """
    Retorna ranking de ativos por win rate.
    lookback: número de trades mais recentes a considerar (ex: 100 para memória curta).
    """
    conn = get_connection()
    
    if lookback:
        # Obter os últimos N trades por ativo
        query = f'''
            WITH ranked AS (
                SELECT 
                    asset, direction, result, timestamp,
                    ROW_NUMBER() OVER (PARTITION BY asset ORDER BY id DESC) as rn
                FROM market_context
                WHERE result != 'PENDENTE'
            )
            SELECT 
                asset,
                COUNT(*) as total,
                SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
            FROM ranked
            WHERE rn <= ?
            GROUP BY asset
            HAVING total >= ?
            ORDER BY win_rate DESC
        '''
        df = pd.read_sql_query(query, conn, params=(lookback, min_trades))
    else:
        query = '''
            SELECT 
                asset,
                COUNT(*) as total,
                SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
                ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
            FROM market_context
            WHERE result != 'PENDENTE'
            GROUP BY asset
            HAVING total >= ?
            ORDER BY win_rate DESC
        '''
        df = pd.read_sql_query(query, conn, params=(min_trades,))
    
    conn.close()
    return df

def get_top_assets(min_trades=3, min_win_rate=60, lookback=None):
    """Retorna ativos com win_rate >= min_win_rate e total >= min_trades."""
    df = get_asset_ranking(min_trades, lookback)
    if df.empty:
        return []
    return df[df['win_rate'] >= min_win_rate].to_dict('records')

def get_bottom_assets(min_trades=3, max_win_rate=40, lookback=None):
    """Retorna ativos com win_rate <= max_win_rate e total >= min_trades."""
    df = get_asset_ranking(min_trades, lookback)
    if df.empty:
        return []
    return df[df['win_rate'] <= max_win_rate].to_dict('records')
