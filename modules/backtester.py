import pandas as pd
from datetime import datetime, timedelta
from modules.strategy import generate_signal
from modules.data_fetcher_hybrid import DataFetcherHybrid as DataFetcher
from modules.notifier import TelegramNotifier
from config import ASSETS, AMOUNT, TIMEFRAME, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, BACKTEST_CANDLES

class Backtester:
    def __init__(self):
        self.assets = ASSETS
        self.timeframe = TIMEFRAME
        self.notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID) if TELEGRAM_TOKEN else None
        self.results = {}

    def run(self):
        print("🧠 Iniciando estudo de fim de semana...")
        print(f"📊 Analisando {len(self.assets)} ativos.")

        for asset in self.assets:
            print(f"🔍 Estudando {asset}...")
            try:
                fetcher = DataFetcher(asset=asset, timeframe=self.timeframe)

                # Tenta com BACKTEST_CANDLES, se falhar, reduz para metade
                df = fetcher.get_historical_data(count=BACKTEST_CANDLES)
                if df is None:
                    print(f"⚠️ Tentando com {BACKTEST_CANDLES//2} velas para {asset}...")
                    df = fetcher.get_historical_data(count=BACKTEST_CANDLES//2)

                if df is None or len(df) < 50:
                    print(f"⚠️ Dados insuficientes para {asset} (menos de 50 velas). Pulando.")
                    continue

                available_candles = len(df)
                print(f"📊 {asset}: {available_candles} velas disponíveis.")

                signals = []
                start_idx = min(50, available_candles // 2)
                for i in range(start_idx, available_candles - 1):
                    slice_df = df.iloc[:i+1].copy()
                    signal_data = generate_signal(slice_df, self.timeframe)
                    signal = signal_data['signal']
                    if signal in ["COMPRA", "VENDA"]:
                        next_close = df['close'].iloc[i+1]
                        current_price = df['close'].iloc[i]
                        if signal == "COMPRA":
                            win = next_close > current_price
                        else:
                            win = next_close < current_price
                        profit = AMOUNT * 0.80 if win else -AMOUNT
                        signals.append({
                            'timestamp': df['timestamp'].iloc[i],
                            'signal': signal,
                            'price': current_price,
                            'next_price': next_close,
                            'win': win,
                            'profit': profit
                        })

                total = len(signals)
                wins = sum(1 for s in signals if s['win'])
                losses = total - wins
                win_rate = (wins / total * 100) if total > 0 else 0
                total_profit = sum(s['profit'] for s in signals)
                avg_profit = total_profit / total if total > 0 else 0

                self.results[asset] = {
                    'total': total,
                    'wins': wins,
                    'losses': losses,
                    'win_rate': win_rate,
                    'total_profit': total_profit,
                    'avg_profit': avg_profit,
                    'signals': signals
                }
                print(f"📊 {asset}: {total} sinais, acerto {win_rate:.1f}%, lucro ${total_profit:.2f}")

            except Exception as e:
                print(f"❌ Erro ao estudar {asset}: {e}")
                self.results[asset] = {'error': str(e)}

        self.send_report()

    def send_report(self):
        if not self.notifier:
            print("ℹ️ Telegram não configurado. Relatório apenas no console.")
            self.print_report()
            return

        msg = "🧠 <b>RELATÓRIO DE ESTUDO DE FIM DE SEMANA</b>\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        total_global = 0
        wins_global = 0
        profit_global = 0.0

        for asset, data in self.results.items():
            if 'error' in data:
                msg += f"❌ {asset}: {data['error']}\n"
                continue
            total_global += data['total']
            wins_global += data['wins']
            profit_global += data['total_profit']
            msg += f"📊 {asset}: {data['total']} sinais, acerto {data['win_rate']:.1f}%, lucro ${data['total_profit']:.2f}\n"

        win_rate_global = (wins_global / total_global * 100) if total_global > 0 else 0
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += f"📈 <b>TOTAL GLOBAL</b>\n"
        msg += f"📊 Sinais: {total_global}\n"
        msg += f"🎯 Acerto: {win_rate_global:.1f}%\n"
        msg += f"💰 Lucro: ${profit_global:.2f}\n"
        msg += "━━━━━━━━━━━━━━━━━━━━━\n"
        msg += "🧠 <i>Robô em aprendizado contínuo</i>"

        self.notifier.send_message(msg)
        self.print_report()

    def print_report(self):
        print("\n" + "=" * 60)
        print("🧠 RELATÓRIO DE ESTUDO DE FIM DE SEMANA")
        print("=" * 60)
        for asset, data in self.results.items():
            if 'error' in data:
                print(f"❌ {asset}: {data['error']}")
                continue
            print(f"📊 {asset}: {data['total']} sinais, acerto {data['win_rate']:.1f}%, lucro ${data['total_profit']:.2f}")
        print("=" * 60)
