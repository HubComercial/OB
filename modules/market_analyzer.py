"""
modules/market_analyzer.py
Analisa mercado e gera sugestões para um ou todos os ativos.
"""
from modules.data_fetcher_hybrid import DataFetcherHybrid
from modules.indicators import calculate_ema, calculate_rsi, calculate_bollinger_bands
from modules.advanced_metrics import calculate_atr, calculate_pivot_points
from modules.notifier import TelegramNotifier
from config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, ASSETS, TIMEFRAME, ATR_PERIOD

class MarketAnalyzer:
    def __init__(self, asset=None, timeframe=1):
        self.timeframe = timeframe
        self.notifier = TelegramNotifier(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID) if TELEGRAM_TOKEN else None

    def analyze_asset(self, asset):
        """Analisa um único ativo e retorna relatório em texto."""
        fetcher = DataFetcherHybrid(asset=asset, timeframe=self.timeframe)
        df = fetcher.get_historical_data(count=200)
        if df is None or len(df) < 50:
            return None

        close = df['close']
        high = df['high']
        low = df['low']

        ema200 = calculate_ema(close, 200).iloc[-1]
        ema50 = calculate_ema(close, 50).iloc[-1]
        rsi = calculate_rsi(close, 14).iloc[-1]
        atr = calculate_atr(df, ATR_PERIOD)
        upper, mid, lower = calculate_bollinger_bands(close, 20, 2)
        pivots = calculate_pivot_points(df)
        current_price = close.iloc[-1]

        atr_historico = df['close'].rolling(100).std().iloc[-1] * 0.01
        atr_variacao = ((atr - atr_historico) / atr_historico) * 100 if atr_historico > 0 else 0

        tendencia = "alta" if current_price > ema200 else "baixa"
        angulo = (ema50 - ema200) / ema200 * 100

        suporte = pivots['s1'] if pivots else None
        resistencia = pivots['r1'] if pivots else None
        perto_suporte = abs(current_price - suporte) / current_price < 0.001 if suporte else False
        perto_resistencia = abs(current_price - resistencia) / current_price < 0.001 if resistencia else False

        if atr < 0.0002:
            regime = "Parado"
        elif atr < 0.0005:
            regime = "Lateral"
        else:
            regime = "Ativo"

        sugestoes = []
        if atr_variacao > 20:
            sugestoes.append(f"ATR subiu {atr_variacao:.0f}% (considerar reduzir ATR_MIN)")
        elif atr_variacao < -20:
            sugestoes.append(f"ATR caiu {abs(atr_variacao):.0f}% (manter filtros)")

        if perto_suporte:
            sugestoes.append(f"Preço perto do suporte ({suporte:.5f}) → possível COMPRA")
        if perto_resistencia:
            sugestoes.append(f"Preço perto da resistência ({resistencia:.5f}) → possível VENDA")

        if angulo > 0.5:
            sugestoes.append("Tendência de alta forte (EMA50 > EMA200) → priorizar COMPRAS")
        elif angulo < -0.5:
            sugestoes.append("Tendência de baixa forte (EMA50 < EMA200) → priorizar VENDAS")

        if rsi > 70:
            sugestoes.append(f"RSI {rsi:.1f} (sobrecompra) → cuidado com compras")
        elif rsi < 30:
            sugestoes.append(f"RSI {rsi:.1f} (sobrevenda) → cuidado com vendas")

        relatorio = (
            f"📊 {asset}\n"
            f"Preço: {current_price:.5f} | Regime: {regime}\n"
            f"Tendência: {tendencia} | ATR: {atr:.5f}\n"
            f"RSI: {rsi:.1f} | EMA200: {ema200:.5f}\n"
        )
        if sugestoes:
            relatorio += "💡 " + "\n".join(sugestoes)
        else:
            relatorio += "✅ Nenhuma sugestão."

        return relatorio

    def analyze_all(self):
        """Analisa todos os ativos e retorna um relatório consolidado."""
        relatorios = []
        for asset in ASSETS:
            r = self.analyze_asset(asset)
            if r:
                relatorios.append(r)

        if not relatorios:
            return "⚠️ Não foi possível analisar nenhum ativo."

        cabecalho = "🧠 <b>ANÁLISE DE FIM DE DIA – TODOS OS ATIVOS</b>\n"
        cabecalho += "━━━━━━━━━━━━━━━━━━━━━\n"
        corpo = "\n\n".join(relatorios)
        rodape = "\n━━━━━━━━━━━━━━━━━━━━━\n✅ Análise concluída."

        return cabecalho + corpo + rodape

    def send_daily_report(self):
        """Envia o relatório de fim de dia pelo Telegram."""
        relatorio = self.analyze_all()
        if self.notifier and relatorio:
            self.notifier.send_message(relatorio)
            print("📨 Relatório de fim de dia enviado.")
