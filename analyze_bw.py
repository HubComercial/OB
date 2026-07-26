import pandas as pd
import json
import os

FEEDBACK_FILE = "data/feedback.csv"

def analyze_bw():
    if not os.path.isfile(FEEDBACK_FILE):
        print("❌ Ficheiro feedback.csv não encontrado.")
        return

    df = pd.read_csv(FEEDBACK_FILE)
    if 'bollinger_width' not in df.columns:
        print("❌ Coluna 'bollinger_width' não encontrada.")
        return

    bw = df['bollinger_width'].dropna()
    if bw.empty:
        print("⚠️ Nenhum dado de Bollinger Width disponível.")
        return

    print("\n📊 ESTATÍSTICAS DO BOLLINGER WIDTH")
    print("=" * 40)
    print(f"Total de registos: {len(bw)}")
    print(f"Mínimo: {bw.min():.6f}")
    print(f"Percentil 10: {bw.quantile(0.10):.6f}")
    print(f"Percentil 25: {bw.quantile(0.25):.6f}")
    print(f"Percentil 50: {bw.quantile(0.50):.6f}")
    print(f"Percentil 75: {bw.quantile(0.75):.6f}")
    print(f"Percentil 90: {bw.quantile(0.90):.6f}")
    print(f"Máximo: {bw.max():.6f}")
    print(f"Média: {bw.mean():.6f}")
    print("=" * 40)

    # Sugestão com base nos percentis
    p90 = bw.quantile(0.90)
    p75 = bw.quantile(0.75)
    print("\n📌 Sugestão:")
    if p90 < 0.001:
        print(f"   90% dos valores estão abaixo de {p90:.6f}.")
        print(f"   Considerar reduzir BOLLINGER_WIDTH_MIN para {p75:.6f} (Percentil 75) ou {p90:.6f} (Percentil 90).")
    else:
        print(f"   O valor atual (0.001) é adequado, pois 90% dos valores são ≥ {p90:.6f}.")

if __name__ == "__main__":
    analyze_bw()
