import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'database/strategy_learning.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_win_rate_by_hour(min_trades=3):
    """Retorna win rate por hora (0-23)."""
    conn = get_connection()
    query = '''
        SELECT 
            hour,
            COUNT(*) as total,
            SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
        GROUP BY hour
        HAVING total >= ?
        ORDER BY hour
    '''
    df = pd.read_sql_query(query, conn, params=(min_trades,))
    conn.close()
    return df

def get_win_rate_by_weekday(min_trades=3):
    """Retorna win rate por dia da semana (0=segunda, 6=domingo)."""
    conn = get_connection()
    query = '''
        SELECT 
            day_of_week,
            COUNT(*) as total,
            SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
        GROUP BY day_of_week
        HAVING total >= ?
        ORDER BY day_of_week
    '''
    df = pd.read_sql_query(query, conn, params=(min_trades,))
    conn.close()
    return df

def get_best_hours(min_trades=3, min_win_rate=60):
    """Retorna horas com win_rate >= min_win_rate e total >= min_trades."""
    df = get_win_rate_by_hour(min_trades)
    if df.empty:
        return []
    return df[df['win_rate'] >= min_win_rate].to_dict('records')

def get_worst_hours(min_trades=3, max_win_rate=40):
    """Retorna horas com win_rate <= max_win_rate e total >= min_trades."""
    df = get_win_rate_by_hour(min_trades)
    if df.empty:
        return []
    return df[df['win_rate'] <= max_win_rate].to_dict('records')

def get_best_weekdays(min_trades=3, min_win_rate=60):
    """Retorna dias com win_rate >= min_win_rate e total >= min_trades."""
    df = get_win_rate_by_weekday(min_trades)
    if df.empty:
        return []
    return df[df['win_rate'] >= min_win_rate].to_dict('records')

def get_worst_weekdays(min_trades=3, max_win_rate=40):
    """Retorna dias com win_rate <= max_win_rate e total >= min_trades."""
    df = get_win_rate_by_weekday(min_trades)
    if df.empty:
        return []
    return df[df['win_rate'] <= max_win_rate].to_dict('records')

def get_session_win_rate(min_trades=3):
    """Retorna win rate por sessão (Ásia, Londres, NY, Overlap)."""
    conn = get_connection()
    query = '''
        SELECT 
            session,
            COUNT(*) as total,
            SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
        GROUP BY session
        HAVING total >= ?
        ORDER BY win_rate DESC
    '''
    df = pd.read_sql_query(query, conn, params=(min_trades,))
    conn.close()
    return df
