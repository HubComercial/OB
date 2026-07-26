import sqlite3
import json
import time
from datetime import datetime

DB_PATH = 'database/strategy_learning.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def save_context(data):
    print(f"[AI] Salvando contexto para {data.get("asset")} ({data.get("direction")})")
    """
    Guarda o contexto completo de um trade antes da execução.
    data é um dicionário com as chaves esperadas.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO market_context (
            timestamp, asset, direction, result, score,
            mq, adx, atr, bollinger_width, rsi, macd,
            volume_ratio, trend, volatility, session,
            spread, day_of_week, hour, news_flag, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get('timestamp'),
        data.get('asset'),
        data.get('direction'),
        'PENDENTE',  # resultado inicial
        data.get('score'),
        data.get('mq'),
        data.get('adx'),
        data.get('atr'),
        data.get('bollinger_width'),
        data.get('rsi'),
        data.get('macd'),
        data.get('volume_ratio'),
        data.get('trend'),
        data.get('volatility'),
        data.get('session'),
        data.get('spread'),
        data.get('day_of_week'),
        data.get('hour'),
        data.get('news_flag'),
        data.get('confidence')
    ))
    conn.commit()
    last_id = cursor.lastrowid
    conn.close()
    return last_id

def update_result(trade_id, result, exit_price=None):
    """
    Atualiza o resultado de um trade após confirmação.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE market_context
        SET result = ?
        WHERE id = ?
    ''', (result, trade_id))
    conn.commit()
    conn.close()

def get_context_groups():
    """
    Retorna grupos de contexto para análise (a ser implementado).
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            CASE 
                WHEN mq < 35 THEN 'baixo'
                WHEN mq < 50 THEN 'médio'
                ELSE 'alto'
            END as mq_group,
            CASE 
                WHEN adx < 25 THEN 'baixo'
                WHEN adx < 40 THEN 'médio'
                ELSE 'alto'
            END as adx_group,
            COUNT(*) as total,
            SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
        GROUP BY mq_group, adx_group
        ORDER BY win_rate DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows
