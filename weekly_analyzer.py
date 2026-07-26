#!/usr/bin/env python3
import pandas as pd
import os
import json
from datetime import datetime, timedelta

def load_analysis():
    if not os.path.isfile("data/analysis/historical_analysis.csv"):
        return None
    df = pd.read_csv("data/analysis/historical_analysis.csv")
    if df.empty:
        return None
    return df

def analyze_patterns(df):
    if df is None:
        return
    df_confirmed = df[df["resultado"].isin(["WIN", "LOSS"])].copy()
    if df_confirmed.empty:
        print("⚠️ Nenhum trade confirmado encontrado.")
        return
    total = len(df_confirmed)
    wins = len(df_confirmed[df_confirmed["resultado"] == "WIN"])
    win_rate = (wins / total) * 100 if total > 0 else 0
    print(f"📊 Análise de {total} trades confirmados:")
    print(f"   Win Rate: {win_rate:.2f}%")
    print("\n📌 Win Rate por Ativo:")
    for asset in df_confirmed["asset"].unique():
        sub = df_confirmed[df_confirmed["asset"] == asset]
        w = len(sub[sub["resultado"] == "WIN"])
        wr = (w / len(sub)) * 100 if len(sub) > 0 else 0
        print(f"   {asset}: {len(sub)} trades, win rate {wr:.1f}%")
    print("\n📌 Win Rate por Market Quality (grupos):")
    df_confirmed["mq_group"] = pd.cut(df_confirmed["market_quality"], bins=[0,35,50,70,100], labels=["<35","35-49","50-69","70+"])
    for group in df_confirmed["mq_group"].unique():
        sub = df_confirmed[df_confirmed["mq_group"] == group]
        w = len(sub[sub["resultado"] == "WIN"])
        wr = (w / len(sub)) * 100 if len(sub) > 0 else 0
        print(f"   {group}: {len(sub)} trades, win rate {wr:.1f}%")
    print("\n📌 Win Rate por ADX (grupos):")
    df_confirmed["adx_group"] = pd.cut(df_confirmed["adx"], bins=[0,25,40,60,100], labels=["<25","25-39","40-59","60+"])
    for group in df_confirmed["adx_group"].unique():
        sub = df_confirmed[df_confirmed["adx_group"] == group]
        w = len(sub[sub["resultado"] == "WIN"])
        wr = (w / len(sub)) * 100 if len(sub) > 0 else 0
        print(f"   {group}: {len(sub)} trades, win rate {wr:.1f}%")
    print("\n📌 Win Rate por Score (grupos):")
    df_confirmed["score_group"] = pd.cut(df_confirmed["score_buy"].where(df_confirmed["score_buy"] >= df_confirmed["score_sell"], df_confirmed["score_sell"]), bins=[0,70,80,90,100], labels=["<70","70-79","80-89","90+"])
    for group in df_confirmed["score_group"].unique():
        sub = df_confirmed[df_confirmed["score_group"] == group]
        w = len(sub[sub["resultado"] == "WIN"])
        wr = (w / len(sub)) * 100 if len(sub) > 0 else 0
        print(f"   {group}: {len(sub)} trades, win rate {wr:.1f}%")

    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    if os.path.isdir("data/candles"):
        for folder in os.listdir("data/candles"):
            if folder < cutoff:
                import shutil
                shutil.rmtree(os.path.join("data/candles", folder))
                print(f"🗑️  Apagando candles de {folder}")
    if os.path.isfile("data/analysis/historical_analysis.csv"):
        df = pd.read_csv("data/analysis/historical_analysis.csv")
        if not df.empty:
            df["timestamp_dt"] = pd.to_datetime(df["timestamp"]).dt.date
            df = df[df["timestamp_dt"] >= pd.to_datetime(cutoff).date()]
            df.drop("timestamp_dt", axis=1, inplace=True)
            df.to_csv("data/analysis/historical_analysis.csv", index=False)

def main():
    print("="*60)
    print("📊 ANÁLISE SEMANAL – DADOS COMPLETOS")
    print("="*60)
    df = load_analysis()
    if df is not None and not df.empty:
        analyze_patterns(df)
    else:
        print("⚠️ Sem dados de análise disponíveis.")
    print("\n🧹 A limpar dados com mais de 30 dias...")
    print("✅ Análise concluída.")

if __name__ == "__main__":
    main()
