import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'database/strategy_learning.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def update_priorities(min_trades=50, min_win_rate=65.0):
    """
    Analisa a base de dados e atualiza a tabela context_priorities
    com grupos que atingem min_trades e win_rate >= min_win_rate.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Identificar grupos com base nos dados atuais
    query = '''
        SELECT 
            MIN(mq) as mq_min, MAX(mq) as mq_max,
            MIN(adx) as adx_min, MAX(adx) as adx_max,
            MIN(bollinger_width) as bw_min, MAX(bollinger_width) as bw_max,
            COUNT(*) as total,
            ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
        GROUP BY 
            CASE 
                WHEN mq < 35 THEN 'Baixo'
                WHEN mq < 50 THEN 'Medio'
                ELSE 'Alto'
            END,
            CASE 
                WHEN adx < 25 THEN 'Baixo'
                WHEN adx < 40 THEN 'Medio'
                ELSE 'Alto'
            END,
            CASE 
                WHEN bollinger_width < 0.0002 THEN 'Baixo'
                WHEN bollinger_width < 0.0004 THEN 'Medio'
                ELSE 'Alto'
            END
        HAVING total >= ? AND win_rate >= ?
        ORDER BY win_rate DESC
    '''
    df = pd.read_sql_query(query, conn, params=(min_trades, min_win_rate))
    
    if df.empty:
        print(f"⚠️ Nenhum grupo com {min_trades}+ trades e win_rate >= {min_win_rate}%.")
        return 0
    
    # 2. Limpar prioridades antigas (apenas as que estão ativas)
    cursor.execute("UPDATE context_priorities SET active = 0")
    
    # 3. Inserir novos grupos
    inserted = 0
    now = int(datetime.now().timestamp())
    for _, row in df.iterrows():
        cursor.execute('''
            INSERT INTO context_priorities (
                mq_min, mq_max, adx_min, adx_max, bw_min, bw_max,
                priority_multiplier, total_trades, win_rate, created_at, updated_at, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            row['mq_min'], row['mq_max'],
            row['adx_min'], row['adx_max'],
            row['bw_min'], row['bw_max'],
            1.5,  # multiplicador base
            row['total'], row['win_rate'],
            now, now, 1
        ))
        inserted += 1
    
    conn.commit()
    conn.close()
    print(f"✅ {inserted} grupos prioritários registados.")
    return inserted

def get_priority_for_context(mq, adx, bw):
    """
    Verifica se um determinado conjunto de valores se enquadra num grupo prioritário.
    Retorna o multiplicador (ex: 1.5) ou 1.0 se não for prioritário.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT priority_multiplier
        FROM context_priorities
        WHERE active = 1
          AND mq_min <= ? AND mq_max >= ?
          AND adx_min <= ? AND adx_max >= ?
          AND bw_min <= ? AND bw_max >= ?
        LIMIT 1
    ''', (mq, mq, adx, adx, bw, bw))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 1.0

def get_all_priorities():
    """Retorna todos os grupos prioritários ativos."""
    conn = get_connection()
    df = pd.read_sql_query('''
        SELECT 
            mq_min, mq_max, adx_min, adx_max, bw_min, bw_max,
            priority_multiplier, total_trades, win_rate
        FROM context_priorities
        WHERE active = 1
        ORDER BY win_rate DESC
    ''', conn)
    conn.close()
    return df

def reset_priorities():
    """Desativa todos os grupos prioritários."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE context_priorities SET active = 0")
    conn.commit()
    conn.close()
    print("✅ Todos os grupos prioritários foram desativados.")
