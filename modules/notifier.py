import requests

class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.url = f"https://api.telegram.org/bot{token}/sendMessage"

    def send_message(self, text):
        try:
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML"
            }
            response = requests.post(self.url, json=payload, timeout=10)
            if response.status_code == 200:
                print("📨 Notificação enviada para Telegram")
            else:
                print(f"⚠️ Falha ao enviar: {response.text}")
        except Exception as e:
            print(f"❌ Erro no Telegram: {e}")

    def send_performance_report(self, summary):
        if summary is None:
            self.send_message("📊 Ainda não há dados de performance suficientes.")
            return
        msg = (
            f"📊 <b>RELATÓRIO DE PERFORMANCE</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 Total de Trades: {summary['total_trades']}\n"
            f"✅ VITÓRIAS: {summary['wins']}\n"
            f"❌ DERROTAS: {summary['losses']}\n"
            f"🎯 Taxa de Acerto: {summary['win_rate']:.2f}%\n"
            f"💰 Lucro Líquido: ${summary['net_profit']:.2f}\n"
            f"📊 Fator de Lucro: {summary['profit_factor']:.2f}\n"
            f"📉 Drawdown Máximo: ${summary['max_drawdown']:.2f}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🧠 <i>Robô em aprendizado contínuo</i>"
        )
        self.send_message(msg)
