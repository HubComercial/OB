#!/usr/bin/env python3
import pandas as pd
import os
import json
from modules.learner import optimize_parameters
from modules.investigator import generate_report
from modules.dynamic_scorer import get_weight_recommendations

def analyze_trades():
    if not os.path.isfile("data/feedback.csv"):
        print("⚠️ Nenhum dado de trades encontrado.")
        return None
    df = pd.read_csv("data/feedback.csv")
    if df.empty:
        print("⚠️ Ficheiro de trades vazio.")
        return None
    df_confirmed = df[df["resultado"].isin(["WIN", "LOSS"])].copy()
    if df_confirmed.empty:
        print("⚠️ Nenhum trade confirmado encontrado.")
        return None
    total = len(df_confirmed)
    wins = len(df_confirmed[df_confirmed["resultado"] == "WIN"])
    win_rate = (wins / total) * 100 if total > 0 else 0
    print(f"📊 Análise de {total} trades confirmados:")
    print(f"   Win Rate: {win_rate:.2f}%")
    print("\n📌 Win Rate por Ativo:")
    for asset in df_confirmed["ativo"].unique():
        sub = df_confirmed[df_confirmed["ativo"] == asset]
        w = len(sub[sub["resultado"] == "WIN"])
        wr = (w / len(sub)) * 100 if len(sub) > 0 else 0
        print(f"   {asset}: {len(sub)} trades, win rate {wr:.1f}%")
    return df_confirmed

def main():
    print("=" * 60)
    print("🧠 MODO DE APRENDIZAGEM – FIM DE SEMANA")
    print("=" * 60)
    df = analyze_trades()
    print("\n📈 A otimizar pesos dinâmicos...")
    suggestions = get_weight_recommendations()
    if suggestions:
        print("✅ Sugestões de novos pesos:")
        for k, v in suggestions.items():
            print(f"   {k}: {v:.2f}")
        with open("data/weights_suggestion.json", "w") as f:
            json.dump(suggestions, f, indent=2)
        print("💾 Sugestões guardadas em data/weights_suggestion.json")
    else:
        print("⚠️ Dados insuficientes para otimizar pesos (mínimo 10 trades).")
    print("\n📋 A gerar relatório do investigador...")
    generate_report()
    print("\n✅ Análise concluída. A dormir até segunda-feira...")
    print("=" * 60)

if __name__ == "__main__":
    main()
