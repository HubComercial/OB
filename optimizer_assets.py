#!/usr/bin/env python3
"""
optimizer_assets.py – Analisa dados históricos e sugere ajustes de parâmetros por ativo.
Gera recomendações específicas (ex: "USDJPY: aumentar ADX_MIN de 25 para 30").
"""
import pandas as pd
import json
import os
from datetime import datetime

def load_analysis():
    file = "data/analysis/historical_analysis.csv"
    if not os.path.isfile(file):
        return None
    df = pd.read_csv(file)
    if df.empty:
        return None
    return df

def simulate_threshold(df, asset, column, values):
    """Simula diferentes thresholds e retorna o win rate para cada um."""
    results = {}
    for val in values:
        sub = df[(df["asset"] == asset) & (df[column] >= val)].copy()
        if sub.empty:
            results[val] = {"trades": 0, "win_rate": 0}
            continue
        confirmed = sub[sub["resultado"].isin(["WIN", "LOSS"])]
        if confirmed.empty:
            results[val] = {"trades": 0, "win_rate": 0}
            continue
        total = len(confirmed)
        wins = len(confirmed[confirmed["resultado"] == "WIN"])
        results[val] = {"trades": total, "win_rate": (wins / total) * 100 if total > 0 else 0}
    return results

def generate_suggestions():
    df = load_analysis()
    if df is None or df.empty:
        return None
    
    # Carregar configuração atual
    try:
        with open("config_assets.json", "r") as f:
            current_config = json.load(f)
    except:
        current_config = {}
    
    suggestions = {}
    
    for asset in df["asset"].unique():
        # Filtrar apenas dados confirmados
        sub = df[(df["asset"] == asset) & (df["resultado"].isin(["WIN", "LOSS"]))].copy()
        if sub.empty or len(sub) < 10:
            continue
        
        current = current_config.get(asset, {})
        
        # Testar diferentes valores para ADX
        adx_results = simulate_threshold(df, asset, "adx", [20, 25, 30, 35, 40])
        best_adx = max(adx_results.items(), key=lambda x: x[1]["win_rate"] if x[1]["trades"] >= 5 else 0)
        current_adx = current.get("adx_min", 25)
        
        if best_adx[0] != current_adx and best_adx[1]["trades"] >= 5:
            suggestions[asset] = suggestions.get(asset, {})
            suggestions[asset]["adx_min"] = {
                "current": current_adx,
                "suggested": best_adx[0],
                "win_rate": best_adx[1]["win_rate"],
                "trades": best_adx[1]["trades"]
            }
        
        # Testar diferentes valores para Market Quality
        mq_results = simulate_threshold(df, asset, "market_quality", [25, 30, 35, 40, 45])
        best_mq = max(mq_results.items(), key=lambda x: x[1]["win_rate"] if x[1]["trades"] >= 5 else 0)
        current_mq = current.get("mq_min", 35)
        
        if best_mq[0] != current_mq and best_mq[1]["trades"] >= 5:
            suggestions[asset] = suggestions.get(asset, {})
            suggestions[asset]["mq_min"] = {
                "current": current_mq,
                "suggested": best_mq[0],
                "win_rate": best_mq[1]["win_rate"],
                "trades": best_mq[1]["trades"]
            }
        
        # Testar diferentes valores para Bollinger Width
        bw_results = simulate_threshold(df, asset, "bollinger_width", [0.00005, 0.0001, 0.00015, 0.0002])
        best_bw = max(bw_results.items(), key=lambda x: x[1]["win_rate"] if x[1]["trades"] >= 5 else 0)
        current_bw = current.get("bollinger_width_min", 0.0001)
        
        if best_bw[0] != current_bw and best_bw[1]["trades"] >= 5:
            suggestions[asset] = suggestions.get(asset, {})
            suggestions[asset]["bollinger_width_min"] = {
                "current": current_bw,
                "suggested": best_bw[0],
                "win_rate": best_bw[1]["win_rate"],
                "trades": best_bw[1]["trades"]
            }
    
    return suggestions

def main():
    print("📊 A gerar sugestões de otimização por ativo...")
    suggestions = generate_suggestions()
    if not suggestions:
        print("⚠️ Dados insuficientes para gerar sugestões (mínimo 10 trades por ativo).")
        return
    
    # Guardar sugestões
    with open("data/pending_suggestions.json", "w") as f:
        json.dump(suggestions, f, indent=2)
    
    print(f"✅ {len(suggestions)} ativos com sugestões geradas.")
    print("📁 Sugestões guardadas em data/pending_suggestions.json")
    
    # Mostrar resumo
    for asset, params in suggestions.items():
        print(f"\n📌 {asset}:")
        for param, data in params.items():
            print(f"   {param}: atual={data['current']} → sugerido={data['suggested']} (win rate {data['win_rate']:.1f}%, {data['trades']} trades)")

if __name__ == "__main__":
    main()
