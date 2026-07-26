#!/usr/bin/env python3
import pandas as pd
import os
import json
from datetime import datetime, timedelta
from modules.notifier import TelegramNotifier
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

def load_analysis():
    file = "data/analysis/historical_analysis.csv"
    if not os.path.isfile(file):
        return None
    df = pd.read_csv(file)
    if df.empty:
        return None
    return df

def get_week_range():
    now = datetime.now()
    start = now - timedelta(days=7)
    return start.strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d")

def analyze_week(df):
    if df is None:
        return "⚠️ Sem dados de análise."
    start, end = get_week_range()
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
    df_week = df[(df['timestamp_dt'] >= start) & (df['timestamp_dt'] <= end)].copy()
    if df_week.empty:
        return "⚠️ Nenhum dado na última semana."
    df_confirmed = df_week[df_week["resultado"].isin(["WIN", "LOSS"])].copy()
    if df_confirmed.empty:
        return "⚠️ Nenhum trade confirmado na última semana."
    total = len(df_confirmed)
    wins = len(df_confirmed[df_confirmed["resultado"] == "WIN"])
    win_rate = (wins / total) * 100 if total > 0 else 0
    report = f"📊 RELATÓRIO SEMANAL\n"
    report += f"Período: {start} a {end}\n"
    report += f"Total de trades: {total}\n"
    report += f"Win Rate: {win_rate:.2f}%\n\n"
    report += "📌 Win Rate por Ativo:\n"
    for asset in df_confirmed["asset"].unique():
        sub = df_confirmed[df_confirmed["asset"] == asset]
        w = len(sub[sub["resultado"] == "WIN"])
        wr = (w / len(sub)) * 100 if len(sub) > 0 else 0
        report += f"  {asset}: {len(sub)} trades, {wr:.1f}%\n"
    if total >= 10:
        report += "\n📌 Recomendações:\n"
        for asset in df_confirmed["asset"].unique():
            sub = df_confirmed[df_confirmed["asset"] == asset]
            if len(sub) >= 3:
                w = len(sub[sub["resultado"] == "WIN"])
                wr = (w / len(sub)) * 100
                if wr < 40:
                    report += f"  ⚠️ {asset} tem win rate baixo ({wr:.1f}%). Considerar reduzir exposição.\n"
                if wr > 65:
                    report += f"  ✅ {asset} tem win rate alto ({wr:.1f}%). Manter ou aumentar.\n"
    return report

def check_pending_suggestions(report):
    """Adiciona ao relatório as sugestões pendentes, se existirem."""
    suggestions_file = "data/pending_suggestions.json"
    if not os.path.isfile(suggestions_file):
        return report
    try:
        with open(suggestions_file, "r") as f:
            suggestions = json.load(f)
        if not suggestions:
            return report
        report += "\n\n📌 Sugestões de otimização pendentes:\n"
        for asset, params in suggestions.items():
            report += f"  {asset}:\n"
            for param, data in params.items():
                report += f"    • {param}: {data['current']} → {data['suggested']} (win rate {data['win_rate']:.1f}%, {data['trades']} trades)\n"
        report += "\nPara aplicar, envie /apply_suggestions no Telegram.\n"
        report += "Para rejeitar, envie /reject_suggestions."
    except Exception as e:
        report += f"\n\n⚠️ Erro ao ler sugestões: {e}"
    return report

def send_report(report):
    # Adicionar sugestões pendentes
    report = check_pending_suggestions(report)
    notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID) if TELEGRAM_TOKEN else None
    if notifier:
        notifier.send_message(report)
        print("📨 Relatório semanal enviado para Telegram.")
    else:
        print(report)

def main():
    # Gerar sugestões de otimização (se houver dados suficientes)
    try:
        import subprocess
        print("📊 A gerar sugestões de otimização...")
        subprocess.run(["python3", "optimizer_assets.py"], check=False)
    
    # Executar backtester avançado (se houver dados)
    try:
        print("📊 A executar backtester avançado...")
        subprocess.run(["python3", "backtester_advanced.py"], check=False)
    except Exception as e:
        print(f"⚠️ Erro no backtester: {e}")
    
    # Executar otimizador de pesos
    try:
        print("📊 A otimizar pesos...")
        subprocess.run(["python3", "optimizer_weights.py"], check=False)
    except Exception as e:
        print(f"⚠️ Erro no otimizador de pesos: {e}")
    except Exception as e:
        print(f"⚠️ Erro ao gerar sugestões: {e}")
    
    df = load_analysis()
    report = analyze_week(df)
    send_report(report)

if __name__ == "__main__":
    main()
