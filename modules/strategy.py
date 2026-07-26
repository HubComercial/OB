import pandas as pd
import datetime
import json

def get_asset_config(asset):
    """Carrega configurações específicas para um ativo (fallback para globais)."""
    try:
        import json
        import os
        with open("config_assets.json", "r") as f:
            config = json.load(f)
        return config.get(asset, {})
    except:
        return {}

# Função para obter um parâmetro específico (fallback)
def get_param(asset, param, default):
    config = get_asset_config(asset)
    return config.get(param, default)
import os
import hashlib
import copy
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
    BB_PERIOD, VOLUME_PERIOD,
    SCORE_WEIGHTS,
    MARKET_QUALITY_MIN,
    ADX_MIN,
    BOLLINGER_WIDTH_MIN
)

WEIGHTS_FILE = "data/weights.json"
_weights_cache = None
_weights_hash = None
_weights_mtime = None

def get_file_hash(filepath):
    if not os.path.isfile(filepath):
        return None
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def load_weights():
    global _weights_cache, _weights_hash, _weights_mtime
    try:
        current_mtime = os.stat(WEIGHTS_FILE).st_mtime
    except OSError:
        current_mtime = None
    if _weights_cache is not None and current_mtime is not None and current_mtime == _weights_mtime:
        return _weights_cache
    current_hash = get_file_hash(WEIGHTS_FILE) if current_mtime is not None else None
    if _weights_cache is not None and current_hash is not None and _weights_hash == current_hash:
        _weights_mtime = current_mtime
        return _weights_cache
    try:
        if os.path.isfile(WEIGHTS_FILE):
            with open(WEIGHTS_FILE, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict) and 'buy' in data and 'sell' in data:
                    _weights_cache = data
                    _weights_hash = current_hash
                    _weights_mtime = current_mtime
                    return _weights_cache
    except (json.JSONDecodeError, KeyError, TypeError):
        print("⚠️ weights.json corrompido ou inválido. Usando pesos padrão.")
    default_weights = {
        'version': 1,
        'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'buy': copy.deepcopy(SCORE_WEIGHTS),
        'sell': copy.deepcopy(SCORE_WEIGHTS)
    }
    _weights_cache = default_weights
    _weights_hash = current_hash
    _weights_mtime = current_mtime
    return _weights_cache

def is_overlay_time():
    now = datetime.datetime.now(datetime.timezone.utc)
    if now.weekday() >= 5 and OTC_WEEKEND:
        return True
    return OVERLAY_START <= now.hour <= OVERLAY_END

def calculate_market_quality(atr, atr_min, atr_max, current_price, ema_trend):
    if atr is None or np.isnan(atr):
        return 0
    score = 40
    if atr_min <= atr <= atr_max * 0.7:
        score += 20
    elif atr < atr_min:
        score -= 20
    elif atr_max * 0.7 < atr <= atr_max:
        score += 5
    elif atr > atr_max:
        score -= 10
    if current_price > ema_trend:
        score += 15
    else:
        score += 5
    return max(0, min(100, score))

def _has_valid_indicators(*values):
    return all(pd.notna(v) for v in values)

def calculate_side_score(conditions, weights):
    score = 0
    max_score = 0
    reasons = []
    for key, condition, reason, default_weight in conditions:
        w = weights.get(key, default_weight)
        max_score += w
        if condition:
            score += w
            reasons.append(reason)
    return score, max_score, reasons

def calculate_adx(df, period=14):
    high = df['high']
    low = df['low']
    close = df['close']

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()

    up_move = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    plus_dm_series = pd.Series(plus_dm, index=df.index)
    minus_dm_series = pd.Series(minus_dm, index=df.index)

    plus_di = 100 * (plus_dm_series.rolling(window=period).mean() / atr)
    minus_di = 100 * (minus_dm_series.rolling(window=period).mean() / atr)

    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.rolling(window=period).mean()

    return adx

def generate_signal(df: pd.DataFrame, timeframe: int, asset: str) -> dict:
    df = df.reset_index(drop=True)
    empty_result = {
        'signal': 'NEUTRO',
        'market_quality': 0,
        'score_buy': 0,
        'score_sell': 0,
        'max_score_buy': 0,
        'max_score_sell': 0,
        'confidence': 0,
        'reasons_buy': [],
        'reasons_sell': [],
        'filters_blocked': [],
        'filters_detailed': {},  # NOVO: detalhes de cada filtro
        'close': 0.0,
        'ema_fast': 0.0,
        'ema_trend': 0.0,
        'rsi': 0.0,
        'macd': 0.0,
        'cci': 0.0,
        'atr': 0.0,
        'bollinger_width': 0.0,
        'distancia_ema': 0.0,
        'trend_direction': '',
        'volume_ratio': 0.0
    }

    if not is_overlay_time():
        empty_result['filters_blocked'] = ['Fora do overlay']
        return empty_result

    if len(df) < 30:
        empty_result['filters_blocked'] = ['Dados insuficientes']
        return empty_result

    required_columns = {"open", "high", "low", "close"}
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        empty_result['filters_blocked'] = [f'Colunas em falta: {sorted(missing)}']
        return empty_result

    cfg = TIMEFRAME_CONFIGS.get(timeframe)
    if cfg is None:
        default_tf = list(TIMEFRAME_CONFIGS.keys())[0] if TIMEFRAME_CONFIGS else 5
        cfg = TIMEFRAME_CONFIGS.get(default_tf, {})
        if not cfg:
            empty_result['filters_blocked'] = [f'Sem configuração para timeframe {timeframe}']
            return empty_result

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
    adx = calculate_adx(df, 14)

    has_volume = 'volume' in df.columns
    if has_volume:
        vol_ma = calculate_volume_ma(df['volume'], VOLUME_PERIOD)
        last_vol = df['volume'].iloc[-1]
        last_vol_ma = vol_ma.iloc[-1]
        volume_ratio = last_vol / last_vol_ma if last_vol_ma > 0 else 1.0
    else:
        last_vol = None
        last_vol_ma = None
        volume_ratio = 1.0

    atr = calculate_atr(df, ATR_PERIOD)
    pivots = calculate_pivot_points(df)
    current_price = close.iloc[-1]
    perto_suporte, perto_resistencia, _ = check_support_resistance(current_price, pivots)

    last_close = close.iloc[-1]
    last_open = open_price.iloc[-1]
    last_ema_fast = ema_fast.iloc[-1]
    last_ema_trend = ema_trend.iloc[-1]
    last_cci = cci.iloc[-1]
    last_macd = macd_line.iloc[-1]
    last_signal = signal_line.iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_boll_lower = boll_lower.iloc[-1]
    last_boll_upper = boll_upper.iloc[-1]
    last_adx = adx.iloc[-1] if not adx.empty else 0

    bollinger_width = (boll_upper.iloc[-1] - boll_lower.iloc[-1]) / boll_mid.iloc[-1] if boll_mid.iloc[-1] != 0 else 0
    print(f"[BW_DEBUG_FORCADO] asset={asset} upper={boll_upper.iloc[-1] if len(boll_upper)>0 else 0} lower={boll_lower.iloc[-1] if len(boll_lower)>0 else 0} mid={boll_mid.iloc[-1] if len(boll_mid)>0 else 0}")
    print(f"[BW_DEBUG] {asset} upper={boll_upper.iloc[-1]:.8f} lower={boll_lower.iloc[-1]:.8f} mid={boll_mid.iloc[-1]:.8f} BW={bollinger_width:.8f}")
    print(f"[BW_DEBUG] {asset} upper={boll_upper.iloc[-1]:.8f} lower={boll_lower.iloc[-1]:.8f} mid={boll_mid.iloc[-1]:.8f} BW={bollinger_width:.8f}")

    # ===== DIAGNÓSTICO =====
    print(f"🔍 DIAG: {asset} | candles={len(df)} | ATR={atr:.6f} | MQ={calculate_market_quality(atr, atr_min, ATR_MAX, current_price, last_ema_trend)} | ADX={last_adx:.1f} | BW={bollinger_width:.4f}")

    # ===== VALIDAÇÃO DOS INDICADORES =====
    if not _has_valid_indicators(
        last_close, last_ema_fast, last_ema_trend, last_cci,
        last_macd, last_signal, last_rsi, last_boll_lower,
        last_boll_upper, atr
    ):
        empty_result['filters_blocked'] = ['Indicadores insuficientes (NaN)']
        return empty_result

    last_vol_ok = (not has_volume) or (last_vol > last_vol_ma)

    # ===== FILTROS DETALHADOS =====
    filters_detailed = {}

    # Market Quality
    mq = calculate_market_quality(atr, atr_min, ATR_MAX, current_price, last_ema_trend)
    filters_detailed['MQ'] = {'value': mq, 'min': mq_min, 'pass': mq >= mq_min}

    # ADX
    filters_detailed['ADX'] = {'value': last_adx, 'min': adx_min, 'pass': last_adx >= adx_min}

    # Bollinger Width
    filters_detailed['BW'] = {'value': bollinger_width, 'min': bollinger_width_min, 'pass': bollinger_width >= bollinger_width_min}

    # Score (será calculado depois)
    # Vamos calcular os scores primeiro

    weights = load_weights()
    w_buy = weights.get('buy', {})
    w_sell = weights.get('sell', {})

    buy_conditions = [
        ('ema_fast',  last_close > last_ema_fast,                  "EMA fast bullish",              15),
        ('ema_trend', last_close > last_ema_trend,                 "EMA trend bullish",              15),
        ('macd',      last_macd > last_signal,                     "MACD bullish",                   15),
        ('cci',       last_cci >= 50,                               "CCI positivo",                   15),
        ('rsi',       45 <= last_rsi <= 65,                         "RSI favorável (tendência)",      10),
        ('volume',    last_vol_ok,                                  "Volume OK",                      10),
        ('bollinger', last_close <= last_boll_lower * 1.0005,       "Bollinger inferior (suporte)",   10),
        ('sr',        perto_suporte,                                "Perto do suporte",                5),
    ]

    sell_conditions = [
        ('ema_fast',  last_close < last_ema_fast,                  "EMA fast bearish",               15),
        ('ema_trend', last_close < last_ema_trend,                 "EMA trend bearish",               15),
        ('macd',      last_macd < last_signal,                     "MACD bearish",                    15),
        ('cci',       last_cci <= -50,                              "CCI negativo",                    15),
        ('rsi',       35 <= last_rsi <= 55,                         "RSI favorável (tendência baixa)", 10),
        ('volume',    last_vol_ok,                                  "Volume OK",                       10),
        ('bollinger', last_close >= last_boll_upper * 0.9995,       "Bollinger superior (resistência)",10),
        ('sr',        perto_resistencia,                            "Perto da resistência",             5),
    ]

    score_buy, max_score_buy, reasons_buy = calculate_side_score(buy_conditions, w_buy)
    score_sell, max_score_sell, reasons_sell = calculate_side_score(sell_conditions, w_sell)

    score_buy_pct = (score_buy / max_score_buy) * 100 if max_score_buy > 0 else 0
    score_sell_pct = (score_sell / max_score_sell) * 100 if max_score_sell > 0 else 0

    # Score final (o maior entre buy e sell)
    score_final = max(score_buy_pct, score_sell_pct)
    filters_detailed['Score'] = {'value': score_final, 'min': 70, 'pass': score_final >= score_min}

    # ===== VERIFICAÇÃO DOS FILTROS =====
    # Ordem de verificação: MQ, ADX, BW, Score
    if not filters_detailed['MQ']['pass']:
        empty_result['filters_blocked'] = [f'MQ ({mq:.0f} < {mq_min})']
        empty_result['filters_detailed'] = filters_detailed
        return empty_result

    if not filters_detailed['ADX']['pass']:
        empty_result['filters_blocked'] = [f'ADX ({last_adx:.1f} < {adx_min})']
        empty_result['filters_detailed'] = filters_detailed
        return empty_result

    if not filters_detailed['BW']['pass']:
        empty_result['filters_blocked'] = [f'BW ({bollinger_width:.4f} < {bollinger_width_min})']
        empty_result['filters_detailed'] = filters_detailed
        return empty_result

    if not filters_detailed['Score']['pass']:
        empty_result['filters_blocked'] = [f'Score ({score_final:.1f} < 70)']
        empty_result['filters_detailed'] = filters_detailed
        return empty_result

    # ===== DECISÃO (SCORE >= 70) =====
    if score_buy_pct > score_sell_pct and score_buy_pct >= score_min:
        signal = "COMPRA"
        confidence = score_buy_pct
    elif score_sell_pct > score_buy_pct and score_sell_pct >= score_min:
        signal = "VENDA"
        confidence = score_sell_pct
    else:
        signal = "NEUTRO"
        confidence = 0

    distancia_ema = last_close - last_ema_trend

    if len(ema_trend) > 20:
        inclinacao = (ema_trend.iloc[-1] - ema_trend.iloc[-20]) / ema_trend.iloc[-20] * 100
        trend_direction = "Alta" if inclinacao > 0.3 else "Baixa" if inclinacao < -0.3 else "Lateral"
    else:
        trend_direction = "Sem dados"

    return {
        'signal': signal,
        'confidence': confidence,
        'market_quality': mq,
        'score_buy': score_buy_pct,
        'score_sell': score_sell_pct,
        'max_score_buy': max_score_buy,
        'max_score_sell': max_score_sell,
        'reasons_buy': reasons_buy,
        'reasons_sell': reasons_sell,
        'filters_blocked': empty_result['filters_blocked'] if signal == "NEUTRO" else [],
        'filters_detailed': filters_detailed,
        'close': last_close,
        'ema_fast': last_ema_fast,
        'ema_trend': last_ema_trend,
        'rsi': last_rsi,
        'macd': last_macd,
        'cci': last_cci,
        'atr': atr,
        'bollinger_width': bollinger_width,
        'distancia_ema': distancia_ema,
        'trend_direction': trend_direction,
        'volume_ratio': volume_ratio
    }
