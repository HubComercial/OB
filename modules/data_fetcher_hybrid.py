"""
DataFetcher Híbrido: prioriza IQ Option (M1/M5/M15), com fallback para Yahoo Finance apenas para M15+.
Corrigido: remoção do candle em formação com base no timeframe.
"""
import pandas as pd
import time
import numpy as np
from datetime import datetime, timedelta, timezone
from iqoptionapi.stable_api import IQ_Option
import yfinance as yf
from config import IQ_EMAIL, IQ_PASSWORD

class DataFetcherHybrid:
    _iq_api = None
    _last_ping = 0

    def __init__(self, asset="EURUSD=X", timeframe=1):
        self.asset = asset
        self.timeframe = timeframe
        self._ensure_connection()

    @classmethod
    def _ensure_connection(cls):
        if cls._iq_api is not None:
            try:
                cls._iq_api.get_candles("EURUSD", 1, 1, time.time())
                return True
            except Exception:
                print("⚠️ Sessão IQ Option perdida. A reconectar...")
                cls._iq_api = None

        for attempt in range(5):
            try:
                print(f"🔑 Conectando à IQ Option... (tentativa {attempt+1}/5)")
                api = IQ_Option(IQ_EMAIL, IQ_PASSWORD)
                check, reason = api.connect()
                if check:
                    print("✅ IQ Option conectada!")
                    try:
                        api.change_balance("PRACTICE")
                        print("📊 Modo DEMO")
                    except:
                        pass
                    cls._iq_api = api
                    cls._last_ping = time.time()
                    return True
                else:
                    print(f"❌ IQ Option falhou: {reason}")
                    time.sleep(5)
            except Exception as e:
                print(f"❌ Erro na conexão IQ: {e}")
                time.sleep(5)
        return False

    def get_historical_data(self, count=100):
        if not self._ensure_connection():
            if self.timeframe <= 5:
                print(f"⚠️ IQ Option falhou. Sem dados para {self.asset} ({self.timeframe}m).")
                return None
            else:
                return self._fetch_yahoo(count)

        try:
            iq_asset = self.asset.replace("=X", "")
            request_count = count + 10
            candles = self._iq_api.get_candles(iq_asset, self.timeframe, request_count, time.time())
            if candles and len(candles) > 0:
                df = self._parse_iq_candles(candles)

                if df is not None and not df.empty:
                    # Remove candle em formação
                    last_ts = df['timestamp'].iloc[-1]
                    if last_ts.tzinfo is not None:
                        last_ts = last_ts.tz_convert('UTC').tz_localize(None)
                    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
                    diff = (now_utc - last_ts).total_seconds()

                    if diff < self.timeframe * 60:
                        print(f"⚠️ Removendo candle em formação ({diff:.1f}s atrás) para {self.timeframe}m")
                        df = df.iloc[:-1]

                    # Remove duplicados
                    if df['timestamp'].duplicated().any():
                        print("⚠️ Timestamps duplicados – agrupando por minuto")
                        df['minute'] = df['timestamp'].dt.floor('min')
                        df = df.groupby('minute').last().reset_index(drop=True)

                    # ===== CONDIÇÃO AJUSTADA PARA 0.1 =====
                    if len(df) < count * 0.1:
                        print(f"⚠️ Dados insuficientes (apenas {len(df)} candles de {count} pedidos).")
                        if self.timeframe >= 15:
                            return self._fetch_yahoo(count)
                        else:
                            return None

                    return df[['timestamp', 'open', 'high', 'low', 'close']].tail(count)

        except Exception as e:
            print(f"⚠️ IQ Option erro: {e}")
            DataFetcherHybrid._iq_api = None

        if self.timeframe >= 15:
            print(f"🔄 Fallback para Yahoo Finance ({self.timeframe}m)")
            return self._fetch_yahoo(count)
        else:
            return None

    def _parse_iq_candles(self, candles):
        try:
            df = pd.DataFrame(candles)
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
                elif 'from' in col_lower or 'time' in col_lower:
                    rename_map[col] = 'timestamp'
            df.rename(columns=rename_map, inplace=True)

            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                if df['timestamp'].dt.tz is not None:
                    df['timestamp'] = df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
            else:
                return None

            required = ['timestamp', 'open', 'high', 'low', 'close']
            for r in required:
                if r not in df.columns:
                    return None

            df = df.sort_values('timestamp').reset_index(drop=True)
            return df[required]

        except Exception as e:
            print(f"❌ Erro ao parsear candles IQ: {e}")
            return None

    def _fetch_yahoo(self, count):
        try:
            if self.timeframe >= 15:
                yf_timeframe = "15m"
            else:
                yf_timeframe = "5m"

            ticker = yf.Ticker(self.asset)
            df = ticker.history(period="5d", interval=yf_timeframe)
            if df.empty:
                return self._generate_mock_data(count)
            df = df.reset_index()
            df.rename(columns={'Datetime': 'timestamp', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close'}, inplace=True)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            if df['timestamp'].dt.tz is not None:
                df['timestamp'] = df['timestamp'].dt.tz_convert('UTC').dt.tz_localize(None)
            return df[['timestamp', 'open', 'high', 'low', 'close']].tail(count)
        except Exception as e:
            print(f"⚠️ Yahoo fallback: {e}")
            return self._generate_mock_data(count)

    def _generate_mock_data(self, count):
        print("⚠️ Usando dados simulados.")
        np.random.seed(int(time.time()) % 1000)
        dates = [datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=i * 60 * self.timeframe) for i in range(count, 0, -1)]
        prices = 1.1000 + np.cumsum(np.random.randn(count) * 0.001)
        return pd.DataFrame({
            'timestamp': dates,
            'open': prices + np.random.randn(count) * 0.0002,
            'high': prices + np.abs(np.random.randn(count) * 0.0005),
            'low': prices - np.abs(np.random.randn(count) * 0.0005),
            'close': prices
        })
