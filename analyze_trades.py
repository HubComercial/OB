#!/usr/bin/env python3
"""
analyze_trades.py
Analisa o histórico de trades do robô e gera um relatório com:
- Win rate global
- Win rate por ativo, timeframe, market quality, confiança
- Correlação entre variáveis e resultados
- Sugestões para otimização
"""
import pandas as pd
import json
from datetime import datetime
from collections import defaultdict

FEEDBACK_FILE = "data/feedback.csv"
REPORT_FILE = "data/analysis_report.txt"

def load_feedback():
    """Carrega o ficheiro feedback.csv."""
    try:
        df = pd.read_csv(FEEDBACK_FILE)
        # Filtrar apenas sinais confirmados (resultado != PENDENTE)
        df_confirmed = df[df['resultado'].isin(["WIN", "LOSS"])].copy()
        return df_confirmed
    except Exception as e:
        print(f"❌ Erro ao carregar {FEEDBACK_FILE}: {e}")
        return None

def parse_reasons(reasons_str):
    """Converte a string JSON de razões para uma lista."""
    try:
        return json.loads(reasons_str) if pd.notna(reasons_str) else []
    except:
        return []

def analyze(df):
    """Gera análise detalhada."""
    if df is None or df.empty:
        print("⚠️ Nenhum trade confirmado encontrado.")
        return

    print("\n" + "=" * 60)
    print("📊 ANÁLISE DE TRADES")
    print("=" * 60)

    total = len(df)
    wins = len(df[df['resultado'] == "WIN"])
    losses = total - wins
    win_rate = (wins / total * 100) if total > 0 else 0

    print(f"\n📈 Geral:")
    print(f"   Total de trades: {total}")
    print(f"   Wins: {wins}")
    print(f"   Losses: {losses}")
    print(f"   Win Rate: {win_rate:.2f}%")

    # ===== 1. Análise por Ativo =====
    print("\n📌 Por Ativo:")
    for asset in df['ativo'].unique():
        sub = df[df['ativo'] == asset]
        w = len(sub[sub['resultado'] == "WIN"])
        l = len(sub) - w
        wr = (w / len(sub) * 100) if len(sub) > 0 else 0
        print(f"   {asset}: {len(sub)} trades, {w}W {l}L, win rate {wr:.1f}%")

    # ===== 2. Timeframe (não disponível) =====
    print("\n📌 Timeframe (não disponível no CSV atual) – aguardar instrumentação.")
    print("   Sugestão: adicionar coluna 'timeframe' no feedback.csv.")

    # ===== 3. Market Quality =====
    if 'market_quality' in df.columns:
        mq_bins = [0, 30, 50, 70, 100]
        labels = ['<30', '30-49', '50-69', '70+']
        df['mq_group'] = pd.cut(df['market_quality'], bins=mq_bins, labels=labels, right=False)
        print("\n📌 Market Quality:")
        for group in df['mq_group'].unique():
            sub = df[df['mq_group'] == group]
            w = len(sub[sub['resultado'] == "WIN"])
            l = len(sub) - w
            wr = (w / len(sub) * 100) if len(sub) > 0 else 0
            print(f"   {group}: {len(sub)} trades, win rate {wr:.1f}%")

    # ===== 4. Score e Confiança =====
    if 'score_buy' in df.columns and 'score_sell' in df.columns:
        for result in ["WIN", "LOSS"]:
            sub = df[df['resultado'] == result]
            if not sub.empty:
                avg_buy = sub['score_buy'].mean()
                avg_sell = sub['score_sell'].mean()
                print(f"\n📌 Scores ({result}):")
                print(f"   Score BUY médio: {avg_buy:.2f}")
                print(f"   Score SELL médio: {avg_sell:.2f}")

    # ===== 5. Razões =====
    win_reasons = defaultdict(int)
    loss_reasons = defaultdict(int)

    for _, row in df.iterrows():
        reasons = parse_reasons(row.get('reasons_buy', '[]')) + parse_reasons(row.get('reasons_sell', '[]'))
        if row['resultado'] == "WIN":
            for r in reasons:
                win_reasons[r] += 1
        else:
            for r in reasons:
                loss_reasons[r] += 1

    print("\n📌 Indicadores mais frequentes em WINs:")
    for motive, count in sorted(win_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   {motive}: {count} vezes")

    print("\n📌 Indicadores mais frequentes em LOSSs:")
    for motive, count in sorted(loss_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"   {motive}: {count} vezes")

    # ===== 6. Confiança proxy =====
    if 'score_buy' in df.columns and 'score_sell' in df.columns:
        df['confidence_proxy'] = df[['score_buy', 'score_sell']].max(axis=1)
        print("\n📌 Confiança média:")
        for result in ["WIN", "LOSS"]:
            sub = df[df['resultado'] == result]
            if not sub.empty:
                avg_conf = sub['confidence_proxy'].mean()
                print(f"   {result}: {avg_conf:.2f}")

    # ===== 7. Horários =====
    if 'timestamp' in df.columns:
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        print("\n📌 Win rate por hora (UTC):")
        for hour in sorted(df['hour'].unique()):
            sub = df[df['hour'] == hour]
            w = len(sub[sub['resultado'] == "WIN"])
            wr = (w / len(sub) * 100) if len(sub) > 0 else 0
            print(f"   {hour:02d}h: {len(sub)} trades, win rate {wr:.1f}%")

    # ===== 8. Conclusões =====
    print("\n" + "=" * 60)
    print("🧠 RECOMENDAÇÕES")
    print("=" * 60)

    if win_rate < 50:
        print("⚠️ Win rate abaixo de 50% – rever filtros ou pesos.")
    elif win_rate < 60:
        print("✅ Win rate aceitável – pode melhorar com ajustes finos.")
    else:
        print("✅ Win rate bom – manter estratégia.")

    if 'mq_group' in df.columns:
        mq_perf = df.groupby('mq_group')['resultado'].apply(lambda x: (x == "WIN").mean() * 100)
        if not mq_perf.empty:
            print("\n📌 Market Quality com melhor performance:")
            print(mq_perf.sort_values(ascending=False).to_string())

    asset_perf = df.groupby('ativo')['resultado'].apply(lambda x: (x == "WIN").mean() * 100)
    print("\n📌 Ativos com melhor win rate:")
    print(asset_perf.sort_values(ascending=False).to_string())

    # ===== 9. Guardar relatório =====
    lines = []
    lines.append("=" * 60)
    lines.append("📊 RELATÓRIO DE ANÁLISE DE TRADES")
    lines.append("=" * 60)
    lines.append(f"Total de trades: {total}")
    lines.append(f"Win Rate: {win_rate:.2f}%")
    lines.append(f"Wins: {wins}, Losses: {losses}")

    if 'mq_group' in df.columns:
        lines.append("\n📌 Market Quality (win rate por grupo):")
        for k, v in mq_perf.items():
            lines.append(f"   {k}: {v:.1f}%")

    lines.append("\n📌 Ativos (win rate):")
    for k, v in asset_perf.items():
        lines.append(f"   {k}: {v:.1f}%")

    lines.append("\n📌 Indicadores mais frequentes em WINs:")
    for m, c in sorted(win_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
        lines.append(f"   {m}: {c}")

    lines.append("\n📌 Indicadores mais frequentes em LOSSs:")
    for m, c in sorted(loss_reasons.items(), key=lambda x: x[1], reverse=True)[:5]:
        lines.append(f"   {m}: {c}")

    with open(REPORT_FILE, "w") as f:
        f.write("\n".join(lines))

    print(f"\n✅ Relatório guardado em: {REPORT_FILE}")

if __name__ == "__main__":
    df = load_feedback()
    analyze(df)
