import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

DB_PATH = 'database/strategy_learning.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def analyze_groups(min_trades=3):
    """
    Analisa grupos de contexto e retorna um DataFrame com:
    - mq_group, adx_group, bw_group
    - total trades, wins, win_rate
    - recomendação: 'RECOMENDADO' (win_rate >65%), 'BLOQUEAR' (win_rate <40%), 'NEUTRO'
    """
    conn = get_connection()
    query = '''
        SELECT 
            mq, adx, bollinger_width, result
        FROM market_context
        WHERE result != 'PENDENTE'
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if df.empty:
        return pd.DataFrame()
    
    # Criar grupos discretizados
    df['mq_group'] = pd.cut(df['mq'], bins=[0, 35, 50, 100], labels=['Baixo', 'Medio', 'Alto'])
    df['adx_group'] = pd.cut(df['adx'], bins=[0, 25, 40, 100], labels=['Baixo', 'Medio', 'Alto'])
    df['bw_group'] = pd.cut(df['bollinger_width'], bins=[0, 0.0002, 0.0004, 1], labels=['Baixo', 'Medio', 'Alto'])
    
    # Agrupar e calcular métricas
    grouped = df.groupby(['mq_group', 'adx_group', 'bw_group'], observed=False).agg(
        total=('result', 'count'),
        wins=('result', lambda x: (x == 'WIN').sum())
    ).reset_index()
    
    grouped['win_rate'] = (grouped['wins'] / grouped['total'] * 100).round(2)
    
    # Classificar grupos
    def classify(row):
        if row['total'] < min_trades:
            return 'DADOS_INSUFICIENTES'
        elif row['win_rate'] >= 65:
            return 'RECOMENDADO'
        elif row['win_rate'] < 40:
            return 'BLOQUEAR'
        else:
            return 'NEUTRO'
    
    grouped['classificacao'] = grouped.apply(classify, axis=1)
    
    return grouped.sort_values('win_rate', ascending=False)

def update_blacklist():
    """
    Atualiza a tabela blacklist com base na análise de grupos.
    (Ainda não implementado automaticamente – será manual por enquanto)
    """
    pass

def get_recommendations():
    """
    Retorna grupos recomendados (win_rate >= 65% e total >= 3).
    """
    df = analyze_groups()
    if df.empty:
        return []
    return df[df['classificacao'] == 'RECOMENDADO'].to_dict('records')

def get_blacklist_candidates():
    """
    Retorna grupos candidatos a blacklist (win_rate < 40% e total >= 3).
    """
    df = analyze_groups()
    if df.empty:
        return []
    return df[df['classificacao'] == 'BLOQUEAR'].to_dict('records')
