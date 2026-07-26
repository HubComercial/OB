#!/usr/bin/env python3
"""
optimizer_weights.py – Otimiza os pesos dos indicadores por ativo
com base em dados históricos (WIN/LOSS) usando correlação.
Sem dependência do scikit-learn.
"""
import pandas as pd
import numpy as np
import os
import json

def load_analysis():
    file = "data/analysis/historical_analysis.csv"
    if not os.path.isfile(file):
        return None
    df = pd.read_csv(file)
    if df.empty:
        return None
    return df

def optimize_weights(df, asset):
    """Encontra os melhores pesos para um ativo usando correlação com o resultado."""
    sub = df[df['asset'] == asset].copy()
    sub = sub[sub['resultado'].isin(['WIN', 'LOSS'])].copy()
    if len(sub) < 20:
        return None

    # Mapear resultado para 1 (WIN) e 0 (LOSS)
    sub['target'] = (sub['resultado'] == 'WIN').astype(int)

    # Features: indicadores disponíveis
    features = ['ema_fast', 'ema_trend', 'rsi', 'macd', 'cci', 'atr', 'adx', 'bollinger_width', 'market_quality', 'score_buy', 'score_sell']
    existing_features = [f for f in features if f in sub.columns]
    if len(existing_features) < 3:
        return None

    # Calcular correlação de cada feature com o target
    correlations = {}
    for f in existing_features:
        corr = sub[f].corr(sub['target'])
        correlations[f] = abs(corr)  # usar valor absoluto como importância

    # Normalizar para pesos (soma = 100)
    total = sum(correlations.values())
    if total == 0:
        return None
    weights = {k: (v / total) * 100 for k, v in correlations.items()}

    # Arredondar e ajustar para soma 100
    weight_dict = {k: round(v) for k, v in weights.items()}
    total_round = sum(weight_dict.values())
    if total_round != 100:
        # Ajustar o maior valor para compensar
        max_key = max(weight_dict, key=weight_dict.get)
        weight_dict[max_key] += (100 - total_round)

    return weight_dict

def main():
    print("=" * 60)
    print("📊 OTIMIZADOR DE PESOS")
    print("=" * 60)

    df = load_analysis()
    if df is None or df.empty:
        print("⚠️ Sem dados de análise (historical_analysis.csv). Aguarda o robô gerar dados.")
        return

    suggestions = {}
    for asset in df['asset'].unique():
        print(f"\n🔍 A otimizar pesos para {asset}...")
        weights = optimize_weights(df, asset)
        if weights:
            suggestions[asset] = weights
            print(f"✅ Novos pesos sugeridos: {weights}")
        else:
            print(f"⚠️ Dados insuficientes para {asset} (mínimo 20 trades confirmados).")

    if suggestions:
        with open("data/weights_suggestions.json", "w") as f:
            json.dump(suggestions, f, indent=2)
        print("\n💾 Sugestões de pesos guardadas em data/weights_suggestions.json")
    else:
        print("\n⚠️ Não foram geradas sugestões de pesos.")

if __name__ == "__main__":
    main()
