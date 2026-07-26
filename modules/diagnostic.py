"""
Diagnóstico contínuo: mostra o status de cada condição para COMPRA e VENDA.
"""
from modules.data_fetcher_hybrid import DataFetcherHybrid
from modules.indicators import calculate_rsi, calculate_bollinger_bands, calculate_ema, calculate_cci, calculate_macd
from modules.advanced_metrics import calculate_atr, calculate_pivot_points, check_support_resistance
from config import *

def diagnostic(asset="EURUSD=X", timeframe=1):
    fetcher = DataFetcherHybrid(asset=asset, timeframe=timeframe)
    df = fetcher.get_historical_data(100)
    if df is None or len(df) < 30:
        return None

    close = df['close']
    open_price = df['open']
    high = df['high']
    low = df['low']

    ema = calculate_ema(close, EMA_PERIOD)
    ema200 = calculate_ema(close, 200)
    cci = calculate_cci(high, low, close, CCI_PERIOD)
    macd, signal, _ = calculate_macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    rsi = calculate_rsi(close, RSI_PERIOD)
    upper, mid, lower = calculate_bollinger_bands(close, BB_PERIOD, BB_STD)
    atr = calculate_atr(df, ATR_PERIOD)
    pivots = calculate_pivot_points(df)
    current_price = close.iloc[-1]
    perto_suporte, perto_resistencia, qual = check_support_resistance(current_price, pivots)

    # Últimos valores
    last_close = close.iloc[-1]
    last_open = open_price.iloc[-1]
    last_ema = ema.iloc[-1]
    prev_ema = ema.iloc[-2]
    last_cci = cci.iloc[-1]
    last_macd = macd.iloc[-1]
    last_signal = signal.iloc[-1]
    last_rsi = rsi.iloc[-1]
    last_boll_lower = lower.iloc[-1]
    last_boll_upper = upper.iloc[-1]
    last_ema200 = ema200.iloc[-1]
    last_atr = atr
    last_price = last_close

    # Condições para COMPRA
    buy_conditions = {
        'Candle verde': last_close > last_open,
        'Preço > EMA10': last_close > last_ema,
        'CCI >= 100': last_cci >= 100,
        'EMA10 subindo': last_ema > prev_ema,
        'MACD bullish': last_macd > last_signal,
        'Preço > EMA200': last_close > last_ema200,
        'RSI < 30': last_rsi < 30,
        'Preço <= Bollinger Inferior': last_close <= last_boll_lower,
        'Volume > média': True,  # simplificado
        'ATR >= 0.0005': last_atr >= 0.0005,
        'Suporte/Resistência OK': not perto_resistencia and not perto_suporte,
    }

    # Condições para VENDA
    sell_conditions = {
        'Candle vermelho': last_close < last_open,
        'Preço < EMA10': last_close < last_ema,
        'CCI <= -100': last_cci <= -100,
        'EMA10 descendo': last_ema < prev_ema,
        'MACD bearish': last_macd < last_signal,
        'Preço < EMA200': last_close < last_ema200,
        'RSI > 70': last_rsi > 70,
        'Preço >= Bollinger Superior': last_close >= last_boll_upper,
        'Volume > média': True,
        'ATR >= 0.0005': last_atr >= 0.0005,
        'Suporte/Resistência OK': not perto_resistencia and not perto_suporte,
    }

    print(f"\n📊 DIAGNÓSTICO PARA {asset} ({timeframe}m)")
    print(f"Preço: {last_price:.5f} | ATR: {last_atr:.5f} | RSI: {last_rsi:.1f}\n")

    print("🟢 CONDIÇÕES DE COMPRA:")
    for k, v in buy_conditions.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print("\n🔴 CONDIÇÕES DE VENDA:")
    for k, v in sell_conditions.items():
        print(f"  {'✅' if v else '❌'} {k}")

    print("\n💡 RESULTADO FINAL:")
    if all(buy_conditions.values()):
        print("  🟢 COMPRA")
    elif all(sell_conditions.values()):
        print("  🔴 VENDA")
    else:
        print("  ⚪ NEUTRO")

    return buy_conditions, sell_conditions
