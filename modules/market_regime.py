import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'database/strategy_learning.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_win_rate_last_n(n):
    """Calcula win rate dos últimos N trades."""
    conn = get_connection()
    query = f'''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins
        FROM (
            SELECT result FROM market_context
            WHERE result != 'PENDENTE'
            ORDER BY id DESC
            LIMIT {n}
        )
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    if df.empty or df['total'].iloc[0] == 0:
        return None
    total = df['total'].iloc[0]
    wins = df['wins'].iloc[0]
    return (wins / total) * 100

def detect_regime_change(short_window=100, long_window=300, threshold=20):
    """
    Compara win rate dos últimos `short_window` vs últimos `long_window` trades.
    Se diferença > threshold, retorna True e a diferença.
    """
    short_wr = get_win_rate_last_n(short_window)
    long_wr = get_win_rate_last_n(long_window)
    
    if short_wr is None or long_wr is None:
        return False, 0, short_wr, long_wr
    
    diff = short_wr - long_wr
    if abs(diff) > threshold:
        return True, diff, short_wr, long_wr
    return False, diff, short_wr, long_wr

def generate_regime_report():
    """Gera um relatório simples sobre a mudança de regime."""
    changed, diff, short, long = detect_regime_change()
    print("📊 RELATÓRIO DE REGIME DE MERCADO")
    print("=" * 50)
    print(f"  Win Rate (últimos 100): {short:.2f}%" if short else "  Dados insuficientes")
    print(f"  Win Rate (últimos 300): {long:.2f}%" if long else "  Dados insuficientes")
    if changed:
        print(f"  ⚠️ MUDANÇA DE REGIME DETETADA! Diferença: {diff:.2f}%")
        print(f"  {'🔻 Queda' if diff < 0 else '🔺 Subida'} de {abs(diff):.2f}%")
    else:
        print("  ✅ Mercado estável (sem alteração significativa).")
    print("=" * 50)
