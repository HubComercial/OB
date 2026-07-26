import yfinance as yf
import pandas as pd
from modules.data_fetcher_hybrid import DataFetcherHybrid
from datetime import datetime, timezone
import time

def get_yahoo_candles(asset, count=50):
    ticker = yf.Ticker(asset)
    df = ticker.history(period="1d", interval="1m")
    if df.empty:
        return None
    df = df.reset_index()
    df.rename(columns={'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'}, inplace=True)
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_convert('UTC').dt.tz_localize(None)
    return df.tail(count).reset_index(drop=True)

def get_iq_candles(asset, count=50):
    fetcher = DataFetcherHybrid(asset=asset, timeframe=1)
    df = fetcher.get_historical_data(count=count)
    if df is None or df.empty:
        return None
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
    return df.tail(count).reset_index(drop=True)

def compare_candles(asset):
    print(f"\n🔍 Auditando candles para {asset}")
    print("-" * 60)

    yahoo_df = get_yahoo_candles(asset, 50)
    iq_df = get_iq_candles(asset, 50)

    if yahoo_df is None or iq_df is None:
        print("⚠️ Dados insuficientes.")
        return

    # ===== 1. TIMESTAMPS =====
    print("\n📅 Últimos timestamps (UTC):")
    print(f"Yahoo: {yahoo_df['timestamp'].iloc[-1]}")
    print(f"IQ:    {iq_df['timestamp'].iloc[-1]}")
    print(f"Sistema UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")

    # ===== 2. COMPARAÇÃO PELO MINUTO =====
    yahoo_df['minute'] = yahoo_df['timestamp'].dt.floor('min')
    iq_df['minute'] = iq_df['timestamp'].dt.floor('min')

    # Remove o último candle (em formação) de ambos
    yahoo_df = yahoo_df.iloc[:-1] if len(yahoo_df) > 1 else yahoo_df
    iq_df = iq_df.iloc[:-1] if len(iq_df) > 1 else iq_df

    # Merge pelo minuto
    merged = pd.merge(
        yahoo_df,
        iq_df,
        on='minute',
        suffixes=('_yahoo', '_iq'),
        how='inner'
    )

    if merged.empty:
        print("❌ Nenhum minuto correspondente entre Yahoo e IQ.")
        return

    # ===== 3. CÁLCULO DO ATRASO =====
    merged['delay_seconds'] = (
        merged['timestamp_iq'] - merged['timestamp_yahoo']
    ).dt.total_seconds()

    # ===== 4. DIFERENÇA DE PREÇOS =====
    merged['diff'] = abs(merged['close_iq'] - merged['close_yahoo'])
    if 'JPY' in asset:
        merged['diff_pips'] = merged['diff'] * 100
    else:
        merged['diff_pips'] = merged['diff'] * 10000

    avg_diff = merged['diff'].mean()
    max_diff = merged['diff'].max()
    std_diff = merged['diff'].std()
    avg_pips = merged['diff_pips'].mean()
    max_pips = merged['diff_pips'].max()
    avg_delay = merged['delay_seconds'].mean()
    max_delay = merged['delay_seconds'].max()
    min_delay = merged['delay_seconds'].min()

    print(f"\n📊 Número de candles comparados: {len(merged)}")
    print(f"📊 Atraso médio (segundos): {avg_delay:.1f}s (mín: {min_delay:.1f}s, máx: {max_delay:.1f}s)")
    print(f"📊 Média de diferença (preço): {avg_diff:.5f} ({avg_pips:.1f} pips)")
    print(f"📊 Máxima diferença: {max_diff:.5f} ({max_pips:.1f} pips)")
    print(f"📊 Desvio padrão: {std_diff:.5f}")

    # ===== 5. INTERPRETAÇÃO =====
    if abs(avg_delay - 59) < 2:
        print("✅ Atraso constante ≈ 59s – IQ usa timestamp de fecho, Yahoo usa início. Nenhum atraso real.")
    elif avg_delay < 5 and abs(avg_delay) < 2:
        print("✅ Atraso praticamente zero – ambos sincronizados.")
    elif avg_delay > 60:
        print(f"⚠️ Atraso médio de {avg_delay:.1f}s – pode indicar que a IQ está atrasada.")
    else:
        print(f"📊 Atraso médio de {avg_delay:.1f}s – dentro do esperado.")

    if std_diff < 0.00005 and avg_diff < 0.00015:
        print("✅ Diferença constante – provavelmente apenas diferença de preço entre provedores.")
    else:
        print("⚠️ Diferença variável – pode indicar dados desalinhados ou diferenças de liquidez.")

    # ===== 6. ÚLTIMOS 10 CANDLES =====
    print("\n📋 Últimos 10 candles comparados (minuto, close_yahoo, close_iq, diff_pips, delay_seconds):")
    print(merged[['minute', 'close_yahoo', 'close_iq', 'diff_pips', 'delay_seconds']].tail(10).to_string(index=False))

if __name__ == "__main__":
    assets = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]
    for asset in assets:
        compare_candles(asset)
        time.sleep(2)

