import yfinance as yf
from modules.data_fetcher_hybrid import DataFetcherHybrid
from datetime import datetime, timezone

def compare_price(asset):
    """Compara o preço atual do Yahoo Finance com o da IQ Option."""
    print(f"\n🔍 Comparando preços para {asset}")
    
    # Yahoo Finance
    try:
        ticker = yf.Ticker(asset)
        data = ticker.history(period="1d", interval="1m")
        if not data.empty:
            yahoo_price = data['Close'].iloc[-1]
            print(f"📊 Yahoo: {yahoo_price:.5f}")
        else:
            print("⚠️ Yahoo: sem dados")
            yahoo_price = None
    except Exception as e:
        print(f"❌ Yahoo erro: {e}")
        yahoo_price = None
    
    # IQ Option
    try:
        fetcher = DataFetcherHybrid(asset=asset, timeframe=1)
        df = fetcher.get_historical_data(count=5)
        if df is not None and not df.empty:
            iq_price = df['close'].iloc[-1]
            print(f"📊 IQ Option: {iq_price:.5f}")
        else:
            print("⚠️ IQ Option: sem dados")
            iq_price = None
    except Exception as e:
        print(f"❌ IQ Option erro: {e}")
        iq_price = None
    
    # Diferença
    if yahoo_price is not None and iq_price is not None:
        diff = abs(yahoo_price - iq_price)
        diff_pips = diff * 10000  # para EURUSD, 1 pip = 0.0001
        print(f"📊 Diferença: {diff:.5f} ({diff_pips:.1f} pips)")
        if diff_pips > 2:
            print("⚠️ Diferença significativa (>2 pips) – pode afetar sinais M1/M5!")
    else:
        print("⚠️ Não foi possível comparar ambos os preços.")

if __name__ == "__main__":
    assets = ["EURUSD=X", "GBPUSD=X", "USDJPY=X"]
    for asset in assets:
        compare_price(asset)
