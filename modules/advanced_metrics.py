"""
modules/advanced_metrics.py
Métricas avançadas para aumentar a assertividade do robô:
- ATR (volatilidade)
- Suporte e Resistência (Pivot Points)
- Sentimento de notícias (VADER - simulado por enquanto)
"""
import pandas as pd
import numpy as np
from datetime import datetime

def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """
    Calcula o Average True Range (ATR) - medida de volatilidade.
    Retorna o valor do ATR atual.
    """
    high = df['high']
    low = df['low']
    close = df['close']
    
    # True Range = max(high - low, |high - prev_close|, |low - prev_close|)
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # ATR é a média móvel exponencial do True Range
    atr = true_range.ewm(span=period, adjust=False).mean()
    
    return atr.iloc[-1]  # Retorna o último valor

def calculate_pivot_points(df: pd.DataFrame) -> dict:
    """
    Calcula os Pivot Points diários com base no último candle completo.
    Retorna um dicionário com: PP (pivot), R1, R2, S1, S2.
    """
    # Usa os dados do penúltimo candle (assumindo que o último está incompleto)
    if len(df) < 2:
        return None
    
    # Pega o candle anterior (completo)
    prev = df.iloc[-2]
    high = prev['high']
    low = prev['low']
    close = prev['close']
    
    # Pivot Point clássico
    pp = (high + low + close) / 3
    r1 = 2 * pp - low
    r2 = pp + (high - low)
    s1 = 2 * pp - high
    s2 = pp - (high - low)
    
    return {
        'pivot': pp,
        'r1': r1,
        'r2': r2,
        's1': s1,
        's2': s2
    }

def check_support_resistance(current_price: float, pivots: dict, tolerance: float = 0.001) -> tuple:
    """
    Verifica se o preço atual está próximo de um suporte ou resistência.
    Retorna (perto_suporte, perto_resistencia, qual).
    """
    if pivots is None:
        return False, False, None
    
    perto_suporte = False
    perto_resistencia = False
    qual = None
    
    # Verifica se está perto de um suporte (S1 ou S2)
    if abs(current_price - pivots['s1']) / current_price < tolerance:
        perto_suporte = True
        qual = "S1"
    elif abs(current_price - pivots['s2']) / current_price < tolerance:
        perto_suporte = True
        qual = "S2"
    
    # Verifica se está perto de uma resistência (R1 ou R2)
    if abs(current_price - pivots['r1']) / current_price < tolerance:
        perto_resistencia = True
        qual = "R1"
    elif abs(current_price - pivots['r2']) / current_price < tolerance:
        perto_resistencia = True
        qual = "R2"
    
    return perto_suporte, perto_resistencia, qual

def get_sentiment_score() -> float:
    """
    Retorna o score de sentimento das notícias.
    Por enquanto, simula um valor aleatório entre -1 e 1.
    Depois vamos conectar com uma API de notícias (ex: NewsAPI).
    """
    # Simulação: gera um número aleatório entre -1 e 1
    # Em produção, isso viria de uma API de notícias com VADER
    import random
    return random.uniform(-1, 1)
