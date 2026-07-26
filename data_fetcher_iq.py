cat > modules/data_fetcher_iq.py << 'EOF'
import pandas as pd
import time
from iqoptionapi.stable_api import IQ_Option

class DataFetcherIQ:
    def __init__(self, asset="EURUSD", timeframe=1):
        self.asset = asset
        self.timeframe = timeframe
        print("🔑 Conectando à IQ Option...")
        self.api = IQ_Option("Gutembergsouza875@gmail.com", "Souza280317@")
        check, reason = self.api.connect()
        if check:
            print("✅ Conectado!")
            try:
                self.api.change_balance("PRACTICE")
                print("📊 Modo DEMO")
            except: pass
        else:
            print(f"❌ Erro: {reason}")
            raise Exception("Falha na conexão")

    def get_historical_data(self, count=100):
        try:
            candles = self.api.get_candles(self.asset, self.timeframe, count, time.time())
            if not candles:
                print("⚠️ Nenhum candle retornado.")
                return None
            
            df = pd.DataFrame(candles)
            
            # Mapeamento SIMPLES e DIRETO (sem confusão)
            rename_map = {}
            for col in df.columns:
                col_lower = col.lower()
                if col_lower == 'open':
                    rename_map[col] = 'open'
                elif col_lower == 'close':
                    rename_map[col] = 'close'
                elif col_lower == 'max':
                    rename_map[col] = 'high'
                elif col_lower == 'min':
                    rename_map[col] = 'low'
                elif col_lower == 'from' or 'time' in col_lower:
                    rename_map[col] = 'timestamp'
            
            df.rename(columns=rename_map, inplace=True)
            
            # Converte timestamp (se existir)
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            
            # Verifica se temos todas as colunas necessárias
            required = ['timestamp', 'open', 'high', 'low', 'close']
            for r in required:
                if r not in df.columns:
                    print(f"⚠️ Coluna '{r}' não encontrada. Colunas disponíveis: {df.columns.tolist()}")
                    return None
            
            return df[required]
            
        except Exception as e:
            print(f"❌ Erro ao buscar dados: {e}")
            return None
EOF
