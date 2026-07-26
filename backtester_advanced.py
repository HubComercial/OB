#!/usr/bin/env python3
"""
backtester_advanced.py – Simula a estratégia com dados históricos
para encontrar a melhor combinação de parâmetros por ativo.
"""
import pandas as pd
import numpy as np
import os
import json
from datetime import datetime, timedelta
from modules.indicators import (
    calculate_ema, calculate_rsi, calculate_macd, calculate_cci,
    calculate_bollinger_bands, calculate_volume_ma
)
from modules.advanced_metrics import calculate_atr, calculate_pivot_points
from modules.strategy import calculate_market_quality, calculate_adx

# Parâmetros fixos (iguais aos do robô)
CCI_PERIOD = 20
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
ATR_PERIOD = 14
BB_PERIOD = 20
VOLUME_PERIOD = 20
TIMEFRAME = 5  # minutos (usado para cálculo de timeframe)

def load_candles(asset, start_date=None, end_date=None):
    """Carrega todos os candles disponíveis para um ativo."""
    candles_dir = "data/candles"
    if not os.path.isdir(candles_dir):
        return None
    all_dfs = []
    for folder in sorted(os.listdir(candles_dir)):
        if start_date and folder < start_date:
            continue
        if end_date and folder > end_date:
            continue
        filepath = os.path.join(candles_dir, folder, f"{asset.replace('=', '-')}.csv")
        if os.path.isfile(filepath):
            df = pd.read_csv(filepath)
            if not df.empty:
                all_dfs.append(df)
    if not all_dfs:
        return None
    df_all = pd.concat(all_dfs, ignore_index=True)
    df_all['timestamp'] = pd.to_datetime(df_all['timestamp'])
    df_all = df_all.sort_values('timestamp').reset_index(drop=True)
    # Remover duplicados (caso haja)
    df_all = df_all.drop_duplicates(subset=['timestamp'], keep='last')
    return df_all

def simulate_strategy(df, params, timeframe=5):
    """Simula a estratégia com os parâmetros dados."""
    if df is None or len(df) < 50:
        return None

    # Parâmetros
    atr_min = params.get('atr_min', 0.00005)
    adx_min = params.get('adx_min', 25)
    bw_min = params.get('bollinger_width_min', 0.0001)
    mq_min = params.get('mq_min', 35)
    score_min = params.get('score_min', 70)
    weights_buy = params.get('weights_buy', None)
    weights_sell = params.get('weights_sell', None)

    close = df['close']
    high = df['high']
    low = df['low']

    # Calcular indicadores
    ema_fast = calculate_ema(close, 12)
    ema_trend = calculate_ema(close, 26)
    rsi = calculate_rsi(close, 14)
    macd_line, signal_line, _ = calculate_macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
    cci = calculate_cci(high, low, close, CCI_PERIOD)
    atr = calculate_atr(df, ATR_PERIOD)
    adx = calculate_adx(df, 14)
    boll_upper, boll_mid, boll_lower = calculate_bollinger_bands(close, BB_PERIOD, 2.0)  # std=2 padrão
    bollinger_width = (boll_upper - boll_lower) / boll_mid

    # Volume (se disponível)
    if 'volume' in df.columns:
        vol_ma = calculate_volume_ma(df['volume'], VOLUME_PERIOD)
        volume_ratio = df['volume'] / vol_ma
    else:
        volume_ratio = pd.Series(1.0, index=df.index)

    # Pivots (para suporte/resistência)
    pivots = df.apply(lambda row: calculate_pivot_points(pd.DataFrame([row])), axis=1)

    trades = []
    for i in range(30, len(df) - 1):  # começa após ter indicadores suficientes
        idx = i
        last_close = close.iloc[idx]
        last_high = high.iloc[idx]
        last_low = low.iloc[idx]
        last_ema_fast = ema_fast.iloc[idx]
        last_ema_trend = ema_trend.iloc[idx]
        last_rsi = rsi.iloc[idx]
        last_macd = macd_line.iloc[idx]
        last_signal = signal_line.iloc[idx]
        last_cci = cci.iloc[idx]
        last_atr = atr.iloc[idx]
        last_adx = adx.iloc[idx] if not pd.isna(adx.iloc[idx]) else 0
        last_bw = bollinger_width.iloc[idx]
        last_boll_lower = boll_lower.iloc[idx]
        last_boll_upper = boll_upper.iloc[idx]
        last_vol_ratio = volume_ratio.iloc[idx] if not pd.isna(volume_ratio.iloc[idx]) else 1.0

        # Market Quality
        mq = calculate_market_quality(last_atr, atr_min, 0.001, last_close, last_ema_trend)

        # Scores
        # Usar pesos fornecidos ou padrão
        if weights_buy is None:
            w_buy = {'ema_fast': 15, 'ema_trend': 15, 'macd': 15, 'cci': 15, 'rsi': 10, 'volume': 10, 'bollinger': 10, 'sr': 5}
        else:
            w_buy = weights_buy
        if weights_sell is None:
            w_sell = {'ema_fast': 15, 'ema_trend': 15, 'macd': 15, 'cci': 15, 'rsi': 10, 'volume': 10, 'bollinger': 10, 'sr': 5}
        else:
            w_sell = weights_sell

        # Condições BUY
        score_buy = 0
        max_score_buy = sum(w_buy.values())
        if last_close > last_ema_fast:
            score_buy += w_buy.get('ema_fast', 15)
        if last_close > last_ema_trend:
            score_buy += w_buy.get('ema_trend', 15)
        if last_macd > last_signal:
            score_buy += w_buy.get('macd', 15)
        if last_cci >= 50:
            score_buy += w_buy.get('cci', 15)
        if 45 <= last_rsi <= 65:
            score_buy += w_buy.get('rsi', 10)
        if last_vol_ratio > 1.0:
            score_buy += w_buy.get('volume', 10)
        if last_close <= last_boll_lower * 1.0005:
            score_buy += w_buy.get('bollinger', 10)
        # Suporte/resistência simplificado (não usamos pivots para simplificar)
        # (poderíamos adicionar, mas não essencial para backtest)

        # Condições SELL
        score_sell = 0
        max_score_sell = sum(w_sell.values())
        if last_close < last_ema_fast:
            score_sell += w_sell.get('ema_fast', 15)
        if last_close < last_ema_trend:
            score_sell += w_sell.get('ema_trend', 15)
        if last_macd < last_signal:
            score_sell += w_sell.get('macd', 15)
        if last_cci <= -50:
            score_sell += w_sell.get('cci', 15)
        if 35 <= last_rsi <= 55:
            score_sell += w_sell.get('rsi', 10)
        if last_vol_ratio > 1.0:
            score_sell += w_sell.get('volume', 10)
        if last_close >= last_boll_upper * 0.9995:
            score_sell += w_sell.get('bollinger', 10)

        score_buy_pct = (score_buy / max_score_buy) * 100 if max_score_buy > 0 else 0
        score_sell_pct = (score_sell / max_score_sell) * 100 if max_score_sell > 0 else 0

        # Filtros
        if mq < mq_min:
            continue
        if last_adx < adx_min:
            continue
        if last_bw < bw_min:
            continue
        score_final = max(score_buy_pct, score_sell_pct)
        if score_final < score_min:
            continue

        # Decisão
        if score_buy_pct > score_sell_pct and score_buy_pct >= score_min:
            signal = "COMPRA"
            entry_price = last_close
            # Verificar próximo candle
            next_close = close.iloc[idx+1]
            result = next_close > entry_price
            trades.append({
                'timestamp': df['timestamp'].iloc[idx],
                'signal': signal,
                'entry_price': entry_price,
                'exit_price': next_close,
                'result': result
            })
        elif score_sell_pct > score_buy_pct and score_sell_pct >= score_min:
            signal = "VENDA"
            entry_price = last_close
            next_close = close.iloc[idx+1]
            result = next_close < entry_price
            trades.append({
                'timestamp': df['timestamp'].iloc[idx],
                'signal': signal,
                'entry_price': entry_price,
                'exit_price': next_close,
                'result': result
            })

    if not trades:
        return None
    df_trades = pd.DataFrame(trades)
    total = len(df_trades)
    wins = len(df_trades[df_trades['result'] == True])
    win_rate = (wins / total) * 100 if total > 0 else 0
    return {
        'total_trades': total,
        'wins': wins,
        'win_rate': win_rate,
        'trades': df_trades
    }

def optimize_parameters(asset, df):
    """Testa diferentes combinações de parâmetros para um ativo."""
    best_params = None
    best_win_rate = 0
    best_trades = 0

    # Faixas de parâmetros
    adx_values = range(20, 41, 5)
    bw_values = [0.00005, 0.0001, 0.00015, 0.0002]
    mq_values = range(30, 46, 5)
    score_values = range(60, 81, 5)

    total_combinations = len(adx_values) * len(bw_values) * len(mq_values) * len(score_values)
    print(f"📊 A testar {total_combinations} combinações para {asset}...")

    count = 0
    for adx in adx_values:
        for bw in bw_values:
            for mq in mq_values:
                for score in score_values:
                    params = {
                        'adx_min': adx,
                        'bollinger_width_min': bw,
                        'mq_min': mq,
                        'score_min': score
                    }
                    result = simulate_strategy(df, params)
                    if result and result['total_trades'] >= 5:  # mínimo de trades para considerar
                        win_rate = result['win_rate']
                        trades = result['total_trades']
                        # Priorizar win rate mais alto, depois número de trades
                        if win_rate > best_win_rate or (win_rate == best_win_rate and trades > best_trades):
                            best_win_rate = win_rate
                            best_trades = trades
                            best_params = params.copy()
                    count += 1
                    if count % 100 == 0:
                        print(f"  Progresso: {count}/{total_combinations}")

    return best_params, best_win_rate, best_trades

def main():
    print("=" * 60)
    print("📊 BACKTESTER AVANÇADO")
    print("=" * 60)

    # Carregar lista de ativos (a partir dos ficheiros de candles)
    candles_dir = "data/candles"
    if not os.path.isdir(candles_dir):
        print("⚠️ Pasta data/candles não encontrada. Executa o robô primeiro para gerar dados.")
        return

    assets = set()
    for folder in os.listdir(candles_dir):
        folder_path = os.path.join(candles_dir, folder)
        if os.path.isdir(folder_path):
            for file in os.listdir(folder_path):
                if file.endswith('.csv'):
                    asset = file.replace('.csv', '').replace('-', '=')
                    assets.add(asset)

    if not assets:
        print("⚠️ Nenhum ficheiro de candles encontrado.")
        return

    print(f"📈 Ativos encontrados: {sorted(assets)}")

    suggestions = {}
    for asset in sorted(assets):
        print(f"\n🔍 A processar {asset}...")
        df = load_candles(asset)
        if df is None or len(df) < 100:
            print(f"⚠️ Dados insuficientes para {asset} (mínimo 100 candles).")
            continue

        best_params, win_rate, trades = optimize_parameters(asset, df)
        if best_params:
            suggestions[asset] = {
                'params': best_params,
                'win_rate': win_rate,
                'trades': trades
            }
            print(f"✅ Melhor combinação para {asset}: {best_params} → win rate {win_rate:.2f}% ({trades} trades)")
        else:
            print(f"⚠️ Nenhuma combinação com pelo menos 5 trades para {asset}.")

    if suggestions:
        with open("data/backtest_suggestions.json", "w") as f:
            json.dump(suggestions, f, indent=2)
        print("\n💾 Sugestões guardadas em data/backtest_suggestions.json")
    else:
        print("\n⚠️ Não foram geradas sugestões.")

if __name__ == "__main__":
    main()
