#!/usr/bin/env python3
import pandas as pd
import os
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

def get_month_range():
    now = datetime.now()
    start = now.replace(day=1)
    end = now
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def analyze_month(df):
    if df is None:
        return "⚠️ Sem dados de análise."
    start, end = get_month_range()
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'])
    df_month = df[(df['timestamp_dt'] >= start) & (df['timestamp_dt'] <= end)].copy()
    if df_month.empty:
        return f"⚠️ Nenhum dado no mês {start[:7]}."
    df_confirmed = df_month[df_month["resultado"].isin(["WIN", "LOSS"])].copy()
    if df_confirmed.empty:
        return f"⚠️ Nenhum trade confirmado no mês {start[:7]}."
    total = len(df_confirmed)
    wins = len(df_confirmed[df_confirmed["resultado"] == "WIN"])
    win_rate = (wins / total) * 100 if total > 0 else 0
    report = f"📊 RELATÓRIO MENSAL\n"
    report += f"Mês: {start[:7]}\n"
    report += f"Total de trades: {total}\n"
    report += f"Win Rate: {win_rate:.2f}%\n\n"
    report += "📌 Win Rate por Ativo:\n"
    for asset in df_confirmed["asset"].unique():
        sub = df_confirmed[df_confirmed["asset"] == asset]
        w = len(sub[sub["resultado"] == "WIN"])
        wr = (w / len(sub)) * 100 if len(sub) > 0 else 0
        report += f"  {asset}: {len(sub)} trades, {wr:.1f}%\n"
    report += "\n📌 Melhor horário:\n"
    df_confirmed['hour'] = pd.to_datetime(df_confirmed['timestamp']).dt.hour
    hour_perf = df_confirmed.groupby('hour').apply(lambda x: (x['resultado'] == "WIN").mean() * 100)
    best_hour = hour_perf.idxmax()
    best_wr = hour_perf.max()
    report += f"  {best_hour:02d}:00 → {best_wr:.1f}% win rate\n"
    return report

def send_report(report):
    notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID) if TELEGRAM_TOKEN else None
    if notifier:
        notifier.send_message(report)
        print("📨 Relatório mensal enviado para Telegram.")
    else:
        print(report)

def main():    # Executar backtester e otimizador
    try:
        import subprocess
        print("📊 A executar backtester avançado...")
        subprocess.run(["python3", "backtester_advanced.py"], check=False)
    except Exception as e:
        print(f"⚠️ Erro no backtester: {e}")
    
    try:
        print("📊 A otimizar pesos...")
        subprocess.run(["python3", "optimizer_weights.py"], check=False)
    except Exception as e:
        print(f"⚠️ Erro no otimizador de pesos: {e}")
    
    
    df = load_analysis()
    report = analyze_month(df)
    send_report(report)


    # Gerar sugestões de otimização (se houver dados suficientes)
    try:
        import subprocess
        print("📊 A gerar sugestões de otimização...")
        subprocess.run(["python3", "optimizer_assets.py"], check=False)
    except Exception as e:
        print(f"⚠️ Erro ao gerar sugestões: {e}")
    

if __name__ == "__main__":
    main()
