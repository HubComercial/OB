"""
modules/alert_manager.py
Monitora condições de mercado e envia alertas de pré-confirmação (70%+ das condições ativas).
Versão corrigida para suportar timeframes dinâmicos (fallback para o primeiro timeframe disponível).
"""
from modules.data_fetcher_hybrid import DataFetcherHybrid
from modules.indicators import calculate_rsi, calculate_bollinger_bands, calculate_ema, calculate_cci, calculate_macd
from modules.advanced_metrics import calculate_atr, calculate_pivot_points, check_support_resistance
from modules.notifier import TelegramNotifier
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, ASSETS, TIMEFRAMES, TIMEFRAME_CONFIGS, MACD_FAST, MACD_SLOW, MACD_SIGNAL, ATR_MAX

class AlertManagerMulti:
    def __init__(self):
        self.notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID) if TELEGRAM_TOKEN else None
        self.last_alerts = {}
        # Define o timeframe base para fallback (primeiro da lista)
        self.default_timeframe = TIMEFRAMES[0] if TIMEFRAMES else 5
        print(f"🔔 AlertManagerMulti ativo para {len(ASSETS)} ativos x {len(TIMEFRAMES)} timeframes")

    def check_and_alert(self):
        for asset in ASSETS:
            for tf in TIMEFRAMES:
                self._check_asset_timeframe(asset, tf)

    def _check_asset_timeframe(self, asset, timeframe):
        key = f"{asset}_{timeframe}"
        df = DataFetcherHybrid(asset=asset, timeframe=timeframe).get_historical_data(150)
        if df is None or len(df) < 50:
            return

        # Usa a configuração do timeframe, ou fallback para o primeiro timeframe disponível
        cfg = TIMEFRAME_CONFIGS.get(timeframe)
        if cfg is None:
            # Se não houver configuração para este timeframe, usa o primeiro da lista
            cfg = TIMEFRAME_CONFIGS.get(self.default_timeframe, {})
            if not cfg:
                return
        ema_trend_period = cfg['ema_trend']
        rsi_low = cfg['rsi_low']
        rsi_high = cfg['rsi_high']
        atr_min = cfg['atr_min']
        bollinger_std = cfg['bollinger_std']

        close = df['close']
        open_price = df['open']
        high = df['high']
        low = df['low']

        current_price = float(close.iloc[-1])
        current_open = float(open_price.iloc[-1])
        ema_trend = float(calculate_ema(close, ema_trend_period).iloc[-1])
        ema_fast = float(calculate_ema(close, cfg['ema_fast']).iloc[-1])
        ema_fast_prev = float(calculate_ema(close, cfg['ema_fast']).iloc[-2]) if len(close) > 1 else ema_fast
        rsi = float(calculate_rsi(close, 14).iloc[-1])
        upper, mid, lower = calculate_bollinger_bands(close, 20, bollinger_std)
        upper_val = float(upper.iloc[-1])
        lower_val = float(lower.iloc[-1])
        atr = float(calculate_atr(df, 14))
        cci = float(calculate_cci(high, low, close, 7).iloc[-1])
        macd_line, signal_line, _ = calculate_macd(close, MACD_FAST, MACD_SLOW, MACD_SIGNAL)
        macd_val = float(macd_line.iloc[-1])
        signal_val = float(signal_line.iloc[-1])
        pivots = calculate_pivot_points(df)
        perto_suporte, perto_resistencia, qual = check_support_resistance(current_price, pivots)

        buy_conditions = {
            'candle_verde': current_price > current_open,
            'preco_acima_ema_fast': current_price > ema_fast,
            'cci_alto': cci >= 50,
            'ema_fast_subindo': ema_fast > ema_fast_prev,
            'macd_bullish': macd_val > signal_val,
            'preco_acima_ema_trend': current_price > ema_trend,
            'rsi_baixo': rsi <= rsi_low,
            'preco_banda_inferior': current_price <= lower_val,
            'atr_valido': atr_min <= atr <= ATR_MAX,
            'sr_ok': not perto_resistencia and not perto_suporte,
            'volume_ok': True
        }
        sell_conditions = {
            'candle_vermelho': current_price < current_open,
            'preco_abaixo_ema_fast': current_price < ema_fast,
            'cci_baixo': cci <= -50,
            'ema_fast_descendo': ema_fast < ema_fast_prev,
            'macd_bearish': macd_val < signal_val,
            'preco_abaixo_ema_trend': current_price < ema_trend,
            'rsi_alto': rsi >= rsi_high,
            'preco_banda_superior': current_price >= upper_val,
            'atr_valido': atr_min <= atr <= ATR_MAX,
            'sr_ok': not perto_suporte and not perto_resistencia,
            'volume_ok': True
        }

        total = len(buy_conditions)
        buy_count = sum(1 for v in buy_conditions.values() if v)
        sell_count = sum(1 for v in sell_conditions.values() if v)
        buy_percent = round((buy_count / total) * 100)
        sell_percent = round((sell_count / total) * 100)

        asset_label = asset.replace("=X", "")
        label = f"{asset_label} ({timeframe}m)"

        last_key_buy = f"{key}_buy"
        if buy_percent >= 70 and buy_percent < 100:
            if self.last_alerts.get(last_key_buy) != buy_percent:
                self.last_alerts[last_key_buy] = buy_percent
                faltam = [k for k, v in buy_conditions.items() if not v]
                self.send_alert(
                    f"🧠 <b>PRÉ-CONFIRMAÇÃO (COMPRA)</b>\n"
                    f"📊 {label}\n"
                    f"✅ Condições ativas: {buy_count}/{total} ({buy_percent}%)\n"
                    f"⏳ Faltam: {', '.join(faltam) if faltam else 'Nenhuma'}\n"
                    f"💡 Fique atento! Sinal pode ser ativado em breve."
                )

        last_key_sell = f"{key}_sell"
        if sell_percent >= 70 and sell_percent < 100:
            if self.last_alerts.get(last_key_sell) != sell_percent:
                self.last_alerts[last_key_sell] = sell_percent
                faltam = [k for k, v in sell_conditions.items() if not v]
                self.send_alert(
                    f"🧠 <b>PRÉ-CONFIRMAÇÃO (VENDA)</b>\n"
                    f"📊 {label}\n"
                    f"✅ Condições ativas: {sell_count}/{total} ({sell_percent}%)\n"
                    f"⏳ Faltam: {', '.join(faltam) if faltam else 'Nenhuma'}\n"
                    f"💡 Fique atento! Sinal pode ser ativado em breve."
                )

        if buy_percent < 70:
            self.last_alerts[last_key_buy] = 0
        if sell_percent < 70:
            self.last_alerts[last_key_sell] = 0

    def send_alert(self, message):
        if self.notifier:
            self.notifier.send_message(message)
            print(f"🔔 Alerta enviado: {message[:60]}...")
