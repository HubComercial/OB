import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'database/strategy_learning.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_win_rate_by_asset():
    conn = get_connection()
    query = '''
        SELECT asset,
               COUNT(*) as total,
               SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
               ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
        GROUP BY asset
        ORDER BY win_rate DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_win_rate_by_hour():
    conn = get_connection()
    query = '''
        SELECT CAST(hour AS INTEGER) as hour,
               COUNT(*) as total,
               SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
               ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
        GROUP BY hour
        ORDER BY hour
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_general_stats():
    conn = get_connection()
    query = '''
        SELECT 
            COUNT(*) as total_trades,
            SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as total_wins,
            SUM(CASE WHEN result = 'LOSS' THEN 1 ELSE 0 END) as total_losses,
            ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df.iloc[0] if not df.empty else None

def get_recent_trades(limit=10):
    conn = get_connection()
    query = f'''
        SELECT id, asset, direction, result, mq, adx, bollinger_width, timestamp
        FROM market_context
        WHERE result != 'PENDENTE'
        ORDER BY id DESC
        LIMIT {limit}
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def show_dashboard():
    print("\n" + "=" * 60)
    print("📊 DASHBOARD DE PERFORMANCE")
    print("=" * 60)
    
    stats = get_general_stats()
    if stats is None or stats['total_trades'] == 0:
        print("⚠️ Ainda não há dados suficientes (0 trades confirmados).")
        return
    
    print(f"\n📈 Resumo Geral:")
    print(f"  Total de trades: {stats['total_trades']:.0f}")
    print(f"  Vitórias: {stats['total_wins']:.0f}")
    print(f"  Derrotas: {stats['total_losses']:.0f}")
    print(f"  Win Rate: {stats['win_rate']:.2f}%")
    
    df_asset = get_win_rate_by_asset()
    if not df_asset.empty:
        print("\n📊 Win Rate por Ativo:")
        for _, row in df_asset.iterrows():
            print(f"  {row['asset']}: {row['win_rate']:.2f}% ({row['wins']:.0f}/{row['total']:.0f})")
    
    df_hour = get_win_rate_by_hour()
    if not df_hour.empty:
        print("\n🕒 Win Rate por Hora:")
        for _, row in df_hour.iterrows():
            print(f"  {int(row['hour']):02d}h: {row['win_rate']:.2f}% ({row['wins']:.0f}/{row['total']:.0f})")
    
    df_recent = get_recent_trades(5)
    if not df_recent.empty:
        print("\n🔄 Últimos 5 trades:")
        for _, row in df_recent.iterrows():
            print(f"  {row['asset']} ({row['direction']}) → {row['result']} | MQ:{row['mq']:.0f} ADX:{row['adx']:.0f}")
    
    print("\n" + "=" * 60)
