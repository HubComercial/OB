from modules.data_fetcher import DataFetcher
from modules.strategy import generate_signal

fetcher = DataFetcher(asset="EURUSD_otc", timeframe=15)
df = fetcher.get_historical_data(count=50)
sinal = generate_signal(df)

print(f"Sinal gerado: {sinal}")
print(f"Último close: {df['close'].iloc[-1]:.5f}")
print(f"Último open:  {df['open'].iloc[-1]:.5f}")
print(f"EMA:          {df['close'].ewm(span=10, adjust=False).mean().iloc[-1]:.5f}")
