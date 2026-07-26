import yfinance as yf
import pandas as pd
from modules.data_fetcher_hybrid import DataFetcherHybrid
from datetime import datetime, timedelta
import time

def get_yahoo_candles(asset, count=50):
    """Busca os últimos 'count' candles do Yahoo Finance."""
    try:
        ticker = yf.Ticker(asset)
        df = ticker.history(period="1d", interval="1m")
        if df.empty:
            return None
        df = df.reset_index()
        df.rename(columns={
            'Datetime': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close'
        }, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df.tail(count)[['timestamp', 'open', 'high', 'low', 'close']]
    except Exception as e:
        print(f"❌ Yahoo erro para {asset}: {e}")
        return None

def get_iq_candles(asset, count=50):
    """Busca os últimos 'count' candles da IQ Option."""
    try:
        fetcher = DataFetcherHybrid(asset=asset, timeframe=1)
        df = fetcher.get_historical_data(count=count)
        if df is None or df.empty:
            return None
        return df[['timestamp', 'open', 'high', 'low', 'close']]
    except Exception as e:
        print(f"❌ IQ Option erro para {asset}: {e}")
        return None

def compare_candles(asset):
    """Compara os candles do Yahoo e IQ Option para um ativo."""
    print(f"\n🔍 Comparando candles para {asset} (50 velas M1)")
    print("-" * 60)

    yahoo_df = get_yahoo_candles(asset, 50)
    iq_df = get_iq_candles(asset, 50)

    if yahoo_df is None or iq_df is None:
        print(f"⚠️ Dados insuficientes para {asset}")
        return

    # Alinha os timestamps (iguala pelo índice)
    yahoo_df = yahoo_df.tail(50)
    iq_df = iq_df.tail(50)

    # Calcula diferenças
    iq_df['close_yahoo'] = yahoo_df['close'].values
    iq_df['diff'] = abs(iq_df['close'] - iq_df['close_yahoo'])
    iq_df['diff_pips'] = iq_df['diff'] * 10000  # para EURUSD/GBPUSD

    # Estatísticas
    max_diff = iq_df['diff'].max()
    avg_diff = iq_df['diff'].mean()
    max_pips = max_diff * 10000

    print(f"📊 Média de diferença: {avg_diff:.5f} ({avg_diff*10000:.1f} pips)")
    print(f"📊 Máxima diferença: {max_diff:.5f} ({max_pips:.1f} pips)")

    # Mostra os últimos 5 candles comparados
    print("\n📋 Últimos 5 candles comparados:")
    print(iq_df[['timestamp', 'close', 'close_yahoo', 'diff_pips']].tail(5).to_string(index=False))

    # Alerta se a diferença média for > 2 pips (para EURUSD/GBPUSD) ou > 0.5 para USDJPY
    if "JPY" in asset:
        threshold = 0.5  # pips
        avg_diff_pips = avg_diff * 100  # para JPY, 1 pip = 0.01
        if avg_diff_pips > threshold:
            print(f"\n⚠️ ALERTA: Diferença média > {threshold} pips para {asset} – dados inconsistentes!")
    else:
        if avg_diff * 10000 > 2:
            print(f"\n⚠️ ALERTA: Diferença média > 2 pips para {asset} – dados inconsistentes!")

    return iq_df

if __name__ == "__main__":
    assets = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]
    for asset in assets:
        compare_candles(asset)
        time.sleep(2)  # espera entre chamadas para não sobrecarregar
