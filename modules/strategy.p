exyimport pandas as pd
import datetime
import json
import os
import numpy as np
from .indicators import (
    calculate_ema, calculate_cci, calculate_macd,
    calculate_rsi, calculate_bollinger_bands, calculate_volume_ma
)
from .advanced_metrics import (
    calculate_atr, calculate_pivot_points,
    check_support_resistance
)
from config import (
    TIMEFRAME_CONFIGS,
    CCI_PERIOD, MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    ATR_MAX, ATR_PERIOD,
    OVERLAY_START, OVERLAY_END, OTC_WEEKEND,
    ASSET, BB_PERIOD, VOLUME_PERIOD
)

WEIGHTS_FILE = "data/weights.json"

def load_weights():
    """Carrega os pesos do ficheiro weights.json, ou usa os padrão se não existir."""
    if os.path.isfile(WEIGHTS_FILE):
        with open(WEIGHTS_FILE, "r") as f:
            return json.load(f)
    # Pesos padrão (caso não exista ficheiro)
    return {
        'buy': {
            'ema_fast': 15,
            'ema_trend': 15,
            'macd': 15,
            'cci': 15,
            'rsi': 10,
            'volume': 10,
            'bollinger': 10,
            'sr': 5,
            'atr_penalty': -20
        },
        'sell': {
            'ema_fast': 15,
            'ema_trend': 15,
            'macd': 15,
            'cci': 15,
            'rsi': 10,
            'volume': 10,
            'bollinger': 10,
            'sr': 5,
            'atr_penalty': -20
        }
    }

# Carrega os pesos uma vez no início
WEIGHTS = load_weights()

def is_overlay_time():
    now = datetime.datetime.utcnow()
    if now.weekday() >= 5 and OTC_WEEKEND:
        return True
    return OVERLAY_START <= now.hour <= OVERLAY_END

def calculate_market_quality(atr, atr_min, atr_max, current_price, ema_trend):
    """Market Quality: avalia se o mercado está em condições favoráveis para operar."""
    score = 40
    if atr is None or np.isnan(atr):
        return 0

    if atr_min <= atr <= atr_max * 0.7:
        score += 20
    elif atr < atr_min:
        score -= 20
    elif atr > atr_max:
        score -= 10

    if current_price > ema_trend:
        score += 15
    else:
        score += 5

    return max(0, min(100, score))

def generate_signal(df: pd.DataFrame, timeframe: int) -> dict:
    df = df.reset_index(drop=True)

    if not is_overlay_time():
        return {
            'signal': 'NEUTRO',
            'market_quality': 0,
            'score_buy': 0,
            'score_sell': 0,
            'reasons_buy': [],
            'reasons_sell': [],
            'filters_blocked': ['Fora do overlay']
        }

    if len(df) < 30:
        return {
            'signal': 'NEUTRO',
            'market_quality': 0,
            'score_buy': 0,
            'score_sell': 0,
            'reasons_buy': [],
            'reasons_sell': [],
            'filters_blocked': ['Dados insuficientes']
        }

    cfg = TIMEFRAME_CONFIGS.get(timeframe, TIMEFRAME_CONFIGS[1])
    ema_fast_period = cfg['ema_fast']
    ema_trend_period = cfg['ema_trend']
    rsi_low = cfg['rsi_low']
    rsi_high = cfg['rsi_high']
    atr_min = cfg['atr_min']
    bollinger_std = cfg['bollinger_std']

    close = df['close']
    open_price = df['open']
    high = df['high']
    low = df['low']

    ema_fast = calculate_ema(close, ema_fast_period)
    ema_trend = calculate_ema(close, ema_trend_period)
    cci = calculate_cci(high, low, close, CCI_PERIOD)
    macd_line, signal_line, _ = calculate_macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    boll_upper, boll_mid, boll_lower = calculate_bollinger_bands(close, BB_PERIOD, bollinger_std)
    rsi = calculate_rsi(close, 14)

    has_volume = 'volume' in df.columns
    if has_volume:
        vol_ma = calculate_volume_ma(df['volume'], VOLUME_PERIOD)
        last_vol = df['volume'].iloc[-1]
        last_vol_ma = vol_ma.iloc[-1]
    else:
        last_vol = None
        last_vol_ma = None

    atr = calculate_atr(df, ATR_PERIOD)
    pivots = calculate_pivot_points(df)
    current_price = close.iloc[-1]
    perto_suporte, perto_resistencia, qual = check_support_resistance(current_price, pivots)

    last_close = close.iloc[-1]
    last_open = open_price.iloc[-1]
    last_ema_fast = ema_fast.iloc[-1]
    prev_ema_fast = ema_fast.iloc[-2]
    last_ema_trend = ema_trend.iloc[-1]
    last_cci = cci.iloc[-1]
    last_macd = macd_line.iloc[-1]
    last_signal = signal_line.iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_boll_lower = boll_lower.iloc[-1]
    last_boll_upper = boll_upper.iloc[-1]
    last_vol_ok = (not has_volume) or (last_vol > last_vol_ma)

    market_quality = calculate_market_quality(atr, atr_min, ATR_MAX, current_price, last_ema_trend)

    # ===== CARREGA PESOS PARA BUY E SELL =====
    w_buy = WEIGHTS.get('buy', {})
    w_sell = WEIGHTS.get('sell', {})

    # ===== SCORE BUY =====
    score_buy = 0
    reasons_buy = []

    if last_close > last_ema_fast:
        score_buy += w_buy.get('ema_fast', 15); reasons_buy.append("EMA fast bullish")
    if last_close > last_ema_trend:
        score_buy += w_buy.get('ema_trend', 15); reasons_buy.append("EMA trend bullish")
    if last_macd > last_signal:
        score_buy += w_buy.get('macd', 15); reasons_buy.append("MACD bullish")
    if last_cci >= 50:
        score_buy += w_buy.get('cci', 15); reasons_buy.append("CCI positivo")
    if 45 <= last_rsi <= 65:
        score_buy += w_buy.get('rsi', 10); reasons_buy.append("RSI favorável (tendência)")
    if last_vol_ok:
        score_buy += w_buy.get('volume', 10); reasons_buy.append("Volume OK")
    if last_close <= last_boll_lower * 1.0005:
        score_buy += w_buy.get('bollinger', 10); reasons_buy.append("Bollinger inferior (suporte)")
    if perto_suporte:
        score_buy += w_buy.get('sr', 5); reasons_buy.append("Perto do suporte")
    if atr < atr_min:
        score_buy += w_buy.get('atr_penalty', -20); reasons_buy.append("ATR baixo (-20)")

    # ===== SCORE SELL =====
    score_sell = 0
    reasons_sell = []

    if last_close < last_ema_fast:
        score_sell += w_sell.get('ema_fast', 15); reasons_sell.append("EMA fast bearish")
    if last_close < last_ema_trend:
        score_sell += w_sell.get('ema_trend', 15); reasons_sell.append("EMA trend bearish")
    if last_macd < last_signal:
        score_sell += w_sell.get('macd', 15); reasons_sell.append("MACD bearish")
    if last_cci <= -50:
        score_sell += w_sell.get('cci', 15); reasons_sell.append("CCI negativo")
    if 35 <= last_rsi <= 55:
        score_sell += w_sell.get('rsi', 10); reasons_sell.append("RSI favorável (tendência baixa)")
    if last_vol_ok:
        score_sell += w_sell.get('volume', 10); reasons_sell.append("Volume OK")
    if last_close >= last_boll_upper * 0.9995:
        score_sell += w_sell.get('bollinger', 10); reasons_sell.append("Bollinger superior (resistência)")
    if perto_resistencia:
        score_sell += w_sell.get('sr', 5); reasons_sell.append("Perto da resistência")
    if atr < atr_min:
        score_sell += w_sell.get('atr_penalty', -20); reasons_sell.append("ATR baixo (-20)")

    score_buy = max(0, min(100, score_buy))
    score_sell = max(0, min(100, score_sell))

    if market_quality < 30:
        signal = "NEUTRO"
    elif score_buy > score_sell and score_buy >= 70:
        signal = "COMPRA"
    elif score_sell > score_buy and score_sell >= 70:
        signal = "VENDA"
    else:
        signal = "NEUTRO"

    confidence = max(score_buy, score_sell) if signal != "NEUTRO" else 0

    return {
        'signal': signal,
        'confidence': confidence,
        'market_quality': market_quality,
        'score_buy': score_buy,
        'score_sell': score_sell,
        'reasons_buy': reasons_buy,
        'reasons_sell': reasons_sell,
        'filters_blocked': []
    }
