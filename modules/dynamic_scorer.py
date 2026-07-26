import sqlite3
import pandas as pd
import numpy as np
from scipy.stats import pointbiserialr
import json
import os

DB_PATH = 'database/strategy_learning.db'
WEIGHTS_FILE = 'data/weights.json'

def get_connection():
    return sqlite3.connect(DB_PATH)

def load_current_weights():
    """Carrega os pesos atuais do ficheiro weights.json"""
    try:
        with open(WEIGHTS_FILE, 'r') as f:
            data = json.load(f)
            return data.get('buy', {}), data.get('sell', {})
    except:
        # Pesos padrão caso o ficheiro não exista
        default = {
            'ema_fast': 15,
            'ema_trend': 15,
            'macd': 15,
            'cci': 15,
            'rsi': 10,
            'volume': 10,
            'bollinger': 10,
            'sr': 5
        }
        return default, default

def calculate_indicator_importance(min_trades=10):
    """
    Calcula a correlação entre cada indicador e o resultado (WIN/LOSS).
    Retorna um dicionário com a importância relativa de cada indicador.
    """
    conn = get_connection()
    query = '''
        SELECT 
            score, mq, adx, atr, bollinger_width, rsi, macd, volume_ratio,
            CASE WHEN result = 'WIN' THEN 1 ELSE 0 END as target
        FROM market_context
        WHERE result != 'PENDENTE'
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    if len(df) < min_trades:
        return None, f"⚠️ Dados insuficientes: {len(df)} trades (mínimo {min_trades})"
    
    # Indicadores a analisar
    indicators = ['mq', 'adx', 'atr', 'bollinger_width', 'rsi', 'macd', 'volume_ratio']
    
    correlations = {}
    for col in indicators:
        if col in df.columns and df[col].nunique() > 1:
            # Correlação point-biserial (adequada para variável binária)
            corr, p_value = pointbiserialr(df[col], df['target'])
            correlations[col] = abs(corr)  # Usamos o valor absoluto da correlação
        else:
            correlations[col] = 0.0
    
    # Normalizar para que a soma seja 100
    total = sum(correlations.values())
    if total == 0:
        return None, "⚠️ Nenhuma correlação significativa encontrada."
    
    importance = {k: (v / total) * 100 for k, v in correlations.items()}
    
    # Mapear para os nomes dos indicadores usados no weights.json
    mapping = {
        'mq': 'mq',
        'adx': 'adx',
        'atr': 'atr',
        'bollinger_width': 'bollinger',
        'rsi': 'rsi',
        'macd': 'macd',
        'volume_ratio': 'volume'
    }
    
    # Adicionar indicadores que não estão na correlação (ex: sr)
    # Manter peso fixo para sr por enquanto
    importance['sr'] = 5.0
    
    # Re-normalizar para incluir sr
    total_ajustado = sum(importance.values())
    for k in importance:
        importance[k] = (importance[k] / total_ajustado) * 100
    
    # Converter para o formato do weights.json
    result = {}
    for key, value in importance.items():
        if key in mapping:
            result[mapping[key]] = round(value, 2)
        else:
            result[key] = round(value, 2)
    
    return result, f"✅ Análise concluída com {len(df)} trades."

def get_weight_recommendations():
    """
    Retorna uma sugestão de novos pesos baseada na correlação dos indicadores.
    """
    new_weights, msg = calculate_indicator_importance()
    if new_weights is None:
        print(msg)
        return None
    
    current_buy, current_sell = load_current_weights()
    
    print("📊 RECOMENDAÇÃO DE PESOS DINÂMICOS")
    print("=" * 50)
    print(f"{'Indicador':<15} | {'Peso Atual':>12} | {'Peso Sugerido':>14} | {'Diferença':>10}")
    print("-" * 60)
    
    suggestions = {}
    for indicator in ['ema_fast', 'ema_trend', 'macd', 'cci', 'rsi', 'volume', 'bollinger', 'sr']:
        current = current_buy.get(indicator, 10.0)
        # Mapear do nome do indicador para o nome usado na correlação
        map_to_corr = {
            'ema_fast': None,  # Não está na correlação atual
            'ema_trend': None,
            'macd': 'macd',
            'cci': None,
            'rsi': 'rsi',
            'volume': 'volume',
            'bollinger': 'bollinger_width',
            'sr': None
        }
        corr_key = map_to_corr.get(indicator)
        if corr_key and corr_key in new_weights:
            suggested = new_weights[corr_key]
        elif indicator in new_weights:
            suggested = new_weights[indicator]
        else:
            suggested = current  # manter o mesmo
        
        # Ajustar para que a soma seja 100
        diff = suggested - current
        print(f"{indicator:<15} | {current:>12.2f} | {suggested:>14.2f} | {diff:>+10.2f}")
        suggestions[indicator] = suggested
    
    print("=" * 50)
    print("📌 Para aplicar estas sugestões, edite o ficheiro data/weights.json")
    print("   ou execute o comando de atualização automática (após aprovação).")
    
    return suggestions

def apply_weights_suggestion(suggestions, dry_run=True):
    """
    Aplica as sugestões de pesos ao ficheiro weights.json.
    Se dry_run=True, apenas simula (não altera).
    """
    if suggestions is None:
        return
    
    with open(WEIGHTS_FILE, 'r') as f:
        data = json.load(f)
    
    if dry_run:
        print("🔍 SIMULAÇÃO (nenhuma alteração foi feita):")
        for k, v in suggestions.items():
            print(f"  {k}: {v:.2f}")
        return
    
    # Atualizar os pesos
    if 'buy' in data:
        for k, v in suggestions.items():
            if k in data['buy']:
                data['buy'][k] = v
    if 'sell' in data:
        for k, v in suggestions.items():
            if k in data['sell']:
                data['sell'][k] = v
    
    data['version'] = data.get('version', 0) + 1
    data['updated_at'] = pd.Timestamp.now().isoformat()
    
    with open(WEIGHTS_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Pesos atualizados (versão {data['version']}).")
