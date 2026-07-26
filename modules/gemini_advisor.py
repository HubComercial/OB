import sqlite3
import pandas as pd
import json
from datetime import datetime
import os
import requests

DB_PATH = 'database/strategy_learning.db'
REPORTS_DB = 'database/ai_reports.db'

API_KEY = os.environ.get('GEMINI_API_KEY', '')

def get_connection():
    return sqlite3.connect(DB_PATH)

def get_reports_connection():
    conn = sqlite3.connect(REPORTS_DB)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS ai_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date INTEGER,
            summary TEXT,
            recommendations TEXT,
            raw_response TEXT,
            applied INTEGER DEFAULT 0
        )
    ''')
    return conn

def collect_stats(min_trades=3):
    conn = get_connection()
    
    df_general = pd.read_sql_query('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) as wins,
            ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
    ''', conn)
    
    df_assets = pd.read_sql_query(f'''
        SELECT asset,
               COUNT(*) as total,
               ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
        GROUP BY asset
        HAVING total >= {min_trades}
        ORDER BY win_rate DESC
        LIMIT 5
    ''', conn)
    
    df_hours = pd.read_sql_query(f'''
        SELECT hour,
               COUNT(*) as total,
               ROUND(100.0 * SUM(CASE WHEN result = 'WIN' THEN 1 ELSE 0 END) / COUNT(*), 2) as win_rate
        FROM market_context
        WHERE result != 'PENDENTE'
        GROUP BY hour
        HAVING total >= {min_trades}
        ORDER BY win_rate DESC
        LIMIT 5
    ''', conn)
    
    df_indicators = pd.read_sql_query('''
        SELECT 
            AVG(mq) as avg_mq,
            AVG(adx) as avg_adx,
            AVG(atr) as avg_atr,
            AVG(bollinger_width) as avg_bw,
            AVG(score) as avg_score
        FROM market_context
        WHERE result != 'PENDENTE'
    ''', conn)
    
    conn.close()
    
    stats = {
        'total_trades': df_general['total'].iloc[0] if not df_general.empty else 0,
        'win_rate': df_general['win_rate'].iloc[0] if not df_general.empty else 0.0,
        'top_assets': df_assets.to_dict('records') if not df_assets.empty else [],
        'top_hours': df_hours.to_dict('records') if not df_hours.empty else [],
        'avg_mq': df_indicators['avg_mq'].iloc[0] if not df_indicators.empty else 0.0,
        'avg_adx': df_indicators['avg_adx'].iloc[0] if not df_indicators.empty else 0.0,
        'avg_atr': df_indicators['avg_atr'].iloc[0] if not df_indicators.empty else 0.0,
        'avg_bw': df_indicators['avg_bw'].iloc[0] if not df_indicators.empty else 0.0,
        'avg_score': df_indicators['avg_score'].iloc[0] if not df_indicators.empty else 0.0
    }
    return stats

def build_prompt(stats):
    prompt = f"""
    Você é um consultor de trading para um robô de opções binárias que usa análise técnica.
    Com base nas estatísticas abaixo, forneça recomendações práticas para melhorar a performance.
    
    Estatísticas atuais:
    - Total de trades: {stats['total_trades']}
    - Win Rate: {stats['win_rate']:.2f}%
    - MQ médio: {stats['avg_mq']:.2f}
    - ADX médio: {stats['avg_adx']:.2f}
    - ATR médio: {stats['avg_atr']:.6f}
    - BW médio: {stats['avg_bw']:.6f}
    - Score médio: {stats['avg_score']:.2f}
    
    Top ativos por win rate (com pelo menos 3 trades):
    {json.dumps(stats['top_assets'], indent=2)}
    
    Top horas por win rate (com pelo menos 3 trades):
    {json.dumps(stats['top_hours'], indent=2)}
    
    Com base nesses dados, sugira:
    1. Ajustes de filtros (MQ, ADX, BW, Score) para melhorar o win rate.
    2. Prioridade de ativos (quais manter, quais evitar).
    3. Horários recomendados para operar.
    4. Qualquer outra observação relevante.
    
    Seja específico e prático. Forneça recomendações num formato que possa ser implementado.
    """
    return prompt

def ask_gemini(stats):
    if not API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {
        "contents": [{
            "parts": [{"text": build_prompt(stats)}]
        }]
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"❌ Erro na API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro ao chamar Gemini: {e}")
        return None

def save_report(stats, response):
    conn = get_reports_connection()
    cursor = conn.cursor()
    now = int(datetime.now().timestamp())
    cursor.execute('''
        INSERT INTO ai_reports (report_date, summary, recommendations, raw_response)
        VALUES (?, ?, ?, ?)
    ''', (now, json.dumps(stats), json.dumps({"recommendations": response}), response))
    conn.commit()
    conn.close()
    print("✅ Relatório guardado em ai_reports.db")

def run_analysis():
    if not API_KEY:
        print("❌ GEMINI_API_KEY não definida. Exporta a chave primeiro.")
        return
    stats = collect_stats()
    if stats['total_trades'] < 3:
        print("⚠️ Dados insuficientes (mínimo 3 trades confirmados).")
        return
    print("📤 Enviando para Gemini...")
    response = ask_gemini(stats)
    if response:
        print("✅ Resposta recebida.")
        save_report(stats, response)
        print("\n📋 RECOMENDAÇÕES DO GEMINI:\n")
        print(response)
    else:
        print("❌ Não foi possível obter resposta do Gemini.")

if __name__ == "__main__":
    run_analysis()
