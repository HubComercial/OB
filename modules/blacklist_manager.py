import sqlite3
import pandas as pd
from datetime import datetime

DB_PATH = 'database/strategy_learning.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def update_blacklist(min_trades=30, max_win_rate=40.0):
    """
    Identifica contextos com win_rate < max_win_rate e total >= min_trades,
    e adiciona à blacklist (tabela blacklist).
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Identificar grupos problemáticos
    query = '''
        SELECT 
            CASE 
                WHEN mq < 35 THEN 'Baixo'
                WHEN mq < 50 THEN 'Medio'
                ELSE 'Alto'
            END as mq_group,
            CASE 
                WHEN adx < 25 THEN 'Baixo'
                WHEN adx < 40 THEN 'Medio'
                ELSE 'Alto'
            END as adx_group,
            CASE 
                WHEN bollinger_width < 0.0002 THEN 'Baixo'
                WHEN bollinger_width < 0.0004 THEN 'Medio'
                ELSE 'Alto'
            END as bw_group,
            COUNT(*) as total,
            ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
        GROUP BY mq_group, adx_group, bw_group
        HAVING total >= ? AND win_rate < ?
    '''
    df = pd.read_sql_query(query, conn, params=(min_trades, max_win_rate))
    
    if df.empty:
        print(f"✅ Nenhum contexto com win_rate < {max_win_rate}% e {min_trades}+ trades.")
        return 0
    
    # 2. Inserir na blacklist (ou atualizar existentes)
    now = int(datetime.now().timestamp())
    inserted = 0
    for _, row in df.iterrows():
        context_desc = f"MQ:{row['mq_group']}, ADX:{row['adx_group']}, BW:{row['bw_group']}"
        cursor.execute('''
            INSERT INTO blacklist (context_description, reason, blocked_until, active)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(context_description) DO UPDATE SET
                reason = excluded.reason,
                blocked_until = excluded.blocked_until,
                active = 1
        ''', (
            context_desc,
            f"win_rate {row['win_rate']}% com {row['total']} trades",
            now + (7 * 24 * 3600),  # bloqueio por 7 dias
            1
        ))
        inserted += 1
    
    conn.commit()
    conn.close()
    print(f"🚫 {inserted} contextos adicionados à blacklist.")
    return inserted

def is_blocked(mq, adx, bw):
    """
    Verifica se um determinado contexto (MQ, ADX, BW) está na blacklist.
    Retorna True se estiver bloqueado.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Determinar grupos
    mq_group = 'Baixo' if mq < 35 else 'Medio' if mq < 50 else 'Alto'
    adx_group = 'Baixo' if adx < 25 else 'Medio' if adx < 40 else 'Alto'
    bw_group = 'Baixo' if bw < 0.0002 else 'Medio' if bw < 0.0004 else 'Alto'
    context_desc = f"MQ:{mq_group}, ADX:{adx_group}, BW:{bw_group}"
    
    cursor.execute('''
        SELECT active FROM blacklist
        WHERE context_description = ? AND active = 1
        AND (blocked_until IS NULL OR blocked_until > ?)
    ''', (context_desc, int(datetime.now().timestamp())))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def get_blacklist():
    """Retorna a lista de contextos bloqueados ativos."""
    conn = get_connection()
    df = pd.read_sql_query('''
        SELECT context_description, reason, blocked_until
        FROM blacklist
        WHERE active = 1
        AND (blocked_until IS NULL OR blocked_until > ?)
        ORDER BY context_description
    ''', conn, params=(int(datetime.now().timestamp()),))
    conn.close()
    return df
