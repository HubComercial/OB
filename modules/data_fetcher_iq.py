import pandas as pd
import time
import json
from iqoptionapi.stable_api import IQ_Option
from config import IQ_EMAIL, IQ_PASSWORD


class DataFetcherIQ:

    def __init__(self, asset="EURUSD", timeframe=1):
        self.asset = asset
        self.timeframe = timeframe
        self.api = None
        self.connected = False
        self.connect()


    def connect(self, max_retries=5):

        for attempt in range(max_retries):

            try:
                print(f"🔑 Conectando à IQ Option... (tentativa {attempt+1}/{max_retries})")

                # limpar conexão antiga
                self.api = None
                self.connected = False

                time.sleep(2)

                self.api = IQ_Option(
                    IQ_EMAIL,
                    IQ_PASSWORD
                )

                check, reason = self.api.connect()

                if check:

                    self.connected = True

                    print("✅ IQ Option conectada!")

                    try:
                        self.api.change_balance("PRACTICE")
                        print("📊 Modo DEMO")
                    except:
                        pass

                    return True

                else:
                    print(f"❌ Falha conexão: {reason}")

            except Exception as e:
                print(f"❌ Erro conexão IQ: {e}")

            time.sleep(5)


        print("❌ Não foi possível conectar IQ Option.")
        return False



    def reconnect(self):

        print("🔄 Reconectando IQ Option...")

        try:
            if self.api:
                try:
                    self.api.close()
                except:
                    pass

        except:
            pass


        self.api = None
        self.connected = False

        time.sleep(3)

        return self.connect()



    def get_historical_data(self, count=100, max_retries=5):

        for attempt in range(max_retries):

            try:

                if not self.connected or self.api is None:

                    if not self.connect():
                        time.sleep(5)
                        continue


                candles = self.api.get_candles(
                    self.asset,
                    self.timeframe,
                    count,
                    time.time()
                )


                if not candles:

                    print("⚠️ Nenhum candle retornado.")
                    self.reconnect()
                    continue



                df = pd.DataFrame(candles)


                rename_map = {}

                for col in df.columns:

                    c = col.lower()

                    if c == "open":
                        rename_map[col] = "open"

                    elif c == "close":
                        rename_map[col] = "close"

                    elif c == "max":
                        rename_map[col] = "high"

                    elif c == "min":
                        rename_map[col] = "low"

                    elif "from" in c or "time" in c:
                        rename_map[col] = "timestamp"



                df.rename(
                    columns=rename_map,
                    inplace=True
                )


                if "timestamp" in df.columns:

                    df["timestamp"] = pd.to_datetime(
                        df["timestamp"],
                        unit="s"
                    )


                required = [
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close"
                ]


                if not all(x in df.columns for x in required):

                    print("⚠️ Dados incompletos. Reconectando...")
                    self.reconnect()
                    continue


                return df[required].reset_index(drop=True)



            except json.JSONDecodeError:

                print("❌ JSON inválido da IQ. Reconectando...")
                self.reconnect()


            except Exception as e:

                print(f"❌ Erro get_candles: {e}")
                self.reconnect()



            time.sleep(3)


        print("❌ Falha ao obter candles.")
        return None
